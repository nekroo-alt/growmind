"""
Dead Code Detector Module (V5)

This module detects unused code in the codebase including dead functions,
classes, and variables.

Key Features:
- Identify functions that are never called
- Identify functions called only by tests
- Identify functions with zero or low call count
- Distinguish between public API functions vs internal functions
- Generate dead code report
- Suggest safe removal candidates
"""

import os
import ast
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from data.call_graph_persistence import CallGraphPersistence
from data.semantic_mapper import SemanticMapper


@dataclass
class DeadFunctionInfo:
    """Information about a dead function."""
    file_path: str
    function_name: str
    function_type: str  # 'function' or 'method'
    call_count: int
    is_public_api: bool
    is_test_only: bool
    confidence: str  # 'high', 'medium', 'low'
    reasons: List[str]
    suggestions: List[str]


@dataclass
class DeadClassInfo:
    """Information about a dead class."""
    file_path: str
    class_name: str
    instantiation_count: int
    is_abstract_base: bool
    is_mixin: bool
    has_subclasses: bool
    methods_count: int
    called_methods: Set[str]
    confidence: str
    reasons: List[str]
    suggestions: List[str]


@dataclass
class UnusedVariableInfo:
    """Information about an unused variable."""
    file_path: str
    variable_name: str
    scope: str  # 'local', 'class', 'module'
    line_number: int
    confidence: str
    reasons: List[str]
    suggestions: List[str]


