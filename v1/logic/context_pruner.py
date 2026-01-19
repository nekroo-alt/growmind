import ast
from typing import Dict, List, Optional, Set
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
    
    def __init__(self, workspace_root: str = "."):
        """
        Initialize the ContextPruner.
        
        Args:
            workspace_root: Root directory of the project
        """
        self.workspace_root = workspace_root
    
    def prune_context(
        self,
        semantic_mappers: Dict[str, object],
        target_entities: List[Dict],
        dependency_chain: Optional[List[Dict]] = None
    ) -> Dict[str, PrunedContext]:
        """
        Generate pruned context for target entities.
        
        Args:
            semantic_mappers: Dictionary mapping file paths to SemanticMapper instances
            target_entities: List of target entity dicts with keys:
                - name: Entity name
                - type: "function" or "class"
                - file_path: Path to the file
                - relevance_score: Optional relevance score (0-1)
            dependency_chain: Optional list of dependency nodes from DependencyTraverser
        
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
                    mapper, entity_name, file_path, dep_entities
                )
            elif entity_type == "function":
                pruned = self._prune_function(
                    mapper, entity_name, file_path, dep_entities
                )
            else:
                continue
            
            if pruned:
                pruned_contexts[entity_name] = pruned
        
        return pruned_contexts
    
    def _prune_function(
        self,
        mapper: object,
        function_name: str,
        file_path: str,
        dep_entities: Set[str]
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
            lines, func_info, key_lines
        )
        
        return PrunedContext(
            code=pruned_code,
            entity_name=function_name,
            entity_type="function",
            file_path=file_path,
            reason=reason,
            line_range=(start_line, end_line),
            importance=importance
        )
    
    def _prune_class(
        self,
        mapper: object,
        class_name: str,
        file_path: str,
        dep_entities: Set[str]
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
            lines, class_info, methods_to_include
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
            importance=importance
        )
    
    def _extract_key_function_lines(
        self,
        mapper: object,
        func_info: Dict
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
                    if len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute):
                        if not isinstance(node.targets[0].value, ast.Name) or \
                           node.targets[0].value.id != "self":
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
                elif line.startswith("if ") or line.startswith("elif ") or line.startswith("else:"):
                    key_logic_lines.append(i)
                elif line.startswith("for ") or line.startswith("while "):
                    key_logic_lines.append(i)
                # Check for assignments (non-trivial)
                elif "=" in line and not line.startswith("#"):
                    # Skip simple self assignments
                    if not (line.startswith("self.") and "=" in line and line.count("=") == 1):
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
            "boilerplate_lines": boilerplate_lines
        }
    
    def _select_class_methods(
        self,
        class_info: Dict,
        dep_entities: Set[str]
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
        key_lines: Dict
    ) -> str:
        """
        Build a pruned function code snippet.
        
        Args:
            lines: List of source code lines
            func_info: Function metadata
            key_lines: Key lines info from _extract_key_function_lines
        
        Returns:
            Pruned function code as string
        """
        start_line = func_info["start_line"]
        end_line = func_info["end_line"]
        
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
        
        # Select key logic lines
        body_lines = []
        key_line_nums = key_lines["key_logic_lines"]
        
        # Include lines near key logic lines (context window of 2 lines)
        context_window = 2
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
        methods_to_include: List[Dict]
    ) -> str:
        """
        Build a pruned class code snippet.
        
        Args:
            lines: List of source code lines
            class_info: Class metadata
            methods_to_include: List of methods to include
        
        Returns:
            Pruned class code as string
        """
        start_line = class_info["start_line"]
        
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
            "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "chr",
            "complex", "dict", "divmod", "enumerate", "filter", "float",
            "format", "frozenset", "getattr", "hasattr", "hash", "help", "hex",
            "id", "int", "isinstance", "issubclass", "iter", "len", "list",
            "locals", "map", "max", "min", "next", "object", "oct", "open",
            "ord", "pow", "print", "property", "range", "repr", "reversed",
            "round", "set", "setattr", "slice", "sorted", "staticmethod",
            "str", "sum", "super", "tuple", "type", "vars", "zip", "len"
        }
    
    def format_context_as_string(
        self,
        pruned_contexts: Dict[str, PrunedContext],
        include_reasons: bool = True
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
            key=lambda x: {
                "high": 0,
                "medium": 1,
                "low": 2
            }.get(x.importance, 3)
        )
        
        for ctx in sorted_contexts:
            # Add header with file and entity info
            output_lines.append("")
            output_lines.append(f"# === {ctx.entity_type.upper()}: {ctx.entity_name} ===")
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
        original_contexts: Optional[Dict[str, str]] = None
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
            "savings_percent": None
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
