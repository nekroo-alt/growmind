"""
Complexity Estimator Module

Analyzes code complexity to help with task estimation and decision-making.
Computes cyclomatic complexity and estimates task effort based on code structure.
"""

import ast
from typing import Dict, List, Optional, Any
from v3.data.semantic_mapper import SemanticMapper


class ComplexityEstimator:
    """
    Estimates code complexity using AST analysis to help with task planning.

    Uses cyclomatic complexity metrics to:
    - Calculate individual function/method complexity
    - Aggregate class-level complexity
    - Estimate task effort
    - Flag complex code that needs breaking down
    """

    # Complexity thresholds based on industry standards
    COMPLEXITY_LEVELS = {
        "simple": (1, 5),
        "moderate": (6, 10),
        "complex": (11, 20),
        "very_complex": (21, float("inf")),
    }

    def __init__(self, semantic_mapper: SemanticMapper):
        """
        Initialize the complexity estimator with a semantic mapper.

        Args:
            semantic_mapper: SemanticMapper instance with AST data
        """
        self.mapper = semantic_mapper
        # Add parent references to AST nodes for easier navigation
        self._add_parent_refs(self.mapper.tree)

    def _add_parent_refs(self, node: ast.AST, parent: Optional[ast.AST] = None):
        """
        Add parent references to all AST nodes for navigation.

        Args:
            node: AST node to process
            parent: Parent AST node
        """
        node.parent = parent
        for child in ast.iter_child_nodes(node):
            self._add_parent_refs(child, node)

    def calculate_function_complexity(self, function_name: str) -> Dict[str, Any]:
        """
        Calculate cyclomatic complexity for a specific function or method.

        Args:
            function_name: Name of the function to analyze

        Returns:
            dict: Complexity information including:
                - complexity: Integer complexity score
                - level: Complexity level (simple/moderate/complex/very_complex)
                - decision_points: List of decision point locations
                - line_count: Number of lines in the function
        """
        summary = self.mapper.get_summary()

        # Search for the function
        func_node = None
        func_type = None
        parent_class = None

        # Check top-level functions
        for func in summary["functions"]:
            if func["name"] == function_name:
                func_node = func
                func_type = "function"
                break

        # Check class methods (if not found as a top-level function)
        if not func_node:
            for cls in summary["classes"]:
                for method in cls["methods"]:
                    if method["name"] == function_name:
                        func_node = method
                        func_type = "method"
                        parent_class = cls["name"]
                        break
                if func_node:
                    break

        if not func_node:
            return None

        # Use the full AST to find the function node and analyze it in context
        # This avoids syntax errors when parsing methods that reference 'self'
        func_ast_node = None
        for node in ast.walk(self.mapper.tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                # For methods, also check if we're in the right class
                if parent_class:
                    # Walk up to find the parent class
                    current = node
                    while hasattr(current, "parent"):
                        current = getattr(current, "parent", None)
                        if (
                            isinstance(current, ast.ClassDef)
                            and current.name == parent_class
                        ):
                            func_ast_node = node
                            break
                else:
                    # Top-level function
                    func_ast_node = node
                break

        if not func_ast_node:
            return {
                "name": function_name,
                "type": func_type,
                "complexity": -1,
                "level": "unknown",
                "error": "Function not found in AST",
            }

        decision_points = self._count_decision_points(func_ast_node)
        complexity = 1 + len(decision_points)  # Base complexity + decision points

        # Determine complexity level
        level = self._get_complexity_level(complexity)

        # Get line count from the func_node metadata
        start_line = func_node["start_line"]
        end_line = func_node["end_line"]

        return {
            "name": function_name,
            "type": func_type,
            "parent_class": parent_class,
            "complexity": complexity,
            "level": level,
            "decision_points": decision_points,
            "line_count": end_line - start_line + 1,
            "start_line": start_line,
            "end_line": end_line,
        }

    def calculate_class_complexity(self, class_name: str) -> Dict[str, Any]:
        """
        Calculate aggregated complexity for a class.

        Args:
            class_name: Name of the class to analyze

        Returns:
            dict: Class complexity including:
                - total_complexity: Sum of all method complexities
                - average_complexity: Average method complexity
                - max_complexity: Highest method complexity
                - method_count: Number of methods
                - attribute_count: Number of attributes
        """
        summary = self.mapper.get_summary()

        # Find the class
        class_node = None
        for cls in summary["classes"]:
            if cls["name"] == class_name:
                class_node = cls
                break

        if not class_node:
            return None

        total_complexity = 0
        method_complexities = []

        # Calculate complexity for each method
        for method in class_node["methods"]:
            method_name = method["name"]
            complexity_info = self.calculate_function_complexity(method_name)

            if complexity_info and complexity_info["complexity"] > 0:
                method_complexity = complexity_info["complexity"]
                method_complexities.append(
                    {
                        "name": method_name,
                        "complexity": method_complexity,
                        "level": complexity_info["level"],
                    }
                )
                total_complexity += method_complexity

        # Calculate statistics
        method_count = len(method_complexities)
        average_complexity = total_complexity / method_count if method_count > 0 else 0
        max_complexity = (
            max([m["complexity"] for m in method_complexities])
            if method_complexities
            else 0
        )

        # Attribute count (from type hints)
        attribute_count = len(class_node.get("attribute_type_hints", {}))

        return {
            "name": class_name,
            "total_complexity": total_complexity,
            "average_complexity": round(average_complexity, 2),
            "max_complexity": max_complexity,
            "method_count": method_count,
            "attribute_count": attribute_count,
            "method_complexities": method_complexities,
        }

    def estimate_task_complexity(
        self, affected_entities: List[str], semantic_map: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Estimate complexity for a task based on affected code entities.

        Args:
            affected_entities: List of function/class names affected by the task
            semantic_map: Optional semantic map for context

        Returns:
            dict: Task complexity estimate including:
                - total_complexity: Combined complexity score
                - estimated_effort: Effort level (easy/medium/hard/very_hard)
                - likely_exceeds_limit: Boolean if likely to exceed 30 lines
                - risk_factors: List of complexity risk factors
        """
        if not affected_entities:
            return {
                "total_complexity": 0,
                "estimated_effort": "trivial",
                "likely_exceeds_limit": False,
                "risk_factors": [],
            }

        total_complexity = 0
        complexities = []
        risk_factors = []

        for entity in affected_entities:
            # Try as function first
            func_complexity = self.calculate_function_complexity(entity)
            if func_complexity:
                complexities.append(func_complexity)
                total_complexity += func_complexity["complexity"]

                # Check for risk factors
                if func_complexity["complexity"] > 10:
                    risk_factors.append(
                        f"High complexity function: {entity} ({func_complexity['complexity']})"
                    )
                continue

            # Try as class
            class_complexity = self.calculate_class_complexity(entity)
            if class_complexity:
                complexities.append(class_complexity)
                total_complexity += class_complexity["total_complexity"]

                # Check for risk factors
                if class_complexity["average_complexity"] > 10:
                    risk_factors.append(f"High complexity class: {entity}")
                if class_complexity["method_count"] > 7:
                    risk_factors.append(f"Large class with many methods: {entity}")

        # Estimate effort level
        estimated_effort = self._estimate_effort_level(
            total_complexity, len(complexities)
        )

        # Predict if task will exceed 30-line limit
        likely_exceeds_limit = self._will_exceed_limit(total_complexity)

        return {
            "affected_entities": affected_entities,
            "entity_count": len(affected_entities),
            "total_complexity": total_complexity,
            "individual_complexities": complexities,
            "estimated_effort": estimated_effort,
            "likely_exceeds_limit": likely_exceeds_limit,
            "risk_factors": risk_factors,
        }

    def will_exceed_line_limit(
        self, entity_names: List[str], threshold: int = 30
    ) -> Dict[str, Any]:
        """
        Check if modifications to given entities will likely exceed line limit.

        Args:
            entity_names: List of function/class names to check
            threshold: Line limit threshold (default: 30)

        Returns:
            dict: Prediction including:
                - will_exceed: Boolean prediction
                - confidence: Confidence level (low/medium/high)
                - reasoning: Explanation of the prediction
                - suggested_action: Recommendation
        """
        total_complexity = 0
        existing_lines = 0

        for entity in entity_names:
            func_complexity = self.calculate_function_complexity(entity)
            if func_complexity:
                total_complexity += func_complexity["complexity"]
                existing_lines += func_complexity["line_count"]
                continue

            class_complexity = self.calculate_class_complexity(entity)
            if class_complexity:
                total_complexity += class_complexity["total_complexity"]
                # Estimate class modification will touch multiple methods
                existing_lines += (
                    class_complexity["method_count"] * 5
                )  # Conservative estimate

        # Estimate: existing lines + complexity * 2 for new/modified code
        estimated_new_lines = existing_lines + (total_complexity * 1.5)

        will_exceed = estimated_new_lines > threshold

        # Determine confidence based on complexity
        if total_complexity > 15:
            confidence = "high"
        elif total_complexity > 8:
            confidence = "medium"
        else:
            confidence = "low"

        if will_exceed:
            suggested_action = "break_down"
            reasoning = f"Estimated {estimated_new_lines} lines (complexity: {total_complexity}) will exceed {threshold} line limit"
        else:
            suggested_action = "proceed"
            reasoning = f"Estimated {estimated_new_lines} lines (complexity: {total_complexity}) is within {threshold} line limit"

        return {
            "entity_names": entity_names,
            "will_exceed": will_exceed,
            "confidence": confidence,
            "estimated_lines": estimated_new_lines,
            "total_complexity": total_complexity,
            "reasoning": reasoning,
            "suggested_action": suggested_action,
        }

    def get_refactoring_suggestions(
        self, complexity_threshold: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Identify complex code that should be refactored.

        Args:
            complexity_threshold: Complexity threshold above which to suggest refactoring

        Returns:
            list: List of refactoring suggestions
        """
        summary = self.mapper.get_summary()
        suggestions = []

        # Check functions
        for func in summary["functions"]:
            complexity_info = self.calculate_function_complexity(func["name"])
            if complexity_info and complexity_info["complexity"] > complexity_threshold:
                suggestions.append(
                    {
                        "type": "function",
                        "name": func["name"],
                        "complexity": complexity_info["complexity"],
                        "line_count": complexity_info["line_count"],
                        "suggestion": f"Break down function '{func['name']}' (complexity: {complexity_info['complexity']}) into smaller functions",
                        "reason": "High cyclomatic complexity indicates multiple decision points",
                    }
                )

        # Check classes
        for cls in summary["classes"]:
            class_complexity = self.calculate_class_complexity(cls["name"])
            if class_complexity:
                if class_complexity["average_complexity"] > complexity_threshold:
                    suggestions.append(
                        {
                            "type": "class",
                            "name": cls["name"],
                            "complexity": class_complexity["average_complexity"],
                            "suggestion": f"Simplify class '{cls['name']}' or extract sub-classes",
                            "reason": f"Average method complexity is {class_complexity['average_complexity']}",
                        }
                    )

                if class_complexity["method_count"] > 7:
                    suggestions.append(
                        {
                            "type": "class",
                            "name": cls["name"],
                            "method_count": class_complexity["method_count"],
                            "suggestion": f"Extract some methods from class '{cls['name']}' into helper classes",
                            "reason": f"Class has {class_complexity['method_count']} methods, consider splitting",
                        }
                    )

                # Check individual high-complexity methods
                for method_info in class_complexity["method_complexities"]:
                    if method_info["complexity"] > complexity_threshold:
                        suggestions.append(
                            {
                                "type": "method",
                                "name": f"{cls['name']}.{method_info['name']}",
                                "complexity": method_info["complexity"],
                                "suggestion": f"Refactor method '{method_info['name']}' in class '{cls['name']}'",
                                "reason": f"Method complexity ({method_info['complexity']}) exceeds threshold",
                            }
                        )

        return suggestions

    def _count_decision_points(self, node: ast.AST) -> List[Dict[str, int]]:
        """
        Count decision points in an AST node.

        Args:
            node: AST node to analyze

        Returns:
            list: List of decision point locations with type and line number
        """
        decision_points = []

        for child in ast.walk(node):
            location = {"line_number": getattr(child, "lineno", 0), "type": None}

            if isinstance(child, (ast.If, ast.While)):
                location["type"] = "if/while"
                decision_points.append(location)
            elif isinstance(child, ast.For):
                location["type"] = "for"
                decision_points.append(location)
            elif isinstance(child, ast.ExceptHandler):
                location["type"] = "except"
                decision_points.append(location)
            elif isinstance(child, ast.BoolOp):
                # 'and' / 'or' operators
                location["type"] = "bool_op"
                decision_points.append(location)
            elif isinstance(
                child, ast.IfExp
            ):  # Ternary expression: x if condition else y
                location["type"] = "ternary"
                decision_points.append(location)

        return decision_points

    def _get_complexity_level(self, complexity: int) -> str:
        """
        Get the complexity level string for a complexity score.

        Args:
            complexity: Complexity score

        Returns:
            str: Complexity level (simple/moderate/complex/very_complex)
        """
        for level, (min_val, max_val) in self.COMPLEXITY_LEVELS.items():
            if min_val <= complexity <= max_val:
                return level
        return "unknown"

    def _estimate_effort_level(self, total_complexity: int, entity_count: int) -> str:
        """
        Estimate effort level based on complexity and number of entities.

        Args:
            total_complexity: Total complexity score
            entity_count: Number of entities affected

        Returns:
            str: Effort level (trivial/easy/medium/hard/very_hard)
        """
        if total_complexity == 0:
            return "trivial"
        elif total_complexity <= 5 and entity_count <= 2:
            return "easy"
        elif total_complexity <= 15 and entity_count <= 4:
            return "medium"
        elif total_complexity <= 25 and entity_count <= 6:
            return "hard"
        else:
            return "very_hard"

    def _will_exceed_limit(self, complexity: int, threshold: int = 30) -> bool:
        """
        Predict if complexity will exceed line limit.

        Args:
            complexity: Complexity score
            threshold: Line limit threshold

        Returns:
            bool: True if likely to exceed limit
        """
        # Rule of thumb: each decision point adds ~2 lines of code
        estimated_lines = complexity * 2
        return estimated_lines > threshold


def analyze_file_complexity(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to analyze complexity of an entire file.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        dict: Comprehensive complexity analysis
    """
    from v3.data.semantic_mapper import map_file

    summary = map_file(file_path)
    if not summary:
        return None

    # We need to create a SemanticMapper instance
    with open(file_path, "r") as f:
        source = f.read()

    mapper = SemanticMapper(source)
    estimator = ComplexityEstimator(mapper)

    # Analyze all functions
    function_complexities = []
    for func in summary["functions"]:
        complexity = estimator.calculate_function_complexity(func["name"])
        if complexity:
            function_complexities.append(complexity)

    # Analyze all classes
    class_complexities = []
    for cls in summary["classes"]:
        complexity = estimator.calculate_class_complexity(cls["name"])
        if complexity:
            class_complexities.append(complexity)

    # Get refactoring suggestions
    suggestions = estimator.get_refactoring_suggestions()

    return {
        "file_path": file_path,
        "function_count": len(function_complexities),
        "class_count": len(class_complexities),
        "function_complexities": function_complexities,
        "class_complexities": class_complexities,
        "refactoring_suggestions": suggestions,
    }
