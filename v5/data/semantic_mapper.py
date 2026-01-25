import ast
import os
from typing import Optional
from .call_graph_persistence import CallGraphPersistence


class SemanticMapper:
    """
    Parses Python source code using AST module to create a semantic map of file.

    V5 Enhancement:
    - Integrates with CallGraphPersistence for persistent call graph storage
    - Tracks function/class usage statistics across sessions
    - Supports incremental updates to call graphs
    """
    """
    Parses Python source code using the AST module to create a semantic map of the file.
    """

    def __init__(self, source_code: str, file_path: Optional[str] = None):
        """
        Initialize SemanticMapper.

        Args:
            source_code: Python source code to analyze
            file_path: Optional file path for persistence tracking
        """
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.lines = source_code.splitlines()
        self.call_graph = None  # Will be built on demand
        self.file_path = file_path
        self.call_graph_persistence = None  # Will be initialized if needed

        # Initialize call graph persistence if file_path is provided
        if file_path:
            self.call_graph_persistence = CallGraphPersistence()

    def get_summary(self):
        """
        Returns a structured summary of the classes and functions in the file.
        """
        summary = {"classes": [], "functions": []}

        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.ClassDef):
                summary["classes"].append(self._parse_class(node))
            elif isinstance(node, ast.FunctionDef):
                summary["functions"].append(self._parse_function(node))

        return summary

    def get_call_graph(self, max_depth=10, persist: bool = True):
        """
        Builds and returns a call graph showing which functions call which.

        V5 Enhancement:
        - Automatically persists call graph if file_path is provided and persist=True
        - Tracks usage statistics across sessions

        Args:
            max_depth: Maximum call depth to track (prevents infinite recursion)
            persist: Whether to persist call graph to database (default: True)

        Returns:
            dict: Call graph where keys are caller functions and values are lists
                  of called functions with metadata (callee, line_number, call_depth)
        """
        if self.call_graph is None:
            self.call_graph = self._build_call_graph(max_depth)

            # Persist call graph if file_path is provided and persist is True
            if persist and self.file_path and self.call_graph_persistence:
                self._persist_call_graph()

        return self.call_graph

    def _persist_call_graph(self):
        """
        Persist call graph to database.

        V5 Enhancement:
        - Stores call graph in SQLite database
        - Stores import dependencies
        - Updates usage statistics
        """
        if self.call_graph_persistence:
            # Store call graph
            self.call_graph_persistence.store_call_graph(self.file_path, self.call_graph)

            # Store import dependencies
            import_deps = self.get_import_dependencies()
            self.call_graph_persistence.store_import_dependencies(self.file_path, import_deps)

    def get_usage_statistics(self, min_calls: int = 0):
        """
        Get usage statistics for this file from persistent storage.

        V5 Enhancement:
        - Retrieves usage statistics from database
        - Returns hot/cold function information

        Args:
            min_calls: Minimum call count threshold

        Returns:
            list: Usage statistics sorted by call count
        """
        if self.call_graph_persistence and self.file_path:
            return self.call_graph_persistence.get_usage_statistics(
                self.file_path,
                min_calls=min_calls
            )
        return []

    def get_hot_cold_functions(self, hot_threshold: int = 10, cold_threshold: int = 2):
        """
        Get hot and cold functions for this file from persistent storage.

        V5 Enhancement:
        - Retrieves hot/cold function classification from database
        - Helps identify frequently vs rarely used functions

        Args:
            hot_threshold: Minimum call count to be considered hot
            cold_threshold: Maximum call count to be considered cold

        Returns:
            tuple: (hot_functions, cold_functions)
        """
        if self.call_graph_persistence and self.file_path:
            # Get all functions for this file
            all_stats = self.call_graph_persistence.get_usage_statistics(self.file_path)

            # Filter into hot and cold
            hot = [f for f in all_stats if f["call_count"] >= hot_threshold]
            cold = [f for f in all_stats if f["call_count"] <= cold_threshold]

            return hot, cold
        return [], []

    def get_persisted_call_graph(self):
        """
        Retrieve call graph from persistent storage for this file.

        V5 Enhancement:
        - Gets previously stored call graph from database
        - Useful for cross-session analysis

        Returns:
            dict: Persisted call graph or empty dict if not found
        """
        if self.call_graph_persistence and self.file_path:
            return self.call_graph_persistence.get_call_graph(self.file_path)
        return {}

    def get_import_usage(self):
        """
        Get import usage statistics for this file from persistent storage.

        V5 Enhancement:
        - Retrieves import usage from database
        - Shows which imports are actually used

        Returns:
            list: Import usage statistics
        """
        if self.call_graph_persistence and self.file_path:
            return self.call_graph_persistence.get_import_dependencies(self.file_path)
        return []

    def _parse_class(self, node: ast.ClassDef):
        """
        Extracts information about a class definition.
        """
        methods = []
        dependencies = set()
        attribute_type_hints = {}

        # Base classes are dependencies
        for base in node.bases:
            if isinstance(base, ast.Name):
                dependencies.add(base.id)
            elif isinstance(base, ast.Attribute):
                dependencies.add(base.attr)

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(self._parse_function(item))
            elif isinstance(item, ast.AnnAssign):
                # Extract class attribute type hints (e.g., self.attr: int = 5)
                attr_info = self._extract_class_attribute_type_hint(item)
                if attr_info:
                    attribute_type_hints[attr_info["name"]] = attr_info
            elif isinstance(item, ast.Assign):
                # Check for __annotations__ assignments
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__annotations__":
                        # Extract type hints from __annotations__ dict
                        annotations = self._extract_annotations_dict(item.value)
                        attribute_type_hints.update(annotations)

        return {
            "name": node.name,
            "type": "class",
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "docstring": ast.get_docstring(node),
            "methods": methods,
            "dependencies": sorted(list(dependencies)),
            "attribute_type_hints": attribute_type_hints,
        }

    def _parse_function(self, node: ast.FunctionDef):
        """
        Extracts information about a function or method definition.
        """
        args = [arg.arg for arg in node.args.args]
        dependencies = self._get_dependencies(node)
        data_flow = self._analyze_data_flow(node)
        type_hints = self._extract_function_type_hints(node)
        return {
            "name": node.name,
            "type": "function",
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "docstring": ast.get_docstring(node),
            "args": args,
            "dependencies": dependencies,
            "data_flow": data_flow,
            "type_hints": type_hints,
        }

    def _get_dependencies(self, node):
        """
        Finds all names used within a node's body.
        Excludes local arguments and common builtins.
        """
        deps = set()
        args = set()

        # Collect arguments to exclude
        if hasattr(node, "args"):
            for arg in node.args.args:
                args.add(arg.arg)

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Load):
                    deps.add(child.id)
            elif isinstance(child, ast.Attribute):
                # For cases like module.function or self.method
                if isinstance(child.value, ast.Name):
                    if child.value.id == "self":
                        # We might want to track self.method calls as dependencies within the class
                        deps.add(child.attr)
                    else:
                        deps.add(child.value.id)

        exclude = args | {
            "self",
            "cls",
            "None",
            "True",
            "False",
            "int",
            "str",
            "list",
            "dict",
            "set",
            "print",
            "len",
            "range",
            "getattr",
            "setattr",
            "isinstance",
            "getattr",
            "hasattr",
        }
        filtered_deps = {d for d in deps if d not in exclude}

        return sorted(list(filtered_deps))

    def get_relevant_nodes(self, node_names):
        """
        Given a list of names (classes or functions), returns their source code snippets.
        """
        relevant_code = []
        summary = self.get_summary()

        for node_name in node_names:
            # Check functions
            for func in summary["functions"]:
                if func["name"] == node_name:
                    relevant_code.append(
                        self._get_source_range(func["start_line"], func["end_line"])
                    )

            # Check classes
            for cls in summary["classes"]:
                if cls["name"] == node_name:
                    relevant_code.append(
                        self._get_source_range(cls["start_line"], cls["end_line"])
                    )
                else:
                    # Check methods within classes
                    for method in cls["methods"]:
                        if method["name"] == node_name:
                            relevant_code.append(
                                self._get_source_range(
                                    method["start_line"], method["end_line"]
                                )
                            )

        return "\n\n".join(relevant_code)

    def _get_source_range(self, start_line, end_line):
        """
        Helper to extract source code lines.
        """
        return "\n".join(self.lines[start_line - 1 : end_line])

    def _build_call_graph(self, max_depth):
        """
        Builds a call graph by analyzing function calls in the AST.

        Args:
            max_depth: Maximum call depth to track (prevents infinite recursion)

        Returns:
            dict: Call graph structure
        """
        call_graph = {}
        summary = self.get_summary()

        # Build a map of all functions and methods for quick lookup
        all_functions = {}

        # Add top-level functions
        for func in summary["functions"]:
            all_functions[func["name"]] = {
                "type": "function",
                "node": func,
                "context": None,
            }

        # Add class methods
        for cls in summary["classes"]:
            for method in cls["methods"]:
                all_methods_key = f"{cls['name']}.{method['name']}"
                all_functions[method["name"]] = {
                    "type": "method",
                    "node": method,
                    "context": cls["name"],
                }
                all_functions[all_methods_key] = {
                    "type": "method",
                    "node": method,
                    "context": cls["name"],
                }

        # Analyze calls in each function
        for func_name, func_info in all_functions.items():
            calls = self._extract_calls(func_info["node"], all_functions, max_depth)
            call_graph[func_name] = calls

        return call_graph

    def _extract_calls(self, func_node, all_functions, max_depth):
        """
        Extracts function calls from a function or method node.

        Args:
            func_node: Function metadata dict
            all_functions: Map of all available functions
            max_depth: Maximum call depth to track

        Returns:
            list: List of call information dicts
        """
        calls = []

        # Re-parse the function body to analyze calls
        if "start_line" in func_node and "end_line" in func_node:
            source = "\n".join(
                self.lines[func_node["start_line"] - 1 : func_node["end_line"]]
            )
            try:
                func_tree = ast.parse(source)

                # Walk through the function's AST
                for node in ast.walk(func_tree):
                    if isinstance(node, ast.Call):
                        call_info = self._analyze_call(node, all_functions)
                        if call_info:
                            calls.append(call_info)
            except SyntaxError:
                # If parsing fails, skip this function
                pass

        return calls

    def _analyze_call(self, call_node, all_functions):
        """
        Analyzes a single call node to determine what's being called.

        Args:
            call_node: ast.Call node
            all_functions: Map of all available functions

        Returns:
            dict or None: Call information dict if it's a function call
        """
        callee_name = None
        is_external = False

        # Get the function being called
        func = call_node.func

        if isinstance(func, ast.Name):
            # Simple call: function()
            callee_name = func.id
            if callee_name not in all_functions:
                is_external = True

        elif isinstance(func, ast.Attribute):
            # Attribute call: obj.method() or self.method()
            if isinstance(func.value, ast.Name):
                if func.value.id == "self":
                    # self.method() - it's a method call in the same class
                    callee_name = func.attr
                    if callee_name not in all_functions:
                        # Could be inherited method, mark as external but keep track
                        is_external = True
                else:
                    # obj.method() - external method call
                    callee_name = f"{func.value.id}.{func.attr}"
                    is_external = True
            elif isinstance(func.value, ast.Call):
                # Chained call: obj().method()
                # This is too complex, mark as external
                callee_name = "<dynamic>"
                is_external = True

        if callee_name and callee_name != "<dynamic>":
            return {
                "callee": callee_name,
                "line_number": call_node.lineno,
                "is_external": is_external,
                "call_depth": 1,  # Direct call, depth 1
            }

        return None

    def _analyze_data_flow(self, node: ast.FunctionDef):
        """
        Analyzes data flow within a function to track variable reads and writes.

        Args:
            node: ast.FunctionDef node to analyze

        Returns:
            dict: Data flow information including reads, writes, and state changes
        """
        reads = set()
        writes = set()
        param_passing = []
        attribute_assigns = []
        attribute_reads = []

        # Collect parameter names to exclude from reads (they're inputs)
        params = {arg.arg for arg in node.args.args}

        # Walk through the function body
        for child in ast.walk(node):
            # Track variable reads
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Load):
                    # Exclude parameters, builtins, and common constructs
                    if child.id not in params and not self._is_builtin(child.id):
                        reads.add(child.id)

            # Track attribute reads (e.g., self.data, obj.value)
            elif isinstance(child, ast.Attribute):
                if isinstance(child.ctx, ast.Load):
                    # Extract attribute read information
                    attr_read_info = self._extract_attribute_read(child)
                    if attr_read_info:
                        attribute_reads.append(attr_read_info)

            # Track variable writes (assignments)
            elif isinstance(child, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                if isinstance(child, ast.Assign):
                    targets = child.targets
                else:  # AugAssign or AnnAssign
                    targets = [child.target]

                for target in targets:
                    if isinstance(target, ast.Name):
                        writes.add(target.id)
                    elif isinstance(target, ast.Attribute):
                        # Track attribute assignments like self.value = x
                        attr_info = self._extract_attribute_assignment(target, child)
                        if attr_info:
                            attribute_assigns.append(attr_info)

            # Track parameter passing through function calls
            elif isinstance(child, ast.Call):
                call_args = self._extract_call_arguments(child)
                if call_args:
                    param_passing.extend(call_args)

        return {
            "reads": sorted(list(reads)),
            "writes": sorted(list(writes)),
            "param_passing": param_passing,
            "attribute_assigns": attribute_assigns,
            "attribute_reads": attribute_reads,
        }

    def _is_builtin(self, name):
        """
        Checks if a name is a Python builtin or common construct.
        """
        builtins = {
            "None",
            "True",
            "False",
            "int",
            "str",
            "list",
            "dict",
            "set",
            "tuple",
            "frozenset",
            "print",
            "len",
            "range",
            "getattr",
            "setattr",
            "isinstance",
            "hasattr",
            "type",
            "bool",
            "float",
            "complex",
            "abs",
            "all",
            "any",
            "bin",
            "chr",
            "dir",
            "divmod",
            "enumerate",
            "eval",
            "exec",
            "filter",
            "format",
            "hex",
            "id",
            "input",
            "isinstance",
            "issubclass",
            "iter",
            "locals",
            "map",
            "max",
            "min",
            "next",
            "oct",
            "open",
            "ord",
            "pow",
            "repr",
            "reversed",
            "round",
            "sorted",
            "sum",
            "vars",
            "zip",
            "Exception",
            "ValueError",
            "TypeError",
            "RuntimeError",
            "self",
            "cls",
        }
        return name in builtins

    def _extract_attribute_assignment(self, target, assignment_node):
        """
        Extracts information about an attribute assignment.

        Args:
            target: ast.Attribute node (e.g., self.value)
            assignment_node: The assignment node containing line number

        Returns:
            dict or None: Assignment information
        """
        if isinstance(target, ast.Attribute):
            obj_name = None

            # Get the object name
            if isinstance(target.value, ast.Name):
                obj_name = target.value.id
            elif isinstance(target.value, ast.Attribute):
                # Handle nested attributes like self.obj.value
                obj_name = "<nested>"

            return {
                "object": obj_name,
                "attribute": target.attr,
                "line_number": assignment_node.lineno,
                "is_self_attribute": obj_name == "self",
            }

        return None

    def _extract_attribute_read(self, attr_node):
        """
        Extracts information about an attribute read.

        Args:
            attr_node: ast.Attribute node (e.g., self.value)

        Returns:
            dict or None: Attribute read information
        """
        if isinstance(attr_node, ast.Attribute):
            obj_name = None

            # Get the object name
            if isinstance(attr_node.value, ast.Name):
                obj_name = attr_node.value.id
            elif isinstance(attr_node.value, ast.Attribute):
                # Handle nested attributes like self.obj.value
                obj_name = "<nested>"

            return {
                "object": obj_name,
                "attribute": attr_node.attr,
                "line_number": attr_node.lineno,
                "is_self_attribute": obj_name == "self",
            }

        return None

    def _extract_call_arguments(self, call_node):
        """
        Extracts information about arguments passed in a function call.

        Args:
            call_node: ast.Call node

        Returns:
            list: List of parameter passing information
        """
        param_info = []

        for arg in call_node.args:
            if isinstance(arg, ast.Name):
                param_info.append(
                    {
                        "variable": arg.id,
                        "line_number": call_node.lineno,
                        "is_positional": True,
                    }
                )

        # Handle keyword arguments
        for keyword in call_node.keywords:
            if isinstance(keyword.value, ast.Name):
                param_info.append(
                    {
                        "variable": keyword.value.id,
                        "parameter_name": keyword.arg,
                        "line_number": call_node.lineno,
                        "is_positional": False,
                    }
                )

        return param_info

    def get_data_flow_summary(self, function_name):
        """
        Returns a detailed data flow summary for a specific function.

        Args:
            function_name: Name of the function to analyze

        Returns:
            dict: Data flow summary or None if function not found
        """
        summary = self.get_summary()

        # Check top-level functions
        for func in summary["functions"]:
            if func["name"] == function_name:
                return func["data_flow"]

        # Check class methods
        for cls in summary["classes"]:
            for method in cls["methods"]:
                if method["name"] == function_name:
                    return method["data_flow"]

        return None

    def get_state_mutations(self):
        """
        Identifies all functions that modify mutable state (self attributes).

        Returns:
            list: List of functions that modify self attributes with details
        """
        mutations = []
        summary = self.get_summary()

        # Check top-level functions
        for func in summary["functions"]:
            state_changes = [
                a
                for a in func["data_flow"]["attribute_assigns"]
                if a["is_self_attribute"]
            ]
            if state_changes:
                mutations.append(
                    {
                        "function": func["name"],
                        "type": "function",
                        "state_changes": state_changes,
                    }
                )

        # Check class methods
        for cls in summary["classes"]:
            for method in cls["methods"]:
                state_changes = [
                    a
                    for a in method["data_flow"]["attribute_assigns"]
                    if a["is_self_attribute"]
                ]
                if state_changes:
                    mutations.append(
                        {
                            "class": cls["name"],
                            "function": method["name"],
                            "type": "method",
                            "state_changes": state_changes,
                        }
                    )

        return mutations

    def get_import_dependencies(self):
        """
        Parses import statements to track module-level dependencies.

        Returns:
            dict: Import dependencies including:
                - modules: List of imported module names (e.g., 'import os')
                - from_imports: Dict of module -> imported names (e.g., 'from ast import parse')
                - line_numbers: Dict of import -> line number where it appears
        """
        dependencies = {"modules": [], "from_imports": {}, "line_numbers": {}}

        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.Import):
                # Handle: import module1, module2
                for alias in node.names:
                    module_name = alias.name
                    dependencies["modules"].append(module_name)
                    dependencies["line_numbers"][module_name] = node.lineno

            elif isinstance(node, ast.ImportFrom):
                # Handle: from module import name1, name2
                module_name = node.module
                imported_names = []

                for alias in node.names:
                    if alias.name == "*":
                        imported_names.append("*")
                    else:
                        imported_names.append(alias.name)

                dependencies["from_imports"][module_name] = imported_names
                dependencies["line_numbers"][f"from {module_name}"] = node.lineno

        return dependencies

    def classify_imports(self, project_modules=None):
        """
        Classifies imports into project modules vs external packages.

        Args:
            project_modules: List of module names that belong to the project

        Returns:
            dict: Classified imports with 'internal' and 'external' categories
        """
        import_deps = self.get_import_dependencies()

        classified = {
            "internal": {"modules": [], "from_imports": {}},
            "external": {"modules": [], "from_imports": {}},
        }

        if project_modules is None:
            project_modules = []

        # Classify simple imports
        for module in import_deps["modules"]:
            if self._is_project_module(module, project_modules):
                classified["internal"]["modules"].append(module)
            else:
                classified["external"]["modules"].append(module)

        # Classify from imports
        for module, names in import_deps["from_imports"].items():
            if self._is_project_module(module, project_modules):
                classified["internal"]["from_imports"][module] = names
            else:
                classified["external"]["from_imports"][module] = names

        return classified

    def _is_project_module(self, module_name, project_modules):
        """
        Determines if a module belongs to the project or is external.

        Args:
            module_name: Name of the module to check
            project_modules: List of project module names

        Returns:
            bool: True if module belongs to the project
        """
        if not project_modules:
            return False

        # Check if module or any parent is in project modules
        module_parts = module_name.split(".")

        for i in range(len(module_parts)):
            partial = ".".join(module_parts[: i + 1])
            if partial in project_modules:
                return True

        return False

    def get_module_dependency_graph(self):
        """
        Builds a dependency graph showing which modules this file depends on.

        Returns:
            dict: Dependency graph with:
                - imports: Full list of all imports
                - external_packages: List of external package names
                - internal_modules: List of internal module names (if provided)
                - is_importing_star: Boolean indicating if any star imports exist
        """
        import_deps = self.get_import_dependencies()

        # Extract external package names (top-level module only)
        external_packages = set()
        internal_modules = set()
        has_star_import = False

        # Check simple imports
        for module in import_deps["modules"]:
            top_level = module.split(".")[0]
            # Skip standard library and built-in-like modules
            if not self._is_stdlib_module(top_level):
                external_packages.add(top_level)

        # Check from imports
        for module, names in import_deps["from_imports"].items():
            if "*" in names:
                has_star_import = True

            top_level = module.split(".")[0]
            if not self._is_stdlib_module(top_level):
                external_packages.add(top_level)

        return {
            "imports": import_deps,
            "external_packages": sorted(list(external_packages)),
            "internal_modules": sorted(list(internal_modules)),
            "is_importing_star": has_star_import,
        }

    def _extract_function_type_hints(self, node: ast.FunctionDef):
        """
        Extracts type hints from a function definition.

        Args:
            node: ast.FunctionDef node

        Returns:
            dict: Type hints including parameter types and return type
        """
        type_hints = {"parameters": {}, "return_type": None, "has_type_hints": False}

        # Extract parameter type hints
        for arg in node.args.args:
            if arg.annotation is not None:
                type_str = self._ast_type_to_string(arg.annotation)
                type_hints["parameters"][arg.arg] = type_str
                type_hints["has_type_hints"] = True

        # Extract return type hint
        if node.returns is not None:
            type_hints["return_type"] = self._ast_type_to_string(node.returns)
            type_hints["has_type_hints"] = True

        return type_hints

    def _extract_class_attribute_type_hint(self, node: ast.AnnAssign):
        """
        Extracts type hints from class attribute annotations.

        Args:
            node: ast.AnnAssign node (e.g., self.attr: int = 5)

        Returns:
            dict or None: Attribute type hint information
        """
        if node.annotation is not None:
            type_str = self._ast_type_to_string(node.annotation)

            # Extract attribute name
            attr_name = None
            if isinstance(node.target, ast.Name):
                attr_name = node.target.id
            elif isinstance(node.target, ast.Attribute):
                attr_name = node.target.attr

            if attr_name:
                return {
                    "name": attr_name,
                    "type": type_str,
                    "line_number": node.lineno,
                    "has_default": node.value is not None,
                }

        return None

    def _extract_annotations_dict(self, node):
        """
        Extracts type hints from an __annotations__ dictionary assignment.

        Args:
            node: ast.Dict node containing the __annotations__ dict

        Returns:
            dict: Mapping of attribute names to type strings
        """
        annotations = {}

        if isinstance(node, ast.Dict):
            keys = node.keys
            values = node.values

            for key, value in zip(keys, values):
                if isinstance(key, ast.Constant):
                    attr_name = key.value
                    type_str = self._ast_type_to_string(value)
                    if type_str:
                        annotations[attr_name] = {
                            "type": type_str,
                            "line_number": getattr(value, "lineno", key.lineno),
                        }

        return annotations

    def _ast_type_to_string(self, type_node):
        """
        Converts an AST type annotation node to a string representation.

        Args:
            type_node: AST node representing a type annotation

        Returns:
            str: String representation of the type
        """
        if type_node is None:
            return None

        # Simple name: int, str, List, etc.
        if isinstance(type_node, ast.Name):
            return type_node.id

        # Attribute: typing.List, collections.abc.Iterable, etc.
        elif isinstance(type_node, ast.Attribute):
            value_str = self._ast_type_to_string(type_node.value)
            return f"{value_str}.{type_node.attr}"

        # Subscript: List[int], Dict[str, int], Optional[int], etc.
        elif isinstance(type_node, ast.Subscript):
            base_str = self._ast_type_to_string(type_node.value)

            # Handle slice (the part in brackets)
            if isinstance(type_node.slice, ast.Tuple):
                # Multiple arguments: Dict[str, int]
                elements = [
                    self._ast_type_to_string(elt) for elt in type_node.slice.elts
                ]
                slice_str = ", ".join(elements)
            else:
                # Single argument: List[int]
                slice_str = self._ast_type_to_string(type_node.slice)

            return f"{base_str}[{slice_str}]"

        # Constant type (rare, but possible)
        elif isinstance(type_node, ast.Constant):
            return str(type_node.value)

        # Ellipsis (used in tuple types like Tuple[int, ...])
        elif isinstance(type_node, ast.Ellipsis):
            return "..."

        # BinOp for Union types (Python 3.9+)
        elif isinstance(type_node, ast.BinOp):
            left = self._ast_type_to_string(type_node.left)
            right = self._ast_type_to_string(type_node.right)
            op_str = " | " if isinstance(type_node.op, ast.BitOr) else " & "
            return f"{left}{op_str}{right}"

        # If we can't parse it, return None
        return None

    def _is_stdlib_module(self, module_name):
        """
        Checks if a module is part of the Python standard library.

        Args:
            module_name: Name of the module to check

        Returns:
            bool: True if it's a standard library module
        """
        # Common stdlib modules (not exhaustive, but covers most used)
        stdlib_modules = {
            "os",
            "sys",
            "re",
            "json",
            "math",
            "random",
            "datetime",
            "time",
            "collections",
            "itertools",
            "functools",
            "typing",
            "pathlib",
            "io",
            "csv",
            "pickle",
            "sqlite3",
            "logging",
            "unittest",
            "pytest",
            "argparse",
            "configparser",
            "hashlib",
            "base64",
            "urllib",
            "http",
            "email",
            "xml",
            "html",
            "ast",
            "inspect",
            "types",
            "copy",
            "weakref",
            "gc",
            "threading",
            "multiprocessing",
            "concurrent",
            "asyncio",
            "subprocess",
            "shutil",
            "tempfile",
            "glob",
            "fnmatch",
            "statistics",
            "fractions",
            "decimal",
            "enum",
            "dataclasses",
            "warnings",
            "traceback",
            "contextlib",
            "abc",
            "numbers",
            "string",
            "struct",
            "codecs",
            "textwrap",
            "difflib",
        }

        return module_name in stdlib_modules


def map_file(file_path):
    """
    Convenience function to map a file directly.
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        source = f.read()

    mapper = SemanticMapper(source)
    return mapper.get_summary()
