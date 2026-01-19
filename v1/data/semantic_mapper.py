import ast
import os


class SemanticMapper:
    """
    Parses Python source code using the AST module to create a semantic map of the file.
    """

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.lines = source_code.splitlines()
        self.call_graph = None  # Will be built on demand

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

    def get_call_graph(self, max_depth=10):
        """
        Builds and returns a call graph showing which functions call which.
        
        Returns:
            dict: Call graph where keys are caller functions and values are lists
                  of called functions with metadata (callee, line_number, call_depth)
        """
        if self.call_graph is None:
            self.call_graph = self._build_call_graph(max_depth)
        return self.call_graph

    def _parse_class(self, node: ast.ClassDef):
        """
        Extracts information about a class definition.
        """
        methods = []
        dependencies = set()

        # Base classes are dependencies
        for base in node.bases:
            if isinstance(base, ast.Name):
                dependencies.add(base.id)
            elif isinstance(base, ast.Attribute):
                dependencies.add(base.attr)

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(self._parse_function(item))

        return {
            "name": node.name,
            "type": "class",
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "docstring": ast.get_docstring(node),
            "methods": methods,
            "dependencies": sorted(list(dependencies)),
        }

    def _parse_function(self, node: ast.FunctionDef):
        """
        Extracts information about a function or method definition.
        """
        args = [arg.arg for arg in node.args.args]
        dependencies = self._get_dependencies(node)
        return {
            "name": node.name,
            "type": "function",
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "docstring": ast.get_docstring(node),
            "args": args,
            "dependencies": dependencies,
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
                "context": None
            }
        
        # Add class methods
        for cls in summary["classes"]:
            for method in cls["methods"]:
                all_methods_key = f"{cls['name']}.{method['name']}"
                all_functions[method["name"]] = {
                    "type": "method",
                    "node": method,
                    "context": cls["name"]
                }
                all_functions[all_methods_key] = {
                    "type": "method",
                    "node": method,
                    "context": cls["name"]
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
            source = "\n".join(self.lines[func_node["start_line"] - 1 : func_node["end_line"]])
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
                "call_depth": 1  # Direct call, depth 1
            }
        
        return None


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