class DeadCodeDetector:
    """
    Detects dead code in the codebase.
    """

    def __init__(
        self,
        project_root: str,
        call_graph_db: str = ".l4_cache/call_graph.db",
        low_usage_threshold: int = 3
    ):
        """
        Initialize DeadCodeDetector.

        Args:
            project_root: Root directory of project
            call_graph_db: Path to call graph database
            low_usage_threshold: Maximum call count to consider low usage
        """
        self.project_root = project_root
        self.low_usage_threshold = low_usage_threshold
        self.call_graph_persistence = CallGraphPersistence(call_graph_db)
        self.semantic_mapper = SemanticMapper(project_root)

    def detect_dead_functions(self, include_test_files: bool = False) -> List[DeadFunctionInfo]:
        """
        Identify functions that are never called.

        Args:
            include_test_files: Whether to include functions in test files

        Returns:
            List[DeadFunctionInfo]: List of dead functions
        """
        # Get all function usage statistics from call graph
        usage_stats = self.call_graph_persistence.get_usage_statistics()
        
        # Get all functions in the codebase
        all_functions = self._get_all_functions()
        
        # Build a lookup of called functions
        called_functions = set()
        test_files = set()
        
        for func in usage_stats:
            file_path = func['file_path']
            function_name = func['function_name']
            call_count = func['call_count']
            
            # Check if it's a test file
            if self._is_test_file(file_path):
                test_files.add(file_path)
            
            if call_count > 0:
                # Check who calls this function
                callers = self._get_function_callers(file_path, function_name)
                
                # Determine if it's called only by tests
                if callers and all(self._is_test_file(caller) for caller in callers):
                    # Test-only function
                    called_functions.add((file_path, function_name))
                elif not include_test_files and file_path in test_files:
                    # Skip test file functions
                    continue
                else:
                    called_functions.add((file_path, function_name))
        
        # Find dead functions
        dead_functions = []
        
        for (file_path, function_name, function_type) in all_functions:
            # Skip test files if not including them
            if not include_test_files and self._is_test_file(file_path):
                continue
            
            # Check if function is called
            is_called = (file_path, function_name) in called_functions
            
            # Check if it's part of public API
            is_public_api = self._is_public_api_function(file_path, function_name)
            
            # Check call count
            call_count = 0
            for func in usage_stats:
                if func['file_path'] == file_path and func['function_name'] == function_name:
                    call_count = func['call_count']
                    break
            
            # Determine if dead
            if call_count == 0 and not is_public_api:
                # Never called, not in public API
                dead_functions.append(self._create_dead_function_info(
                    file_path, function_name, function_type, 
                    call_count, is_public_api, test_only=False
                ))
            elif call_count == 0 and is_public_api:
                # Never called, but in public API
                dead_functions.append(self._create_dead_function_info(
                    file_path, function_name, function_type,
                    call_count, is_public_api, test_only=False
                ))
            elif 0 < call_count <= self.low_usage_threshold and not is_public_api:
                # Low usage
                callers = self._get_function_callers(file_path, function_name)
                is_test_only = callers and all(self._is_test_file(caller) for caller in callers)
                dead_functions.append(self._create_dead_function_info(
                    file_path, function_name, function_type,
                    call_count, is_public_api, is_test_only
                ))
        
        return dead_functions

    def detect_dead_classes(self, include_test_files: bool = False) -> List[DeadClassInfo]:
        """
        Identify classes that are never instantiated.

        Args:
            include_test_files: Whether to include classes in test files

        Returns:
            List[DeadClassInfo]: List of dead classes
        """
        # Get all classes in the codebase
        all_classes = self._get_all_classes()
        
        # Get call graph to track instantiations
        call_graph = self.call_graph_persistence.get_call_graph()
        
        # Build a lookup of called classes
        called_classes = set()
        class_method_calls = {}  # (file, class) -> set of called methods
        
        for caller, callees in call_graph.items():
            caller_file, caller_func = caller.split(':', 1) if ':' in caller else (caller, '')
            
            for callee_info in callees:
                callee = callee_info['callee']
                # Try to parse as method call: ClassName.method
                if '.' in callee:
                    class_name, method_name = callee.rsplit('.', 1)
                    # Record that this class's method was called
                    key = (caller_file, class_name)
                    if key not in class_method_calls:
                        class_method_calls[key] = set()
                    class_method_calls[key].add(method_name)
        
        # Find dead classes
        dead_classes = []
        
        for (file_path, class_name, methods) in all_classes:
            # Skip test files if not including them
            if not include_test_files and self._is_test_file(file_path):
                continue
            
            # Check if class is instantiated or methods are called
            key = (file_path, class_name)
            called_methods = class_method_calls.get(key, set())
            
            # Determine if dead
            if len(called_methods) == 0:
                # No methods called
                dead_classes.append(self._create_dead_class_info(
                    file_path, class_name, methods, 
                    called_methods, is_abstract=False
                ))
            elif len(called_methods) < len(methods) * 0.3:
                # Very few methods called (<30%)
                dead_classes.append(self._create_dead_class_info(
                    file_path, class_name, methods,
                    called_methods, is_abstract=False
                ))
        
        return dead_classes

    def detect_unused_variables(self, include_test_files: bool = False) -> List[UnusedVariableInfo]:
        """
        Identify unused variables in Python code.

        Args:
            include_test_files: Whether to include variables in test files

        Returns:
            List[UnusedVariableInfo]: List of unused variables
        """
        unused_variables = []
        
        # Find all Python files
        python_files = self._find_python_files(self.project_root, recursive=True)
        
        for file_path in python_files:
            # Skip test files if not including them
            if not include_test_files and self._is_test_file(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                # Parse AST
                tree = ast.parse(source_code, filename=file_path)
                
                # Detect unused variables
                file_unused = self._detect_unused_variables_in_file(tree, file_path)
                unused_variables.extend(file_unused)
                
            except Exception as e:
                # Skip files that can't be parsed
                continue
        
        return unused_variables

    def generate_dead_function_report(self, format: str = "text") -> str:
        """
        Generate dead function detection report.

        Args:
            format: Report format ('text', 'json', 'markdown')

        Returns:
            str: Generated report
        """
        dead_functions = self.detect_dead_functions()
        
        if format == "json":
            import json
            return json.dumps(
                [self._dead_function_to_dict(f) for f in dead_functions],
                indent=2,
                default=str
            )
        elif format == "markdown":
            return self._generate_dead_functions_markdown(dead_functions)
        else:
            return self._generate_dead_functions_text(dead_functions)

    def _get_all_functions(self) -> List[Tuple[str, str, str]]:
        """
        Get all functions in the codebase.

        Returns:
            List[Tuple]: (file_path, function_name, function_type)
        """
        all_functions = []
        python_files = self._find_python_files(self.project_root, recursive=True)
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                tree = ast.parse(source_code, filename=file_path)
                
                for node in ast.walk(tree):
                    # Function definitions
                    if isinstance(node, ast.FunctionDef):
                        func_type = 'function'
                        # Check if it's a method
                        if isinstance(node.col_offset, int):  # Has indentation
                            func_type = 'method'
                        
                        all_functions.append((file_path, node.name, func_type))
                    
                    # Async function definitions
                    elif isinstance(node, ast.AsyncFunctionDef):
                        func_type = 'function'
                        all_functions.append((file_path, node.name, func_type))
                        
            except Exception:
                continue
        
        return all_functions

    def _get_all_classes(self) -> List[Tuple[str, str, List[str]]]:
        """
        Get all classes in the codebase.

        Returns:
            List[Tuple]: (file_path, class_name, list_of_methods)
        """
        all_classes = []
        python_files = self._find_python_files(self.project_root, recursive=True)
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                tree = ast.parse(source_code, filename=file_path)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Get methods
                        methods = []
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                methods.append(item.name)
                        
                        all_classes.append((file_path, node.name, methods))
                        
            except Exception:
                continue
        
        return all_classes

    def _get_function_callers(self, file_path: str, function_name: str) -> List[str]:
        """
        Get files that call a specific function.

        Args:
            file_path: Path to function's file
            function_name: Name of function

        Returns:
            List[str]: List of caller file paths
        """
        call_graph = self.call_graph_persistence.get_call_graph()
        callers = []
        
        for caller, callees in call_graph.items():
            caller_file = caller.split(':', 1)[0] if ':' in caller else caller
            for callee_info in callees:
                if callee_info['callee'] == function_name:
                    callers.append(caller_file)
        
        return callers

    def _is_public_api_function(self, file_path: str, function_name: str) -> bool:
        """
        Check if function is part of public API.

        Args:
            file_path: Path to function's file
            function_name: Name of function

        Returns:
            bool: True if part of public API
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=file_path)
            
            # Check for __all__ export
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == '__all__':
                            # Check if function is in __all__
                            if isinstance(node.value, (ast.List, ast.Tuple)):
                                for elt in ast.walk(node.value):
                                    if isinstance(elt, ast.Constant) and elt.value == function_name:
                                        return True
            
            # Check if exported in __init__.py
            if file_path.endswith('__init__.py'):
                return True
            
            return False
            
        except Exception:
            return False

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        return 'test' in os.path.basename(file_path).lower()

    def _create_dead_function_info(
        self,
        file_path: str,
        function_name: str,
        function_type: str,
        call_count: int,
        is_public_api: bool,
        test_only: bool
    ) -> DeadFunctionInfo:
        """
        Create DeadFunctionInfo object.

        Args:
            file_path: Path to function's file
            function_name: Name of function
            function_type: Type of function
            call_count: Number of calls
            is_public_api: Whether it's part of public API
            test_only: Whether it's called only by tests

        Returns:
            DeadFunctionInfo: Dead function information
        """
        reasons = []
        suggestions = []
        
        if call_count == 0:
            reasons.append("Function is never called")
        elif call_count <= self.low_usage_threshold:
            reasons.append(f"Function called only {call_count} time(s)")
        
        if is_public_api:
            reasons.append("Function is exported in __all__ or is in __init__.py")
        
        if test_only:
            reasons.append("Function is called only by test files")
        
        # Determine confidence
        if call_count == 0 and not is_public_api:
            confidence = 'high'
            suggestions.append("Consider removing this function")
        elif call_count == 0 and is_public_api:
            confidence = 'medium'
            suggestions.append("Review if function is still needed in public API")
        elif test_only:
            confidence = 'medium'
            suggestions.append("Consider if function is needed in production")
        else:
            confidence = 'low'
            suggestions.append("Review before removing - may be used in future")
        
        return DeadFunctionInfo(
            file_path=file_path,
            function_name=function_name,
            function_type=function_type,
            call_count=call_count,
            is_public_api=is_public_api,
            is_test_only=test_only,
            confidence=confidence,
            reasons=reasons,
            suggestions=suggestions
        )

    def _create_dead_class_info(
        self,
        file_path: str,
        class_name: str,
        methods: List[str],
        called_methods: Set[str],
        is_abstract: bool
    ) -> DeadClassInfo:
        """Create DeadClassInfo object."""
        reasons = []
        suggestions = []
        
        if len(called_methods) == 0:
            reasons.append("No methods of this class are called")
            confidence = 'high'
            suggestions.append("Consider removing this class")
        elif len(called_methods) < len(methods) * 0.3:
            reasons.append(f"Only {len(called_methods)} of {len(methods)} methods are called")
            confidence = 'medium'
            suggestions.append("Review which methods are actually needed")
        
        return DeadClassInfo(
            file_path=file_path,
            class_name=class_name,
            instantiation_count=0,
            is_abstract_base=is_abstract,
            is_mixin=False,
            has_subclasses=False,
            methods_count=len(methods),
            called_methods=called_methods,
            confidence=confidence,
            reasons=reasons,
            suggestions=suggestions
        )

    def _detect_unused_variables_in_file(
        self,
        tree: ast.AST,
        file_path: str
    ) -> List[UnusedVariableInfo]:
        """
        Detect unused variables in a single file.

        Args:
            tree: AST tree
            file_path: Path to file

        Returns:
            List[UnusedVariableInfo]: Unused variables
        """
        unused = []
        
        # Collect all assignments and their scopes
        assignments = []  # (name, line_number, scope)
        references = set()
        
        for node in ast.walk(tree):
            # Variable assignments
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # Skip special variables
                        if not self._is_special_variable(name):
                            assignments.append((name, node.lineno, 'local'))
            
            # Variable references
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    references.add(node.id)
            
            # For loops
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    if not self._is_special_variable(node.target.id):
                        # Loop variables are often used, skip them
                        pass
            
            # Comprehensions
            elif isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp)):
                for generator in node.generators:
                    if isinstance(generator.target, ast.Name):
                        if not self._is_special_variable(generator.target.id):
                            # Comprehension variables are often used, skip them
                            pass
        
        # Find unused variables
        for name, line_number, scope in assignments:
            if name not in references:
                unused.append(UnusedVariableInfo(
                    file_path=file_path,
                    variable_name=name,
                    scope=scope,
                    line_number=line_number,
                    confidence='high',
                    reasons=[f"Variable '{name}' is assigned but never used"],
                    suggestions=["Consider removing this variable"]
                ))
        
        return unused

    def _is_special_variable(self, name: str) -> bool:
        """Check if variable name is special (should not be flagged)."""
        special_names = {
            '__name__', '__file__', '__package__', '__loader__',
            '__spec__', '__builtins__', '__path__',
            '__all__', '__version__', '__author__',
            '__doc__', 'self', 'cls', '_'
        }
        return name in special_names or name.startswith('_')

    def _find_python_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Find all Python files in directory."""
        python_files = []
        
        if recursive:
            for root, dirs, files in os.walk(directory):
                # Skip common directories to ignore
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'venv', 'node_modules']]
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if file.endswith('.py'):
                    python_files.append(os.path.join(directory, file))
        
        return python_files

    def _dead_function_to_dict(self, func: DeadFunctionInfo) -> Dict:
        """Convert DeadFunctionInfo to dictionary."""
        return {
            "file_path": func.file_path,
            "function_name": func.function_name,
            "function_type": func.function_type,
            "call_count": func.call_count,
            "is_public_api": func.is_public_api,
            "is_test_only": func.is_test_only,
            "confidence": func.confidence,
            "reasons": func.reasons,
            "suggestions": func.suggestions
        }

    def _generate_dead_functions_text(self, dead_functions: List[DeadFunctionInfo]) -> str:
        """Generate text format report for dead functions."""
        lines = []
        lines.append("=" * 70)
        lines.append("DEAD FUNCTION DETECTION REPORT")
        lines.append("=" * 70)
        lines.append(f"Total Dead Functions: {len(dead_functions)}")
        lines.append("")
        
        # Count by confidence
        high_conf = sum(1 for f in dead_functions if f.confidence == 'high')
        medium_conf = sum(1 for f in dead_functions if f.confidence == 'medium')
        low_conf = sum(1 for f in dead_functions if f.confidence == 'low')
        
        lines.append("Confidence Breakdown:")
        lines.append(f"  High: {high_conf}")
        lines.append(f"  Medium: {medium_conf}")
        lines.append(f"  Low: {low_conf}")
        lines.append("")
        
        # Dead functions
        if dead_functions:
            lines.append("DEAD FUNCTIONS:")
            lines.append("-" * 70)
            for func in dead_functions[:50]:  # Limit to first 50
                file_name = os.path.basename(func.file_path)
                lines.append(f"  {func.function_name} ({file_name})")
                lines.append(f"    Confidence: {func.confidence}, Calls: {func.call_count}")
                if func.reasons:
                    lines.append(f"    Reasons:")
                    for reason in func.reasons[:2]:
                        lines.append(f"      - {reason}")
                if func.suggestions:
                    lines.append(f"    Suggestion: {func.suggestions[0]}")
            if len(dead_functions) > 50:
                lines.append(f"  ... and {len(dead_functions) - 50} more")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)

    def _generate_dead_functions_markdown(self, dead_functions: List[DeadFunctionInfo]) -> str:
        """Generate markdown format report for dead functions."""
        lines = []
        lines.append("# Dead Function Detection Report")
        lines.append("")
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Dead Functions**: {len(dead_functions)}")
        
        high_conf = sum(1 for f in dead_functions if f.confidence == 'high')
        medium_conf = sum(1 for f in dead_functions if f.confidence == 'medium')
        low_conf = sum(1 for f in dead_functions if f.confidence == 'low')
        
        lines.append(f"- **High Confidence**: {high_conf}")
        lines.append(f"- **Medium Confidence**: {medium_conf}")
        lines.append(f"- **Low Confidence**: {low_conf}")
        lines.append("")
        
        # Dead functions table
        if dead_functions:
            lines.append("## Dead Functions")
            lines.append("")
            lines.append("| Function | File | Calls | Confidence | Reason |")
            lines.append("|----------|------|-------|------------|--------|")
            for func in dead_functions[:50]:
                file_name = os.path.basename(func.file_path)
                reason = func.reasons[0] if func.reasons else "N/A"
                lines.append(f"| {func.function_name} | {file_name} | {func.call_count} | {func.confidence} | {reason} |")
            if len(dead_functions) > 50:
                lines.append(f"| ... | ... | ... | ... | and {len(dead_functions) - 50} more |")
            lines.append("")
        
        return "\n".join(lines)