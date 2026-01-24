"""
Import Dependency Analyzer Module (V5)

This module analyzes and tracks import dependencies across the codebase,
identifying unused imports, circular dependencies, and import depth.

Key Features:
- Track all imports in Python files (absolute, relative, from imports)
- Identify unused imports (imported but not used)
- Identify circular import dependencies
- Identify import depth (how many levels deep)
- Track import usage frequency over time
- Generate import dependency report
"""

import os
import ast
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass

from ..data.semantic_mapper import SemanticMapper
from ..data.call_graph_persistence import CallGraphPersistence


@dataclass
class ImportInfo:
    """Information about a single import."""
    file_path: str
    module_name: str
    import_type: str  # 'import' or 'from'
    imported_names: Optional[List[str]]  # For from imports
    line_number: int
    is_used: bool = False
    usage_count: int = 0


@dataclass
class CircularDependency:
    """Information about a circular dependency."""
    cycle: List[str]  # List of modules in the cycle
    files_involved: List[str]  # Files that form the cycle
    severity: str  # 'direct' or 'indirect'


class ImportAnalyzer:
    """
    Analyzes import dependencies across the codebase.
    """

    def __init__(
        self,
        project_root: str,
        call_graph_persistence: Optional[CallGraphPersistence] = None
    ):
        """
        Initialize ImportAnalyzer.

        Args:
            project_root: Root directory of the project
            call_graph_persistence: Optional CallGraphPersistence instance for tracking usage
        """
        self.project_root = project_root
        self.call_graph_persistence = call_graph_persistence or CallGraphPersistence()
        self._import_cache: Dict[str, List[ImportInfo]] = {}
        self._usage_cache: Dict[str, Set[str]] = {}

    def analyze_project(self, recursive: bool = True) -> Dict:
        """
        Analyze all Python files in the project.

        Args:
            recursive: Whether to analyze recursively in subdirectories

        Returns:
            Dict: Complete analysis results
        """
        python_files = self._find_python_files(self.project_root, recursive)

        all_imports = []
        unused_imports = []
        circular_deps = []
        import_depths = {}

        for file_path in python_files:
            # Analyze imports for this file
            file_imports = self.analyze_file_imports(file_path)
            all_imports.extend(file_imports)

            # Detect unused imports
            unused = self.detect_unused_imports(file_path)
            unused_imports.extend(unused)

            # Calculate import depth
            depth = self.calculate_import_depth(file_path)
            if depth:
                import_depths[file_path] = depth

        # Detect circular dependencies across all files
        circular_deps = self.detect_circular_dependencies()

        # Calculate statistics
        stats = self._calculate_statistics(all_imports, unused_imports, circular_deps)

        return {
            "total_files": len(python_files),
            "total_imports": len(all_imports),
            "unused_imports": unused_imports,
            "circular_dependencies": circular_deps,
            "import_depths": import_depths,
            "statistics": stats
        }

    def analyze_file_imports(self, file_path: str) -> List[ImportInfo]:
        """
        Analyze imports in a single Python file.

        Args:
            file_path: Path to Python file

        Returns:
            List[ImportInfo]: List of import information
        """
        # Check cache
        if file_path in self._import_cache:
            return self._import_cache[file_path]

        # Read file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            return []

        # Parse imports using SemanticMapper
        mapper = SemanticMapper(source_code, file_path)
        import_deps = mapper.get_import_dependencies()

        # Convert to ImportInfo objects
        imports = []

        # Simple imports (import module)
        for module in import_deps.get("modules", []):
            line_number = import_deps["line_numbers"].get(module, 0)
            imports.append(ImportInfo(
                file_path=file_path,
                module_name=module,
                import_type='import',
                imported_names=None,
                line_number=line_number,
                is_used=False,
                usage_count=0
            ))

        # From imports (from module import name1, name2)
        for module, names in import_deps.get("from_imports", {}).items():
            line_key = f"from {module}"
            line_number = import_deps["line_numbers"].get(line_key, 0)
            imports.append(ImportInfo(
                file_path=file_path,
                module_name=module,
                import_type='from',
                imported_names=names,
                line_number=line_number,
                is_used=False,
                usage_count=0
            ))

        # Check usage from call graph persistence
        if self.call_graph_persistence:
            import_usages = self.call_graph_persistence.get_import_dependencies(file_path)
            usage_map = {imp["module_name"]: imp["usage_count"] for imp in import_usages}

            for imp in imports:
                if imp.module_name in usage_map:
                    imp.is_used = True
                    imp.usage_count = usage_map[imp.module_name]

        # Cache results
        self._import_cache[file_path] = imports

        return imports

    def detect_unused_imports(self, file_path: str) -> List[Dict]:
        """
        Detect unused imports in a file.

        Args:
            file_path: Path to Python file

        Returns:
            List[Dict]: List of unused import information
        """
        imports = self.analyze_file_imports(file_path)
        unused = []

        # Get used names from code
        used_names = self._get_used_names(file_path)

        for imp in imports:
            if not imp.is_used:
                # For simple imports, check if module name is used
                if imp.import_type == 'import':
                    module_base = imp.module_name.split('.')[0]
                    if module_base not in used_names:
                        unused.append({
                            "file_path": imp.file_path,
                            "module_name": imp.module_name,
                            "import_type": imp.import_type,
                            "line_number": imp.line_number,
                            "suggestion": f"Remove unused import: import {imp.module_name}"
                        })

                # For from imports, check if any imported names are used
                elif imp.import_type == 'from':
                    if imp.imported_names:
                        unused_names = [
                            name for name in imp.imported_names
                            if name not in used_names and name != '*'
                        ]
                        if len(unused_names) == len(imp.imported_names):
                            # All names unused
                            names_str = ", ".join(imp.imported_names)
                            unused.append({
                                "file_path": imp.file_path,
                                "module_name": imp.module_name,
                                "import_type": imp.import_type,
                                "imported_names": imp.imported_names,
                                "line_number": imp.line_number,
                                "suggestion": f"Remove unused import: from {imp.module_name} import {names_str}"
                            })
                        elif unused_names:
                            # Some names unused
                            used_names_list = [
                                name for name in imp.imported_names
                                if name in used_names
                            ]
                            unused.append({
                                "file_path": imp.file_path,
                                "module_name": imp.module_name,
                                "import_type": imp.import_type,
                                "imported_names": unused_names,
                                "line_number": imp.line_number,
                                "suggestion": f"Remove unused names from {imp.module_name}: {', '.join(unused_names)}. Keep: {', '.join(used_names_list)}"
                            })

        return unused

    def detect_circular_dependencies(self) -> List[Dict]:
        """
        Detect circular import dependencies across the project.

        Args:
            None (uses project files)

        Returns:
            List[Dict]: List of circular dependency information
        """
        # Build dependency graph
        dep_graph = defaultdict(set)
        file_to_module = {}

        # Find all Python files
        python_files = self._find_python_files(self.project_root, recursive=True)

        # Build graph
        for file_path in python_files:
            module_name = self._file_to_module(file_path)
            file_to_module[file_path] = module_name

            # Get imports
            imports = self.analyze_file_imports(file_path)

            for imp in imports:
                # Only consider internal imports (same project)
                if self._is_internal_import(imp.module_name):
                    dep_graph[module_name].add(imp.module_name)

        # Detect cycles using DFS
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dep_graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        # Run DFS from all nodes
        for module in dep_graph:
            if module not in visited:
                dfs(module, [])

        # Convert cycles to dictionaries
        result = []
        for cycle in cycles:
            # Find files involved
            files = []
            for module in cycle:
                files.extend([f for f, m in file_to_module.items() if m == module])

            # Determine severity
            severity = 'direct' if len(cycle) == 2 else 'indirect'

            result.append({
                "cycle": cycle,
                "cycle_str": " -> ".join(cycle),
                "files_involved": files,
                "severity": severity,
                "cycle_length": len(cycle) - 1,
                "suggestion": self._suggest_fix_for_cycle(cycle)
            })

        return result

    def calculate_import_depth(self, file_path: str) -> Dict:
        """
        Calculate import depth for a file (how many levels deep the import chain is).

        Args:
            file_path: Path to Python file

        Returns:
            Dict: Import depth information
        """
        # Build dependency graph
        dep_graph = defaultdict(list)

        # Find all Python files
        python_files = self._find_python_files(self.project_root, recursive=True)

        # Build graph (file -> imports)
        for fp in python_files:
            imports = self.analyze_file_imports(fp)
            for imp in imports:
                # Only consider internal imports
                if self._is_internal_import(imp.module_name):
                    dep_graph[fp].append(imp.module_name)

        # BFS to find depth
        depths = {fp: 0 for fp in python_files}
        queue = deque()

        # Start with files that have no dependencies
        for fp in python_files:
            if not dep_graph[fp]:
                queue.append((fp, 0))

        # BFS
        while queue:
            current, depth = queue.popleft()

            # Find files that depend on current
            for fp in python_files:
                imports = self.analyze_file_imports(fp)
                for imp in imports:
                    module_name = self._file_to_module(current)
                    if imp.module_name == module_name:
                        # fp depends on current
                        if depths[fp] < depth + 1:
                            depths[fp] = depth + 1
                            queue.append((fp, depth + 1))

        return {
            "file_path": file_path,
            "depth": depths.get(file_path, 0),
            "is_leaf": not dep_graph[file_path]
        }

    def generate_import_report(self, format: str = "text") -> str:
        """
        Generate comprehensive import dependency report.

        Args:
            format: Report format ('text', 'json', 'markdown')

        Returns:
            str: Generated report
        """
        analysis = self.analyze_project()

        if format == "json":
            import json
            return json.dumps(analysis, indent=2, default=str)

        elif format == "markdown":
            return self._generate_markdown_report(analysis)

        else:  # text
            return self._generate_text_report(analysis)

    def _generate_text_report(self, analysis: Dict) -> str:
        """Generate text format report."""
        lines = []
        lines.append("=" * 70)
        lines.append("IMPORT DEPENDENCY REPORT")
        lines.append("=" * 70)
        lines.append(f"Total Files: {analysis['total_files']}")
        lines.append(f"Total Imports: {analysis['total_imports']}")
        lines.append("")

        # Statistics
        stats = analysis['statistics']
        lines.append("STATISTICS:")
        lines.append(f"  Simple Imports: {stats['simple_imports']}")
        lines.append(f"  From Imports: {stats['from_imports']}")
        lines.append(f"  Unused Imports: {stats['unused_count']}")
        lines.append(f"  Circular Dependencies: {stats['circular_count']}")
        lines.append(f"  Average Import Depth: {stats['avg_depth']:.2f}")
        lines.append(f"  Maximum Import Depth: {stats['max_depth']}")
        lines.append("")

        # Unused imports
        if analysis['unused_imports']:
            lines.append("UNUSED IMPORTS:")
            lines.append("-" * 70)
            for imp in analysis['unused_imports'][:20]:  # Limit to first 20
                file_name = os.path.basename(imp['file_path'])
                lines.append(f"  {file_name}:{imp['line_number']}")
                lines.append(f"    {imp['suggestion']}")
            if len(analysis['unused_imports']) > 20:
                lines.append(f"  ... and {len(analysis['unused_imports']) - 20} more")
            lines.append("")

        # Circular dependencies
        if analysis['circular_dependencies']:
            lines.append("CIRCULAR DEPENDENCIES:")
            lines.append("-" * 70)
            for dep in analysis['circular_dependencies']:
                lines.append(f"  {dep['cycle_str']}")
                lines.append(f"    Severity: {dep['severity']}")
                lines.append(f"    Files: {', '.join([os.path.basename(f) for f in dep['files_involved'][:3]])}")
                if dep['suggestion']:
                    lines.append(f"    Suggestion: {dep['suggestion']}")
            lines.append("")

        # Import depths
        if analysis['import_depths']:
            lines.append("IMPORT DEPTH:")
            lines.append("-" * 70)
            # Show top 10 deepest
            sorted_depths = sorted(
                analysis['import_depths'].items(),
                key=lambda x: x[1]['depth'],
                reverse=True
            )[:10]
            for file_path, depth_info in sorted_depths:
                file_name = os.path.basename(file_path)
                lines.append(f"  {file_name}: depth {depth_info['depth']}")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def _generate_markdown_report(self, analysis: Dict) -> str:
        """Generate markdown format report."""
        lines = []
        lines.append("# Import Dependency Report")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Files**: {analysis['total_files']}")
        lines.append(f"- **Total Imports**: {analysis['total_imports']}")
        lines.append("")

        # Statistics
        stats = analysis['statistics']
        lines.append("## Statistics")
        lines.append("")
        lines.append(f"- **Simple Imports**: {stats['simple_imports']}")
        lines.append(f"- **From Imports**: {stats['from_imports']}")
        lines.append(f"- **Unused Imports**: {stats['unused_count']}")
        lines.append(f"- **Circular Dependencies**: {stats['circular_count']}")
        lines.append(f"- **Average Import Depth**: {stats['avg_depth']:.2f}")
        lines.append(f"- **Maximum Import Depth**: {stats['max_depth']}")
        lines.append("")

        # Unused imports
        if analysis['unused_imports']:
            lines.append("## Unused Imports")
            lines.append("")
            lines.append("| File | Line | Module | Issue |")
            lines.append("|------|------|--------|-------|")
            for imp in analysis['unused_imports'][:20]:
                file_name = os.path.basename(imp['file_path'])
                module = imp.get('module_name', '')
                names = ', '.join(imp.get('imported_names', [])) if imp.get('imported_names') else module
                lines.append(f"| {file_name} | {imp['line_number']} | `{names}` | {imp['suggestion']} |")
            if len(analysis['unused_imports']) > 20:
                lines.append(f"| ... | ... | ... | and {len(analysis['unused_imports']) - 20} more |")
            lines.append("")

        # Circular dependencies
        if analysis['circular_dependencies']:
            lines.append("## Circular Dependencies")
            lines.append("")
            for dep in analysis['circular_dependencies']:
                lines.append(f"### {dep['cycle_str']}")
                lines.append("")
                lines.append(f"- **Severity**: {dep['severity']}")
                lines.append(f"- **Files Involved**: {len(dep['files_involved'])}")
                if dep['suggestion']:
                    lines.append(f"- **Suggestion**: {dep['suggestion']}")
                lines.append("")

        # Import depths
        if analysis['import_depths']:
            lines.append("## Import Depth")
            lines.append("")
            lines.append("| File | Depth | Is Leaf |")
            lines.append("|------|-------|---------|")
            sorted_depths = sorted(
                analysis['import_depths'].items(),
                key=lambda x: x[1]['depth'],
                reverse=True
            )[:10]
            for file_path, depth_info in sorted_depths:
                file_name = os.path.basename(file_path)
                is_leaf = "Yes" if depth_info['is_leaf'] else "No"
                lines.append(f"| {file_name} | {depth_info['depth']} | {is_leaf} |")
            lines.append("")

        return "\n".join(lines)

    def _calculate_statistics(self, all_imports: List[ImportInfo],
                           unused_imports: List[Dict],
                           circular_deps: List[Dict]) -> Dict:
        """Calculate statistics from analysis results."""
        simple_imports = sum(1 for imp in all_imports if imp.import_type == 'import')
        from_imports = sum(1 for imp in all_imports if imp.import_type == 'from')

        depths = [info['depth'] for info in all_imports if 'depth' in info]
        avg_depth = sum(depths) / len(depths) if depths else 0
        max_depth = max(depths) if depths else 0

        return {
            "simple_imports": simple_imports,
            "from_imports": from_imports,
            "unused_count": len(unused_imports),
            "circular_count": len(circular_deps),
            "avg_depth": avg_depth,
            "max_depth": max_depth
        }

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

    def _file_to_module(self, file_path: str) -> str:
        """Convert file path to module name."""
        rel_path = os.path.relpath(file_path, self.project_root)
        module_path = rel_path.replace(os.sep, '.')
        module_name = module_path[:-3] if module_path.endswith('.py') else module_path
        return module_name

    def _is_internal_import(self, module_name: str) -> bool:
        """Check if import is internal (belongs to same project)."""
        # This is a simple check - in practice, you'd compare against known project modules
        # For now, we'll assume imports that start with project name are internal
        project_name = os.path.basename(self.project_root)
        return module_name.startswith(project_name)

    def _get_used_names(self, file_path: str) -> Set[str]:
        """Get set of all names used in a file."""
        if file_path in self._usage_cache:
            return self._usage_cache[file_path]

        used_names = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Parse AST
            tree = ast.parse(source_code)

            # Collect all names
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Load):
                        used_names.add(node.id)

        except Exception as e:
            pass

        self._usage_cache[file_path] = used_names
        return used_names

    def _suggest_fix_for_cycle(self, cycle: List[str]) -> str:
        """Suggest fix for circular dependency."""
        if len(cycle) == 2:
            # Direct cycle (A -> B -> A)
            return f"Consider moving shared functionality from {cycle[0]} or {cycle[1]} to a third module"
        else:
            # Indirect cycle
            return f"Consider refactoring to break the cycle, perhaps by introducing an interface module"