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

from v5.data import CallGraphPersistence
from v5.data import SemanticMapper


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
        Identify classes that are never instantiated or have unused methods.

        This method detects:
        - Classes that are never instantiated
        - Classes with methods that are never called
        - Classes inherited from but never directly used
        - Abstract base classes (distinguished from dead classes)
        - Mixin classes (used for inheritance, not instantiation)

        Args:
            include_test_files: Whether to include classes in test files

        Returns:
            List[DeadClassInfo]: List of potentially dead classes
        """
        # Get all classes in the codebase with their metadata
        all_classes = self._get_all_classes_with_metadata()
        
        # Get call graph to track instantiations and method calls
        call_graph = self.call_graph_persistence.get_call_graph()
        
        # Build lookup structures
        class_instantiations = {}  # (file, class) -> count
        class_method_calls = {}  # (file, class) -> set of called methods
        subclass_relationships = {}  # (file, class) -> set of (file, subclass)
        
        # Analyze call graph
        for caller, callees in call_graph.items():
            caller_file = caller.split(':', 1)[0] if ':' in caller else caller
            
            for callee_info in callees:
                callee = callee_info['callee']
                
                # Check for class instantiation: ClassName()
                if '(' in callee and not '.' in callee:
                    class_name = callee.replace('()', '').strip()
                    key = (caller_file, class_name)
                    class_instantiations[key] = class_instantiations.get(key, 0) + 1
                
                # Check for method calls: ClassName.method
                elif '.' in callee:
                    parts = callee.rsplit('.', 1)
                    if len(parts) == 2:
                        class_name, method_name = parts
                        key = (caller_file, class_name)
                        if key not in class_method_calls:
                            class_method_calls[key] = set()
                        class_method_calls[key].add(method_name)
        
        # Build subclass relationships by analyzing inheritance
        subclass_relationships = self._detect_subclass_relationships(all_classes)
        
        # Find potentially dead classes
        dead_classes = []
        
        for class_info in all_classes:
            file_path = class_info['file_path']
            class_name = class_info['class_name']
            methods = class_info['methods']
            base_classes = class_info['base_classes']
            is_abstract = class_info['is_abstract']
            
            # Skip test files if not including them
            if not include_test_files and self._is_test_file(file_path):
                continue
            
            # Get call statistics
            key = (file_path, class_name)
            instantiation_count = class_instantiations.get(key, 0)
            called_methods = class_method_calls.get(key, set())
            has_subclasses = bool(subclass_relationships.get(key, set()))
            
            # Check if it's a mixin (has no state, only methods)
            is_mixin = self._is_mixin_class(class_info)
            
            # Determine if dead
            if is_abstract and has_subclasses:
                # Abstract base class with subclasses - not dead, expected behavior
                continue
            elif is_mixin and has_subclasses:
                # Mixin with subclasses - not dead, used for inheritance
                continue
            elif not is_abstract and instantiation_count == 0 and not has_subclasses:
                # Never instantiated, no subclasses - dead class
                dead_classes.append(self._create_dead_class_info(
                    file_path, class_name, methods,
                    called_methods, is_abstract=is_abstract,
                    is_mixin=is_mixin, has_subclasses=has_subclasses,
                    instantiation_count=instantiation_count,
                    base_classes=base_classes
                ))
            elif not is_abstract and instantiation_count > 0 and len(called_methods) < len(methods) * 0.3:
                # Instantiated but very few methods called (<30%) - potentially dead methods
                dead_classes.append(self._create_dead_class_info(
                    file_path, class_name, methods,
                    called_methods, is_abstract=is_abstract,
                    is_mixin=is_mixin, has_subclasses=has_subclasses,
                    instantiation_count=instantiation_count,
                    base_classes=base_classes
                ))
            elif not is_abstract and instantiation_count == 0 and has_subclasses and len(methods) == 0:
                # Never instantiated, has subclasses, no methods - potential base class
                dead_classes.append(self._create_dead_class_info(
                    file_path, class_name, methods,
                    called_methods, is_abstract=is_abstract,
                    is_mixin=is_mixin, has_subclasses=has_subclasses,
                    instantiation_count=instantiation_count,
                    base_classes=base_classes
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

    def _get_all_classes_with_metadata(self) -> List[Dict]:
        """
        Get all classes in the codebase with detailed metadata.

        Returns:
            List[Dict]: List of class information dictionaries with keys:
                - file_path: Path to file
                - class_name: Name of class
                - methods: List of method names
                - base_classes: List of base class names
                - is_abstract: Whether class is abstract (has ABC or abstract methods)
                - has_init: Whether class has __init__ method
        """
        all_classes = []
        python_files = self._find_python_files(self.project_root, recursive=True)
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                tree = ast.parse(source_code, filename=file_path)
                
                # Track imported modules for ABC detection
                imported_modules = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_modules.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imported_modules.add(node.module)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Get methods
                        methods = []
                        has_init = False
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                methods.append(item.name)
                                if item.name == '__init__':
                                    has_init = True
                        
                        # Get base classes
                        base_classes = []
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                base_classes.append(base.id)
                            elif isinstance(base, ast.Attribute):
                                base_classes.append(ast.unparse(base))
                        
                        # Check if abstract
                        is_abstract = self._is_abstract_class(node, imported_modules)
                        
                        all_classes.append({
                            'file_path': file_path,
                            'class_name': node.name,
                            'methods': methods,
                            'base_classes': base_classes,
                            'is_abstract': is_abstract,
                            'has_init': has_init
                        })
                        
            except Exception:
                continue
        
        return all_classes

    def _detect_subclass_relationships(
        self, 
        all_classes: List[Dict]
    ) -> Dict[Tuple[str, str], Set[Tuple[str, str]]]:
        """
        Detect subclass relationships between classes.

        Args:
            all_classes: List of class information dictionaries

        Returns:
            Dict: Maps (file, class) to set of (file, subclass) tuples
        """
        subclass_map = {}
        
        # Build a lookup of class names to their file paths
        class_to_file = {}
        for class_info in all_classes:
            file_path = class_info['file_path']
            class_name = class_info['class_name']
            class_to_file[class_name] = file_path
        
        # Detect inheritance relationships
        for class_info in all_classes:
            file_path = class_info['file_path']
            class_name = class_info['class_name']
            base_classes = class_info['base_classes']
            
            # For each base class, add this class as a subclass
            for base_name in base_classes:
                if base_name in class_to_file:
                    base_file = class_to_file[base_name]
                    key = (base_file, base_name)
                    if key not in subclass_map:
                        subclass_map[key] = set()
                    subclass_map[key].add((file_path, class_name))
        
        return subclass_map

    def _is_abstract_class(self, node: ast.ClassDef, imported_modules: Set[str]) -> bool:
        """
        Check if a class is abstract.

        Args:
            node: AST ClassDef node
            imported_modules: Set of imported module names

        Returns:
            bool: True if class is abstract
        """
        # Check if inherits from ABC or abc.ABC
        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id == 'ABC':
                    return True
            elif isinstance(base, ast.Attribute):
                if ast.unparse(base) in ['abc.ABC', 'ABCMeta']:
                    return True
        
        # Check for abstract methods (decorated with @abstractmethod)
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in item.decorator_list:
                    if isinstance(decorator, ast.Name):
                        if decorator.id == 'abstractmethod':
                            return True
                    elif isinstance(decorator, ast.Attribute):
                        if ast.unparse(decorator) == 'abc.abstractmethod':
                            return True
        
        return False

    def _is_mixin_class(self, class_info: Dict) -> bool:
        """
        Check if a class is a mixin (used for inheritance, not instantiation).

        Args:
            class_info: Class information dictionary

        Returns:
            bool: True if class is a mixin
        """
        class_name = class_info['class_name']
        methods = class_info['methods']
        has_init = class_info['has_init']
        
        # Mixin classes typically:
        # 1. Have "Mixin" in their name
        if 'Mixin' in class_name or 'mixin' in class_name:
            return True
        
        # 2. Don't have __init__ method (no state to initialize)
        if not has_init:
            return True
        
        # 3. Have only method definitions (no attributes in __init__)
        # This is harder to detect without full AST analysis of __init__
        
        return False

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
        is_abstract: bool = False,
        is_mixin: bool = False,
        has_subclasses: bool = False,
        instantiation_count: int = 0,
        base_classes: List[str] = None
    ) -> DeadClassInfo:
        """
        Create DeadClassInfo object with enhanced detection logic.

        Args:
            file_path: Path to class's file
            class_name: Name of class
            methods: List of method names
            called_methods: Set of method names that were called
            is_abstract: Whether class is abstract
            is_mixin: Whether class is a mixin
            has_subclasses: Whether class has subclasses
            instantiation_count: Number of times class was instantiated
            base_classes: List of base class names

        Returns:
            DeadClassInfo: Dead class information
        """
        reasons = []
        suggestions = []
        
        if is_abstract and has_subclasses:
            # Abstract base class - not considered dead
            confidence = 'low'
            reasons.append("Class is an abstract base class with subclasses")
            suggestions.append("Abstract base classes are expected to not be instantiated")
        
        elif is_mixin and has_subclasses:
            # Mixin class - not considered dead
            confidence = 'low'
            reasons.append("Class is a mixin used for inheritance")
            suggestions.append("Mixin classes are expected to be used via inheritance, not direct instantiation")
        
        elif instantiation_count == 0 and not has_subclasses and not is_abstract and not is_mixin:
            # Never instantiated, no subclasses - dead class
            confidence = 'high'
            reasons.append("Class is never instantiated and has no subclasses")
            if base_classes:
                reasons.append(f"Base classes: {', '.join(base_classes)}")
            suggestions.append("Consider removing this class")
        
        elif instantiation_count == 0 and not is_abstract and not is_mixin and has_subclasses and len(methods) == 0:
            # Never instantiated, has subclasses, no methods - potential base class
            confidence = 'medium'
            reasons.append("Class is never instantiated but has subclasses")
            reasons.append("Class has no methods, may be used only for inheritance")
            suggestions.append("Review if this base class is still needed")
        
        elif instantiation_count > 0 and len(called_methods) < len(methods) * 0.3:
            # Instantiated but very few methods called (<30%)
            confidence = 'medium'
            reasons.append(f"Only {len(called_methods)} of {len(methods)} methods ({len(called_methods)/len(methods)*100:.1f}%) are called")
            reasons.append(f"Class was instantiated {instantiation_count} time(s)")
            suggestions.append("Review which methods are actually needed, consider removing unused methods")
        
        elif len(called_methods) == 0 and not is_abstract and not is_mixin:
            # No methods called
            confidence = 'high'
            reasons.append("No methods of this class are called")
            suggestions.append("Consider removing this class")
        
        else:
            # Fallback
            confidence = 'low'
            reasons.append("Class has some usage but may be underutilized")
            suggestions.append("Review usage before removing")
        
        return DeadClassInfo(
            file_path=file_path,
            class_name=class_name,
            instantiation_count=instantiation_count,
            is_abstract_base=is_abstract,
            is_mixin=is_mixin,
            has_subclasses=has_subclasses,
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

        Detects:
        - Local variables (inside functions)
        - Class attributes
        - Module-level variables

        Args:
            tree: AST tree
            file_path: Path to file

        Returns:
            List[UnusedVariableInfo]: Unused variables
        """
        unused = []
        
        # Track module-level variables
        module_assignments = {}  # name -> (line_number, scope)
        module_references = set()
        
        # Track class attributes
        class_assignments = {}  # (class_name, attr_name) -> (line_number, scope)
        class_references = {}  # (class_name, attr_name) -> set of contexts
        
        # Track local variables per function
        function_scopes = {}  # function_name -> (assignments, references)
        current_function = None
        
        # First pass: collect assignments and references
        for node in ast.walk(tree):
            # Module-level assignments (top-level)
            if isinstance(node, ast.Assign) and self._is_module_level(node, tree):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if not self._is_special_variable(name):
                            module_assignments[name] = (node.lineno, 'module')
            
            # Class attribute assignments (self.attr, cls.attr)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        if isinstance(target.value, ast.Name):
                            base_name = target.value.id
                            if base_name in ('self', 'cls'):
                                attr_name = target.attr
                                # Try to find the containing class
                                containing_class = self._get_containing_class(node, tree)
                                if containing_class:
                                    class_assignments[(containing_class, attr_name)] = (node.lineno, 'class')
            
            # Variable references (Load context)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    if current_function:
                        # Local variable reference
                        if current_function not in function_scopes:
                            function_scopes[current_function] = ([], set())
                        function_scopes[current_function][1].add(node.id)
                    else:
                        # Module-level reference
                        module_references.add(node.id)
            
            # Attribute references (Load context)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.ctx, ast.Load):
                    if isinstance(node.value, ast.Name) and node.value.id in ('self', 'cls'):
                        attr_name = node.attr
                        containing_class = self._get_containing_class(node, tree)
                        if containing_class:
                            if (containing_class, attr_name) not in class_references:
                                class_references[(containing_class, attr_name)] = set()
                            # Record the reference
                            pass
            
            # Function definitions - track current scope
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if current_function is None:
                    # Module-level function
                    current_function = node.name
                    if current_function not in function_scopes:
                        function_scopes[current_function] = ([], set())
                    
                    # Local variable assignments
                    for stmt in node.body:
                        for inner_node in ast.walk(stmt):
                            if isinstance(inner_node, ast.Assign):
                                for target in inner_node.targets:
                                    if isinstance(target, ast.Name):
                                        name = target.id
                                        if not self._is_special_variable(name):
                                            function_scopes[current_function][0].append(
                                                (name, inner_node.lineno, 'local')
                                            )
                    
                    # Process local references
                    for stmt in node.body:
                        for inner_node in ast.walk(stmt):
                            if isinstance(inner_node, ast.Name):
                                if isinstance(inner_node.ctx, ast.Load):
                                    function_scopes[current_function][1].add(inner_node.id)
                    
                    current_function = None
        
        # Detect unused module-level variables
        for name, (line_number, scope) in module_assignments.items():
            if name not in module_references:
                unused.append(UnusedVariableInfo(
                    file_path=file_path,
                    variable_name=name,
                    scope=scope,
                    line_number=line_number,
                    confidence='medium',
                    reasons=[
                        f"Module-level variable '{name}' is assigned but never used",
                        "This variable may be imported by other modules"
                    ],
                    suggestions=["Consider removing if not used", "Check if imported by other modules"]
                ))
        
        # Detect unused class attributes
        for (class_name, attr_name), (line_number, scope) in class_assignments.items():
            key = (class_name, attr_name)
            if key not in class_references:
                unused.append(UnusedVariableInfo(
                    file_path=file_path,
                    variable_name=attr_name,
                    scope=scope,
                    line_number=line_number,
                    confidence='medium',
                    reasons=[
                        f"Class attribute '{class_name}.{attr_name}' is assigned but never used",
                        "This attribute may be set but never accessed"
                    ],
                    suggestions=["Consider removing this attribute", "Check if used dynamically"]
                ))
        
        # Detect unused local variables
        for func_name, (assignments, references) in function_scopes.items():
            for name, line_number, scope in assignments:
                if name not in references:
                    unused.append(UnusedVariableInfo(
                        file_path=file_path,
                        variable_name=name,
                        scope=scope,
                        line_number=line_number,
                        confidence='high',
                        reasons=[
                            f"Local variable '{name}' in function '{func_name}' is assigned but never used"
                        ],
                        suggestions=["Consider removing this variable"]
                    ))
        
        return unused

    def _is_module_level(self, node: ast.AST, tree: ast.AST) -> bool:
        """
        Check if a node is at module level (not inside a function or class).

        Args:
            node: AST node to check
            tree: Root AST tree

        Returns:
            bool: True if node is at module level
        """
        # Simple check: if node's line number matches any function/class definition
        for child in ast.walk(tree):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if child.lineno <= node.lineno <= child.end_lineno if child.end_lineno else False:
                    return False
        return True

    def _get_containing_class(self, node: ast.AST, tree: ast.AST) -> Optional[str]:
        """
        Get the name of the class containing a node.

        Args:
            node: AST node
            tree: Root AST tree

        Returns:
            Optional[str]: Class name or None
        """
        for child in ast.walk(tree):
            if isinstance(child, ast.ClassDef):
                # Check if node is within this class's body
                for body_node in child.body:
                    for inner_node in ast.walk(body_node):
                        if inner_node is node:
                            return child.name
        return None

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

    def generate_dead_class_report(self, format: str = "text") -> str:
        """
        Generate dead class detection report.

        Args:
            format: Report format ('text', 'json', 'markdown')

        Returns:
            str: Generated report
        """
        dead_classes = self.detect_dead_classes()
        
        if format == "json":
            import json
            return json.dumps(
                [self._dead_class_to_dict(c) for c in dead_classes],
                indent=2,
                default=str
            )
        elif format == "markdown":
            return self._generate_dead_classes_markdown(dead_classes)
        else:
            return self._generate_dead_classes_text(dead_classes)

    def generate_unused_variables_report(self, format: str = "text") -> str:
        """
        Generate unused variable detection report.

        Args:
            format: Report format ('text', 'json', 'markdown')

        Returns:
            str: Generated report
        """
        unused_variables = self.detect_unused_variables()
        
        if format == "json":
            import json
            return json.dumps(
                [self._unused_variable_to_dict(v) for v in unused_variables],
                indent=2,
                default=str
            )
        elif format == "markdown":
            return self._generate_unused_variables_markdown(unused_variables)
        else:
            return self._generate_unused_variables_text(unused_variables)

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

    def _dead_class_to_dict(self, cls: DeadClassInfo) -> Dict:
        """Convert DeadClassInfo to dictionary."""
        return {
            "file_path": cls.file_path,
            "class_name": cls.class_name,
            "instantiation_count": cls.instantiation_count,
            "is_abstract_base": cls.is_abstract_base,
            "is_mixin": cls.is_mixin,
            "has_subclasses": cls.has_subclasses,
            "methods_count": cls.methods_count,
            "called_methods": list(cls.called_methods),
            "confidence": cls.confidence,
            "reasons": cls.reasons,
            "suggestions": cls.suggestions
        }

    def _generate_dead_classes_text(self, dead_classes: List[DeadClassInfo]) -> str:
        """Generate text format report for dead classes."""
        lines = []
        lines.append("=" * 70)
        lines.append("DEAD CLASS DETECTION REPORT")
        lines.append("=" * 70)
        lines.append(f"Total Dead Classes: {len(dead_classes)}")
        lines.append("")
        
        # Count by confidence
        high_conf = sum(1 for c in dead_classes if c.confidence == 'high')
        medium_conf = sum(1 for c in dead_classes if c.confidence == 'medium')
        low_conf = sum(1 for c in dead_classes if c.confidence == 'low')
        
        lines.append("Confidence Breakdown:")
        lines.append(f"  High: {high_conf}")
        lines.append(f"  Medium: {medium_conf}")
        lines.append(f"  Low: {low_conf}")
        lines.append("")
        
        # Dead classes
        if dead_classes:
            lines.append("DEAD CLASSES:")
            lines.append("-" * 70)
            for cls in dead_classes[:50]:  # Limit to first 50
                file_name = os.path.basename(cls.file_path)
                lines.append(f"  {cls.class_name} ({file_name})")
                lines.append(f"    Confidence: {cls.confidence}, Instantiations: {cls.instantiation_count}")
                lines.append(f"    Methods: {len(cls.called_methods)}/{cls.methods_count} called")
                if cls.reasons:
                    lines.append(f"    Reasons:")
                    for reason in cls.reasons[:2]:
                        lines.append(f"      - {reason}")
                if cls.suggestions:
                    lines.append(f"    Suggestion: {cls.suggestions[0]}")
                if cls.is_abstract_base:
                    lines.append(f"    Type: Abstract Base Class")
                elif cls.is_mixin:
                    lines.append(f"    Type: Mixin")
                elif cls.has_subclasses:
                    lines.append(f"    Type: Base Class (has subclasses)")
            if len(dead_classes) > 50:
                lines.append(f"  ... and {len(dead_classes) - 50} more")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)

    def _generate_dead_classes_markdown(self, dead_classes: List[DeadClassInfo]) -> str:
        """Generate markdown format report for dead classes."""
        lines = []
        lines.append("# Dead Class Detection Report")
        lines.append("")
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Dead Classes**: {len(dead_classes)}")
        
        high_conf = sum(1 for c in dead_classes if c.confidence == 'high')
        medium_conf = sum(1 for c in dead_classes if c.confidence == 'medium')
        low_conf = sum(1 for c in dead_classes if c.confidence == 'low')
        
        lines.append(f"- **High Confidence**: {high_conf}")
        lines.append(f"- **Medium Confidence**: {medium_conf}")
        lines.append(f"- **Low Confidence**: {low_conf}")
        lines.append("")
        
        # Dead classes table
        if dead_classes:
            lines.append("## Dead Classes")
            lines.append("")
            lines.append("| Class | File | Methods | Confidence | Type | Reason |")
            lines.append("|-------|------|---------|------------|------|--------|")
            for cls in dead_classes[:50]:
                file_name = os.path.basename(cls.file_path)
                reason = cls.reasons[0] if cls.reasons else "N/A"
                class_type = []
                if cls.is_abstract_base:
                    class_type.append("Abstract")
                elif cls.is_mixin:
                    class_type.append("Mixin")
                elif cls.has_subclasses:
                    class_type.append("Base")
                type_str = ", ".join(class_type) if class_type else "Regular"
                lines.append(f"| {cls.class_name} | {file_name} | {len(cls.called_methods)}/{cls.methods_count} | {cls.confidence} | {type_str} | {reason} |")
            if len(dead_classes) > 50:
                lines.append(f"| ... | ... | ... | ... | ... | and {len(dead_classes) - 50} more |")
            lines.append("")
        
        return "\n".join(lines)

    def _unused_variable_to_dict(self, var: UnusedVariableInfo) -> Dict:
        """Convert UnusedVariableInfo to dictionary."""
        return {
            "file_path": var.file_path,
            "variable_name": var.variable_name,
            "scope": var.scope,
            "line_number": var.line_number,
            "confidence": var.confidence,
            "reasons": var.reasons,
            "suggestions": var.suggestions
        }

    def _generate_unused_variables_text(self, unused_variables: List[UnusedVariableInfo]) -> str:
        """Generate text format report for unused variables."""
        lines = []
        lines.append("=" * 70)
        lines.append("UNUSED VARIABLE DETECTION REPORT")
        lines.append("=" * 70)
        lines.append(f"Total Unused Variables: {len(unused_variables)}")
        lines.append("")
        
        # Count by scope
        local_vars = sum(1 for v in unused_variables if v.scope == 'local')
        class_vars = sum(1 for v in unused_variables if v.scope == 'class')
        module_vars = sum(1 for v in unused_variables if v.scope == 'module')
        
        # Count by confidence
        high_conf = sum(1 for v in unused_variables if v.confidence == 'high')
        medium_conf = sum(1 for v in unused_variables if v.confidence == 'medium')
        low_conf = sum(1 for v in unused_variables if v.confidence == 'low')
        
        lines.append("Scope Breakdown:")
        lines.append(f"  Local Variables: {local_vars}")
        lines.append(f"  Class Attributes: {class_vars}")
        lines.append(f"  Module-Level Variables: {module_vars}")
        lines.append("")
        
        lines.append("Confidence Breakdown:")
        lines.append(f"  High: {high_conf}")
        lines.append(f"  Medium: {medium_conf}")
        lines.append(f"  Low: {low_conf}")
        lines.append("")
        
        # Unused variables
        if unused_variables:
            lines.append("UNUSED VARIABLES:")
            lines.append("-" * 70)
            for var in unused_variables[:50]:  # Limit to first 50
                file_name = os.path.basename(var.file_path)
                lines.append(f"  {var.variable_name} ({file_name}:{var.line_number})")
                lines.append(f"    Scope: {var.scope}, Confidence: {var.confidence}")
                if var.reasons:
                    lines.append(f"    Reasons:")
                    for reason in var.reasons[:2]:
                        lines.append(f"      - {reason}")
                if var.suggestions:
                    lines.append(f"    Suggestion: {var.suggestions[0]}")
            if len(unused_variables) > 50:
                lines.append(f"  ... and {len(unused_variables) - 50} more")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)

    def _generate_unused_variables_markdown(self, unused_variables: List[UnusedVariableInfo]) -> str:
        """Generate markdown format report for unused variables."""
        lines = []
        lines.append("# Unused Variable Detection Report")
        lines.append("")
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Unused Variables**: {len(unused_variables)}")
        
        # Count by scope
        local_vars = sum(1 for v in unused_variables if v.scope == 'local')
        class_vars = sum(1 for v in unused_variables if v.scope == 'class')
        module_vars = sum(1 for v in unused_variables if v.scope == 'module')
        
        # Count by confidence
        high_conf = sum(1 for v in unused_variables if v.confidence == 'high')
        medium_conf = sum(1 for v in unused_variables if v.confidence == 'medium')
        low_conf = sum(1 for v in unused_variables if v.confidence == 'low')
        
        lines.append("### Scope Breakdown")
        lines.append(f"- **Local Variables**: {local_vars}")
        lines.append(f"- **Class Attributes**: {class_vars}")
        lines.append(f"- **Module-Level Variables**: {module_vars}")
        lines.append("")
        
        lines.append("### Confidence Breakdown")
        lines.append(f"- **High Confidence**: {high_conf}")
        lines.append(f"- **Medium Confidence**: {medium_conf}")
        lines.append(f"- **Low Confidence**: {low_conf}")
        lines.append("")
        
        # Unused variables table
        if unused_variables:
            lines.append("## Unused Variables")
            lines.append("")
            lines.append("| Variable | File:Line | Scope | Confidence | Reason |")
            lines.append("|----------|-----------|-------|------------|--------|")
            for var in unused_variables[:50]:
                file_name = os.path.basename(var.file_path)
                reason = var.reasons[0] if var.reasons else "N/A"
                lines.append(f"| {var.variable_name} | {file_name}:{var.line_number} | {var.scope} | {var.confidence} | {reason} |")
            if len(unused_variables) > 50:
                lines.append(f"| ... | ... | ... | ... | and {len(unused_variables) - 50} more |")
            lines.append("")
        
        return "\n".join(lines)
