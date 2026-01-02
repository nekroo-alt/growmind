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
