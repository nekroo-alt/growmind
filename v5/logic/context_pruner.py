import ast
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class PrunedContext:
    """
    Represents a pruned code snippet with metadata.
    """

    code: str  # The actual code snippet
    entity_name: str  # Name of the function/class
    entity_type: str  # "function" or "class"
    file_path: str  # Path to the source file
    reason: str  # Why this snippet is included
    line_range: tuple  # (start_line, end_line)
    importance: str  # "high", "medium", or "low"


class ContextPruner:
    """
    Selects minimum informative code snippets for context collection.

    This class implements intelligent context pruning by extracting only the
    essential parts of functions and classes that are relevant to a task,
    while excluding implementation details that don't affect the task.
    """

    def __init__(self, workspace_root: str = ".", max_tokens_per_task: int = 8000):
        """
        Initialize the ContextPruner.

        Args:
            workspace_root: Root directory of the project
            max_tokens_per_task: Maximum tokens allowed per task (default: 8000)
        """
        self.workspace_root = workspace_root
        self.max_tokens_per_task = max_tokens_per_task
        self.token_usage_tracker = {}  # Track token usage per task

    def prune_context(
        self,
        semantic_mappers: Dict[str, object],
        target_entities: List[Dict],
        dependency_chain: Optional[List[Dict]] = None,
        task_complexity: str = "medium",
        task_id: Optional[str] = None,
    ) -> Dict[str, PrunedContext]:
        """
        Generate pruned context for target entities with adaptive compression.

        Args:
            semantic_mappers: Dictionary mapping file paths to SemanticMapper instances
            target_entities: List of target entity dicts with keys:
                - name: Entity name
                - type: "function" or "class"
                - file_path: Path to the file
                - relevance_score: Optional relevance score (0-1)
            dependency_chain: Optional list of dependency nodes from DependencyTraverser
            task_complexity: Task complexity level ("low", "medium", "high")
            task_id: Optional task ID for tracking token usage

        Returns:
            Dict mapping entity names to PrunedContext objects
        """
        pruned_contexts = {}

        # Track which entities are in dependency chain for prioritization
        dep_entities = set()
        if dependency_chain:
            dep_entities = {node["name"] for node in dependency_chain}

        for entity in target_entities:
            entity_name = entity["name"]
            entity_type = entity["type"]
            file_path = entity["file_path"]

            # Get semantic mapper for this file
            if file_path not in semantic_mappers:
                continue

            mapper = semantic_mappers[file_path]

            # Prune based on entity type
            if entity_type == "class":
                pruned = self._prune_class(
                    mapper, entity_name, file_path, dep_entities, task_complexity
                )
            elif entity_type == "function":
                pruned = self._prune_function(
                    mapper, entity_name, file_path, dep_entities, task_complexity
                )
            else:
                continue

            if pruned:
                pruned_contexts[entity_name] = pruned

        # Apply context budgeting - remove low importance items if over budget
        pruned_contexts = self._apply_context_budget(
            pruned_contexts, task_complexity, task_id
        )

        # Track token usage if task_id provided
        if task_id:
            self._track_token_usage(task_id, pruned_contexts)

        return pruned_contexts

    def _prune_function(
        self,
        mapper: object,
        function_name: str,
        file_path: str,
        dep_entities: Set[str],
        task_complexity: str = "medium",
    ) -> Optional[PrunedContext]:
        """
        Extract minimal, informative code for a function.

        Args:
            mapper: SemanticMapper instance
            function_name: Name of the function
            file_path: Path to the file
            dep_entities: Set of entity names in dependency chain

        Returns:
            PrunedContext or None if function not found
        """
        summary = mapper.get_summary()

        # Find the function
        func_info = None
        for func in summary["functions"]:
            if func["name"] == function_name:
                func_info = func
                break

        if not func_info:
            # Check if it's a method
            for cls in summary["classes"]:
                for method in cls["methods"]:
                    if method["name"] == function_name:
                        func_info = method
                        func_info["class_name"] = cls["name"]
                        break

        if not func_info:
            return None

        # Extract key lines
        key_lines = self._extract_key_function_lines(mapper, func_info)

        # Generate code snippet
        lines = mapper.lines
        start_line = func_info["start_line"]
        end_line = func_info["end_line"]
        full_code = "\n".join(lines[start_line - 1 : end_line])

        # Determine importance and reason
        is_in_dep_chain = function_name in dep_entities

        if is_in_dep_chain:
            importance = "high"
            reason = f"Directly affects task execution - {function_name} is in dependency chain"
        elif key_lines["has_return"] or key_lines["has_exception"]:
            importance = "medium"
            reason = f"Returns value or handles exceptions - {function_name} affects control flow"
        else:
            importance = "low"
            reason = f"Helper/utility function - {function_name} provides context for implementation"

        # For functions, include signature, docstring, and key logic
        pruned_code = self._build_function_snippet(
            lines, func_info, key_lines, task_complexity
        )

        return PrunedContext(
            code=pruned_code,
            entity_name=function_name,
            entity_type="function",
            file_path=file_path,
            reason=reason,
            line_range=(start_line, end_line),
            importance=importance,
        )

    def _prune_class(
        self,
        mapper: object,
        class_name: str,
        file_path: str,
        dep_entities: Set[str],
        task_complexity: str = "medium",
    ) -> Optional[PrunedContext]:
        """
        Extract minimal, informative code for a class.

        Args:
            mapper: SemanticMapper instance
            class_name: Name of the class
            file_path: Path to the file
            dep_entities: Set of entity names in dependency chain

        Returns:
            PrunedContext or None if class not found
        """
        summary = mapper.get_summary()

        # Find the class
        class_info = None
        for cls in summary["classes"]:
            if cls["name"] == class_name:
                class_info = cls
                break

        if not class_info:
            return None

        lines = mapper.lines
        start_line = class_info["start_line"]
        end_line = class_info["end_line"]

        # Determine which methods to include
        methods_to_include = self._select_class_methods(class_info, dep_entities)

        # Build class snippet
        pruned_code = self._build_class_snippet(
            lines, class_info, methods_to_include, task_complexity
        )

        # Determine importance and reason
        relevant_methods = [m for m in methods_to_include if m["name"] in dep_entities]

        if relevant_methods:
            importance = "high"
            reason = f"Class contains {len(relevant_methods)} methods in dependency chain - critical for task"
        elif methods_to_include:
            importance = "medium"
            reason = f"Class with {len(methods_to_include)} relevant methods - affects task execution"
        else:
            importance = "low"
            reason = f"Class structure - provides context for related functionality"

        return PrunedContext(
            code=pruned_code,
            entity_name=class_name,
            entity_type="class",
            file_path=file_path,
            reason=reason,
            line_range=(start_line, end_line),
            importance=importance,
        )

    def _extract_key_function_lines(
        self, mapper: object, func_info: Dict
    ) -> Dict[str, any]:
        """
        Identify key lines in a function for pruning.

        Args:
            mapper: SemanticMapper instance
            func_info: Function metadata dict

        Returns:
            Dict with keys:
                - has_return: Whether function returns a value
                - has_exception: Whether function handles exceptions
                - key_logic_lines: List of line numbers with key logic
                - boilerplate_lines: List of line numbers to skip
        """
        lines = mapper.lines
        start_line = func_info["start_line"]
        end_line = func_info["end_line"]

        has_return = False
        has_exception = False
        key_logic_lines = []
        boilerplate_lines = []

        # Parse function body
        func_code = "\n".join(lines[start_line - 1 : end_line])

        # Use heuristic to detect exception handling
        # Check for "try" and "except" keywords in the code
        code_lower = func_code.lower()
        if "try:" in code_lower and "except" in code_lower:
            has_exception = True

        try:
            # Try to parse as-is
            func_tree = ast.parse(func_code)

            for node in ast.walk(func_tree):
                if isinstance(node, ast.Return):
                    has_return = True
                    key_logic_lines.append(node.lineno + start_line - 1)
                elif isinstance(node, ast.Try):
                    has_exception = True
                    key_logic_lines.append(node.lineno + start_line - 1)
                    # Also include except handlers
                    for handler in node.handlers:
                        key_logic_lines.append(handler.lineno + start_line - 1)
                elif isinstance(node, ast.ExceptHandler):
                    has_exception = True
                    key_logic_lines.append(node.lineno + start_line - 1)
                elif isinstance(node, ast.If):
                    # Include conditionals (but skip trivial checks)
                    key_logic_lines.append(node.lineno + start_line - 1)
                elif isinstance(node, ast.For) or isinstance(node, ast.While):
                    # Include loops
                    key_logic_lines.append(node.lineno + start_line - 1)
                elif isinstance(node, ast.Assign):
                    # Include assignments, but skip trivial ones like "self.x = x"
                    if len(node.targets) == 1 and isinstance(
                        node.targets[0], ast.Attribute
                    ):
                        if (
                            not isinstance(node.targets[0].value, ast.Name)
                            or node.targets[0].value.id != "self"
                        ):
                            key_logic_lines.append(node.lineno + start_line - 1)
                    else:
                        key_logic_lines.append(node.lineno + start_line - 1)
                elif isinstance(node, ast.Call):
                    # Include non-builtin function calls
                    if isinstance(node.func, ast.Name):
                        if node.func.id not in self._get_builtins():
                            key_logic_lines.append(node.lineno + start_line - 1)

        except SyntaxError:
            # If parsing fails due to indentation (class methods), use heuristic
            # Find lines with key constructs
            for i in range(start_line, end_line + 1):
                line = lines[i - 1].strip()

                # Check for return statements
                if line.startswith("return"):
                    has_return = True
                    key_logic_lines.append(i)
                # Check for try/except
                elif line.startswith("try:"):
                    has_exception = True
                    key_logic_lines.append(i)
                elif line.startswith("except"):
                    has_exception = True
                    key_logic_lines.append(i)
                # Check for control flow
                elif (
                    line.startswith("if ")
                    or line.startswith("elif ")
                    or line.startswith("else:")
                ):
                    key_logic_lines.append(i)
                elif line.startswith("for ") or line.startswith("while "):
                    key_logic_lines.append(i)
                # Check for assignments (non-trivial)
                elif "=" in line and not line.startswith("#"):
                    # Skip simple self assignments
                    if not (
                        line.startswith("self.")
                        and "=" in line
                        and line.count("=") == 1
                    ):
                        key_logic_lines.append(i)
                # Check for function calls
                elif "(" in line and ")" in line:
                    # Extract function name
                    func_name = line.split("(")[0].strip()
                    # Skip builtins
                    if func_name and not func_name in self._get_builtins():
                        key_logic_lines.append(i)

        return {
            "has_return": has_return,
            "has_exception": has_exception,
            "key_logic_lines": sorted(list(set(key_logic_lines))),
            "boilerplate_lines": boilerplate_lines,
        }

    def _select_class_methods(
        self, class_info: Dict, dep_entities: Set[str]
    ) -> List[Dict]:
        """
        Select which methods to include for a class.

        Args:
            class_info: Class metadata dict
            dep_entities: Set of entity names in dependency chain

        Returns:
            List of method metadata dicts to include
        """
        methods_to_include = []

        for method in class_info["methods"]:
            method_name = method["name"]

            # Always include __init__
            if method_name == "__init__":
                methods_to_include.append(method)
                continue

            # Include methods in dependency chain
            if method_name in dep_entities:
                methods_to_include.append(method)
                continue

            # Include methods with side effects (modify self attributes)
            data_flow = method.get("data_flow", {})
            if data_flow.get("attribute_assigns"):
                methods_to_include.append(method)
                continue

            # Include methods that return values (not just getters)
            if data_flow.get("reads") or data_flow.get("has_return"):
                methods_to_include.append(method)
                continue

        return methods_to_include

    def _build_function_snippet(
        self,
        lines: List[str],
        func_info: Dict,
        key_lines: Dict,
        task_complexity: str = "medium",
    ) -> str:
        """
        Build a pruned function code snippet with adaptive compression.

        Args:
            lines: List of source code lines
            func_info: Function metadata
            key_lines: Key lines info from _extract_key_function_lines
            task_complexity: Task complexity level for adaptive pruning

        Returns:
            Pruned function code as string
        """
        start_line = func_info["start_line"]
        end_line = func_info["end_line"]

        # For low complexity tasks, use summarized version for well-understood code
        if task_complexity == "low" and self._is_well_understood_function(func_info):
            return self._create_function_summary(func_info)

        # Always include signature (first line(s) until :)
        signature_lines = []
        for i in range(start_line - 1, end_line):
            line = lines[i]
            signature_lines.append(line)
            if ":" in line and not line.strip().startswith("#"):
                break

        # Add docstring if present
        docstring_lines = []
        if func_info.get("docstring"):
            docstring_lines.append(func_info["docstring"])

        # Select key logic lines - adaptive based on task complexity
        body_lines = []
        key_line_nums = key_lines["key_logic_lines"]

        # Context window varies by task complexity
        context_window = self._get_context_window(task_complexity)

        for line_num in key_line_nums:
            for offset in range(-context_window, context_window + 1):
                adj_line = line_num + offset
                if start_line <= adj_line <= end_line and adj_line not in body_lines:
                    body_lines.append(adj_line)

        body_lines = sorted(body_lines)

        # Build snippet
        snippet_lines = []
        snippet_lines.extend(signature_lines)

        if docstring_lines:
            snippet_lines.append('"""')
            snippet_lines.append(func_info["docstring"])
            snippet_lines.append('"""')

        # Add body lines with indentation
        for line_num in body_lines:
            line = lines[line_num - 1]
            snippet_lines.append(line)

        return "\n".join(snippet_lines)

    def _build_class_snippet(
        self,
        lines: List[str],
        class_info: Dict,
        methods_to_include: List[Dict],
        task_complexity: str = "medium",
    ) -> str:
        """
        Build a pruned class code snippet with adaptive compression.

        Args:
            lines: List of source code lines
            class_info: Class metadata
            methods_to_include: List of methods to include
            task_complexity: Task complexity level for adaptive pruning

        Returns:
            Pruned class code as string
        """
        start_line = class_info["start_line"]

        # For low complexity tasks, use summarized version for well-understood classes
        if task_complexity == "low" and self._is_well_understood_class(class_info):
            return self._create_class_summary(class_info, methods_to_include)

        # Get class definition line
        class_line = lines[start_line - 1]
        snippet_lines = [class_line]

        # Add docstring if present
        if class_info.get("docstring"):
            snippet_lines.append('"""')
            snippet_lines.append(class_info["docstring"])
            snippet_lines.append('"""')

        # Add selected methods
        for method in methods_to_include:
            method_start = method["start_line"]
            method_end = method["end_line"]

            # For low/medium complexity, summarize trivial methods
            if task_complexity in ["low", "medium"] and self._is_trivial_method(method):
                summary = self._create_method_summary(method)
                snippet_lines.append("")
                snippet_lines.append(f"    # {summary}")
                continue

            # Add blank line before method
            snippet_lines.append("")

            # Add method code
            for i in range(method_start - 1, method_end):
                snippet_lines.append(lines[i])

        return "\n".join(snippet_lines)

    def _get_builtins(self) -> Set[str]:
        """
        Get set of Python builtin function names.

        Returns:
            Set of builtin names
        """
        return {
            "abs",
            "all",
            "any",
            "bin",
            "bool",
            "bytearray",
            "bytes",
            "chr",
            "complex",
            "dict",
            "divmod",
            "enumerate",
            "filter",
            "float",
            "format",
            "frozenset",
            "getattr",
            "hasattr",
            "hash",
            "help",
            "hex",
            "id",
            "int",
            "isinstance",
            "issubclass",
            "iter",
            "len",
            "list",
            "locals",
            "map",
            "max",
            "min",
            "next",
            "object",
            "oct",
            "open",
            "ord",
            "pow",
            "print",
            "property",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "setattr",
            "slice",
            "sorted",
            "staticmethod",
            "str",
            "sum",
            "super",
            "tuple",
            "type",
            "vars",
            "zip",
            "len",
        }

    def format_context_as_string(
        self, pruned_contexts: Dict[str, PrunedContext], include_reasons: bool = True
    ) -> str:
        """
        Format pruned contexts as a single string for LLM consumption.

        Args:
            pruned_contexts: Dict of PrunedContext objects
            include_reasons: Whether to include reason comments

        Returns:
            Formatted context string
        """
        output_lines = []

        # Sort by importance (high, medium, low)
        sorted_contexts = sorted(
            pruned_contexts.values(),
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.importance, 3),
        )

        for ctx in sorted_contexts:
            # Add header with file and entity info
            output_lines.append("")
            output_lines.append(
                f"# === {ctx.entity_type.upper()}: {ctx.entity_name} ==="
            )
            output_lines.append(f"# File: {ctx.file_path}")
            output_lines.append(f"# Lines: {ctx.line_range[0]}-{ctx.line_range[1]}")
            output_lines.append(f"# Importance: {ctx.importance}")

            if include_reasons:
                output_lines.append(f"# Why included: {ctx.reason}")

            output_lines.append("")
            output_lines.append(ctx.code)
            output_lines.append("")

        return "\n".join(output_lines)

    def estimate_token_savings(
        self,
        pruned_contexts: Dict[str, PrunedContext],
        original_contexts: Optional[Dict[str, str]] = None,
    ) -> Dict[str, int]:
        """
        Estimate token savings from pruning.

        Args:
            pruned_contexts: Dict of PrunedContext objects
            original_contexts: Optional dict of original full code snippets

        Returns:
            Dict with keys:
                - pruned_tokens: Estimated tokens in pruned context
                - original_tokens: Estimated tokens in original context (if provided)
                - savings_percent: Percentage saved (if original provided)
        """
        # Simple estimation: ~4 characters per token (rough approximation)
        pruned_chars = sum(len(ctx.code) for ctx in pruned_contexts.values())
        pruned_tokens = pruned_chars // 4

        result = {
            "pruned_tokens": pruned_tokens,
            "original_tokens": None,
            "savings_percent": None,
        }

        if original_contexts:
            original_chars = sum(len(code) for code in original_contexts.values())
            original_tokens = original_chars // 4
            result["original_tokens"] = original_tokens

            if original_tokens > 0:
                result["savings_percent"] = round(
                    ((original_tokens - pruned_tokens) / original_tokens) * 100, 2
                )

        return result

    def _apply_context_budget(
        self,
        pruned_contexts: Dict[str, PrunedContext],
        task_complexity: str,
        task_id: Optional[str],
    ) -> Dict[str, PrunedContext]:
        """
        Apply context budgeting by removing low importance items if over budget.

        Args:
            pruned_contexts: Dict of PrunedContext objects
            task_complexity: Task complexity level
            task_id: Optional task ID for tracking

        Returns:
            Filtered dict of PrunedContext objects within budget
        """
        # Calculate current token estimate
        token_estimate = self._estimate_tokens_from_contexts(pruned_contexts)

        # Get budget threshold based on task complexity
        budget_threshold = self._get_budget_threshold(task_complexity)

        if token_estimate <= budget_threshold:
            return pruned_contexts

        # Need to prune - remove low importance items first
        sorted_contexts = sorted(
            pruned_contexts.items(),
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x[1].importance, 3),
        )

        filtered_contexts = {}
        current_tokens = 0

        for entity_name, ctx in sorted_contexts:
            ctx_tokens = len(ctx.code) // 4  # Rough token estimation

            if current_tokens + ctx_tokens <= budget_threshold:
                filtered_contexts[entity_name] = ctx
                current_tokens += ctx_tokens
            elif ctx.importance == "high":
                # Keep high importance items even if slightly over budget
                filtered_contexts[entity_name] = ctx
                current_tokens += ctx_tokens

        return filtered_contexts

    def _track_token_usage(
        self, task_id: str, pruned_contexts: Dict[str, PrunedContext]
    ):
        """
        Track token usage for a task.

        Args:
            task_id: Task identifier
            pruned_contexts: Dict of PrunedContext objects
        """
        token_estimate = self._estimate_tokens_from_contexts(pruned_contexts)

        if task_id not in self.token_usage_tracker:
            self.token_usage_tracker[task_id] = {
                "total_tokens": 0,
                "context_count": 0,
                "high_importance": 0,
                "medium_importance": 0,
                "low_importance": 0,
            }

        self.token_usage_tracker[task_id]["total_tokens"] += token_estimate
        self.token_usage_tracker[task_id]["context_count"] += len(pruned_contexts)

        for ctx in pruned_contexts.values():
            if ctx.importance == "high":
                self.token_usage_tracker[task_id]["high_importance"] += 1
            elif ctx.importance == "medium":
                self.token_usage_tracker[task_id]["medium_importance"] += 1
            else:
                self.token_usage_tracker[task_id]["low_importance"] += 1

    def get_token_usage_stats(self, task_id: str) -> Optional[Dict[str, int]]:
        """
        Get token usage statistics for a task.

        Args:
            task_id: Task identifier

        Returns:
            Dict with token usage stats or None if task not tracked
        """
        return self.token_usage_tracker.get(task_id)

    def _estimate_tokens_from_contexts(
        self, pruned_contexts: Dict[str, PrunedContext]
    ) -> int:
        """
        Estimate total tokens from pruned contexts.

        Args:
            pruned_contexts: Dict of PrunedContext objects

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        total_chars = sum(len(ctx.code) for ctx in pruned_contexts.values())
        return total_chars // 4

    def _get_budget_threshold(self, task_complexity: str) -> int:
        """
        Get token budget threshold based on task complexity.

        Args:
            task_complexity: Task complexity level

        Returns:
            Token budget threshold
        """
        if task_complexity == "low":
            return self.max_tokens_per_task * 0.5  # 50% of max
        elif task_complexity == "medium":
            return self.max_tokens_per_task * 0.75  # 75% of max
        else:  # high
            return self.max_tokens_per_task  # 100% of max

    def _get_context_window(self, task_complexity: str) -> int:
        """
        Get context window size based on task complexity.

        Args:
            task_complexity: Task complexity level

        Returns:
            Context window size (lines of context)
        """
        if task_complexity == "low":
            return 1
        elif task_complexity == "medium":
            return 2
        else:  # high
            return 3

    def _is_well_understood_function(self, func_info: Dict) -> bool:
        """
        Check if a function is well-understood and can be summarized.

        Args:
            func_info: Function metadata

        Returns:
            True if function can be summarized
        """
        # Small functions with simple logic can be summarized
        line_count = func_info["end_line"] - func_info["start_line"]

        # Getter/setter patterns
        name = func_info["name"].lower()
        if (
            name.startswith("get_")
            or name.startswith("set_")
            or name.startswith("is_")
            or name.startswith("has_")
        ):
            return line_count <= 5

        # Small, simple functions
        return line_count <= 8

    def _is_well_understood_class(self, class_info: Dict) -> bool:
        """
        Check if a class is well-understood and can be summarized.

        Args:
            class_info: Class metadata

        Returns:
            True if class can be summarized
        """
        # Classes with few methods and small size
        method_count = len(class_info.get("methods", []))
        line_count = class_info["end_line"] - class_info["start_line"]

        return method_count <= 3 and line_count <= 30

    def _is_trivial_method(self, method: Dict) -> bool:
        """
        Check if a method is trivial and can be summarized.

        Args:
            method: Method metadata

        Returns:
            True if method is trivial
        """
        name = method["name"].lower()
        line_count = method["end_line"] - method["start_line"]

        # Getter/setter patterns
        if (
            name.startswith("get_")
            or name.startswith("set_")
            or name.startswith("is_")
            or name.startswith("has_")
        ):
            return line_count <= 5

        # __str__, __repr__, etc.
        if name.startswith("__") and name.endswith("__"):
            return line_count <= 5

        return False

    def _create_function_summary(self, func_info: Dict) -> str:
        """
        Create a summarized version of a function.

        Args:
            func_info: Function metadata

        Returns:
            Function summary string
        """
        name = func_info["name"]
        docstring = func_info.get("docstring", f"Function {name}")

        return f"""# Function: {name}
# Purpose: {docstring[:100]}
# Type: Well-understood helper - full implementation omitted for brevity"""

    def _create_class_summary(
        self, class_info: Dict, methods_to_include: List[Dict]
    ) -> str:
        """
        Create a summarized version of a class.

        Args:
            class_info: Class metadata
            methods_to_include: List of methods to include

        Returns:
            Class summary string
        """
        name = class_info["name"]
        docstring = class_info.get("docstring", f"Class {name}")

        method_names = [m["name"] for m in methods_to_include]
        methods_summary = ", ".join(method_names)

        return f"""# Class: {name}
# Purpose: {docstring[:100]}
# Methods: {methods_summary}
# Type: Well-understood class - full implementation omitted for brevity"""

    def _create_method_summary(self, method: Dict) -> str:
        """
        Create a summarized version of a method.

        Args:
            method: Method metadata

        Returns:
            Method summary string
        """
        name = method["name"]
        docstring = method.get("docstring", f"Method {name}")

        return f"Method {name}: {docstring[:80]}..."
