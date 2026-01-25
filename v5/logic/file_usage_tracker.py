"""
File Usage Tracker Module (V5)

This module tracks file usage patterns across the codebase to identify unused files.

Key Features:
- Track which files are imported/referenced in the codebase
- Track which files are executed (entry points, scripts)
- Track file modification timestamps
- Track file size over time
- Identify potential unused files
- Generate file usage report
"""

import os
import ast
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json

from .import_analyzer import ImportAnalyzer


@dataclass
class FileInfo:
    """Information about a single file."""
    file_path: str
    file_type: str  # 'python', 'test', 'documentation', 'config', 'other'
    size_bytes: int
    last_modified: datetime
    is_entry_point: bool = False
    is_imported: bool = False
    import_count: int = 0
    importers: List[str] = None
    execution_count: int = 0
    last_used: Optional[datetime] = None


@dataclass
class UnusedFileCandidate:
    """Information about a potentially unused file."""
    file_path: str
    file_type: str
    size_bytes: int
    last_modified: datetime
    confidence: str  # 'high', 'medium', 'low'
    reasons: List[str]
    suggestions: List[str]


class FileUsageTracker:
    """
    Tracks file usage patterns and identifies potentially unused files.
    """

    def __init__(
        self,
        project_root: str,
        import_analyzer: Optional[ImportAnalyzer] = None,
        unused_age_days: int = 30
    ):
        """
        Initialize FileUsageTracker.

        Args:
            project_root: Root directory of project
            import_analyzer: Optional ImportAnalyzer instance for tracking imports
            unused_age_days: Age in days to consider a file potentially unused
        """
        self.project_root = project_root
        self.unused_age_threshold = timedelta(days=unused_age_days)
        self.import_analyzer = import_analyzer or ImportAnalyzer(project_root)
        self._file_cache: Dict[str, FileInfo] = {}
        self._import_graph: Dict[str, Set[str]] = {}  # file -> set of files that import it

    def analyze_project(self, recursive: bool = True) -> Dict:
        """
        Analyze all files in the project for usage patterns.

        Args:
            recursive: Whether to analyze recursively in subdirectories

        Returns:
            Dict: Complete analysis results
        """
        # Find all relevant files
        all_files = self._find_all_files(self.project_root, recursive)

        # Track which files are imported
        imported_files = self._track_imported_files()

        # Track entry points
        entry_points = self._find_entry_points(self.project_root, recursive)

        # Build file info for each file
        file_infos = {}
        unused_candidates = []

        for file_path in all_files:
            # Get file metadata
            file_info = self._get_file_info(file_path)

            # Update with import information
            if file_path in imported_files:
                file_info.is_imported = True
                file_info.import_count = len(imported_files[file_path]['importers'])
                file_info.importers = list(imported_files[file_path]['importers'])

            # Update with entry point information
            if file_path in entry_points:
                file_info.is_entry_point = True
                file_info.execution_count = entry_points[file_path]

            file_infos[file_path] = file_info

            # Check if potentially unused
            if self._is_potentially_unused(file_info):
                candidate = self._create_unused_candidate(file_info)
                unused_candidates.append(candidate)

        # Calculate statistics
        stats = self._calculate_statistics(file_infos, unused_candidates)

        return {
            "total_files": len(all_files),
            "total_size_bytes": sum(f.size_bytes for f in file_infos.values()),
            "imported_files": sum(1 for f in file_infos.values() if f.is_imported),
            "entry_points": sum(1 for f in file_infos.values() if f.is_entry_point),
            "unused_candidates": unused_candidates,
            "most_used_files": self._get_most_used_files(file_infos),
            "file_infos": file_infos,
            "statistics": stats
        }

    def track_file_access(self, file_path: str, access_type: str = "read") -> None:
        """
        Track when a file is accessed.

        Args:
            file_path: Path to file
            access_type: Type of access ('read', 'write', 'import')
        """
        # This would integrate with telemetry to track actual file access patterns
        # For now, we'll store in cache
        if file_path not in self._file_cache:
            file_info = self._get_file_info(file_path)
            self._file_cache[file_path] = file_info

        # Update last used timestamp
        self._file_cache[file_path].last_used = datetime.now()

    def identify_unused_files(self, recursive: bool = True) -> List[UnusedFileCandidate]:
        """
        Identify potentially unused files in the project.

        Args:
            recursive: Whether to analyze recursively in subdirectories

        Returns:
            List[UnusedFileCandidate]: List of potentially unused files
        """
        analysis = self.analyze_project(recursive)
        return analysis['unused_candidates']

    def generate_usage_report(self, format: str = "text") -> str:
        """
        Generate comprehensive file usage report.

        Args:
            format: Report format ('text', 'json', 'markdown')

        Returns:
            str: Generated report
        """
        analysis = self.analyze_project()

        if format == "json":
            return json.dumps(analysis, indent=2, default=str)

        elif format == "markdown":
            return self._generate_markdown_report(analysis)

        else:  # text
            return self._generate_text_report(analysis)

    def _track_imported_files(self) -> Dict[str, Dict]:
        """
        Track which files are imported by others.

        Returns:
            Dict: Mapping of file -> {'importers': set, 'count': int}
        """
        # Find all Python files
        python_files = self._find_python_files(self.project_root, recursive=True)

        imported_files = {}

        for file_path in python_files:
            # Get imports for this file
            imports = self.import_analyzer.analyze_file_imports(file_path)

            for imp in imports:
                # Resolve imported module to file path
                imported_file = self._resolve_import_to_file(imp.module_name, file_path)

                if imported_file:
                    if imported_file not in imported_files:
                        imported_files[imported_file] = {'importers': set(), 'count': 0}

                    imported_files[imported_file]['importers'].add(file_path)
                    imported_files[imported_file]['count'] += 1

        return imported_files

    def _find_entry_points(self, directory: str, recursive: bool = True) -> Dict[str, int]:
        """
        Find entry point files (files with if __name__ == '__main__' blocks).

        Args:
            directory: Directory to search
            recursive: Whether to search recursively

        Returns:
            Dict: Mapping of file -> execution count
        """
        entry_points = {}
        python_files = self._find_python_files(directory, recursive)

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()

                # Parse AST
                tree = ast.parse(source_code)

                # Look for if __name__ == '__main__' blocks
                for node in ast.walk(tree):
                    if isinstance(node, ast.If):
                        # Check if test is __name__ == '__main__'
                        if (isinstance(node.test, ast.Compare) and
                            len(node.test.comparators) == 1):
                            left = node.test.left
                            comparator = node.test.comparators[0]

                            if (isinstance(left, ast.Name) and
                                left.id == '__name__' and
                                isinstance(comparator, ast.Constant) and
                                comparator.value == '__main__'):
                                entry_points[file_path] = 1
                                break

            except Exception as e:
                pass

        return entry_points

    def _get_file_info(self, file_path: str) -> FileInfo:
        """
        Get information about a file.

        Args:
            file_path: Path to file

        Returns:
            FileInfo: File information
        """
        # Check cache
        if file_path in self._file_cache:
            return self._file_cache[file_path]

        # Get file metadata
        stat = os.stat(file_path)
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime)

        # Determine file type
        file_type = self._determine_file_type(file_path)

        # Create FileInfo
        file_info = FileInfo(
            file_path=file_path,
            file_type=file_type,
            size_bytes=size,
            last_modified=modified,
            is_entry_point=False,
            is_imported=False,
            import_count=0,
            importers=[],
            execution_count=0,
            last_used=None
        )

        # Cache result
        self._file_cache[file_path] = file_info

        return file_info

    def _is_potentially_unused(self, file_info: FileInfo) -> bool:
        """
        Determine if a file is potentially unused.

        Args:
            file_info: FileInfo object

        Returns:
            bool: True if potentially unused
        """
        # Exclude test files
        if file_info.file_type == 'test':
            return False

        # Exclude entry points
        if file_info.is_entry_point:
            return False

        # Exclude documentation files
        if file_info.file_type == 'documentation':
            return False

        # Exclude configuration files
        if file_info.file_type == 'config':
            return False

        # Check if not imported
        if not file_info.is_imported:
            # Check if old
            age = datetime.now() - file_info.last_modified
            if age > self.unused_age_threshold:
                return True

        # Check if very low usage
        if file_info.import_count == 1:
            # Only imported once, check age
            age = datetime.now() - file_info.last_modified
            if age > self.unused_age_threshold * 2:  # Double threshold
                return True

        return False

    def _create_unused_candidate(self, file_info: FileInfo) -> UnusedFileCandidate:
        """
        Create UnusedFileCandidate from FileInfo.

        Args:
            file_info: FileInfo object

        Returns:
            UnusedFileCandidate: Unused file candidate
        """
        reasons = []
        suggestions = []

        if not file_info.is_imported:
            reasons.append("File is not imported by any other file")

        if file_info.import_count == 1:
            reasons.append(f"File is imported by only 1 file: {os.path.basename(file_info.importers[0])}")

        age_days = (datetime.now() - file_info.last_modified).days
        reasons.append(f"Last modified {age_days} days ago")

        # Determine confidence
        if not file_info.is_imported and age_days > self.unused_age_threshold.days:
            confidence = 'high'
            suggestions.append("Consider removing this file")
        elif file_info.import_count == 1 and age_days > self.unused_age_threshold.days * 2:
            confidence = 'medium'
            suggestions.append("Consider if this file is still needed")
        else:
            confidence = 'low'
            suggestions.append("Review before removing")

        if file_info.file_type == 'python':
            suggestions.append("Check if functions/classes are used externally")
        elif file_info.file_type == 'test':
            suggestions.append("Consider if tests are still relevant")

        return UnusedFileCandidate(
            file_path=file_info.file_path,
            file_type=file_info.file_type,
            size_bytes=file_info.size_bytes,
            last_modified=file_info.last_modified,
            confidence=confidence,
            reasons=reasons,
            suggestions=suggestions
        )

    def _get_most_used_files(self, file_infos: Dict[str, FileInfo], top_n: int = 10) -> List[Dict]:
        """
        Get the most used files.

        Args:
            file_infos: Dict of file infos
            top_n: Number of top files to return

        Returns:
            List[Dict]: Most used files with usage info
        """
        # Sort by import count
        sorted_files = sorted(
            file_infos.values(),
            key=lambda f: f.import_count,
            reverse=True
        )

        # Convert to dicts
        return [
            {
                "file_path": f.file_path,
                "file_name": os.path.basename(f.file_path),
                "file_type": f.file_type,
                "import_count": f.import_count,
                "is_entry_point": f.is_entry_point,
                "size_bytes": f.size_bytes
            }
            for f in sorted_files[:top_n]
        ]

    def _calculate_statistics(self, file_infos: Dict[str, FileInfo],
                            unused_candidates: List[UnusedFileCandidate]) -> Dict:
        """Calculate statistics from analysis results."""
        total_size = sum(f.size_bytes for f in file_infos.values())
        unused_size = sum(c.size_bytes for c in unused_candidates)

        # Count by file type
        file_types = {}
        for f in file_infos.values():
            file_types[f.file_type] = file_types.get(f.file_type, 0) + 1

        # Count by confidence
        confidence_counts = {}
        for c in unused_candidates:
            confidence_counts[c.confidence] = confidence_counts.get(c.confidence, 0) + 1

        return {
            "total_size_mb": total_size / (1024 * 1024),
            "unused_size_mb": unused_size / (1024 * 1024),
            "unused_percentage": (len(unused_candidates) / len(file_infos) * 100) if file_infos else 0,
            "potential_savings_mb": unused_size / (1024 * 1024),
            "file_types": file_types,
            "confidence_counts": confidence_counts
        }

    def _generate_text_report(self, analysis: Dict) -> str:
        """Generate text format report."""
        lines = []
        lines.append("=" * 70)
        lines.append("FILE USAGE REPORT")
        lines.append("=" * 70)
        lines.append(f"Total Files: {analysis['total_files']}")
        lines.append(f"Total Size: {analysis['statistics']['total_size_mb']:.2f} MB")
        lines.append("")

        # Statistics
        stats = analysis['statistics']
        lines.append("STATISTICS:")
        lines.append(f"  Imported Files: {analysis['imported_files']}")
        lines.append(f"  Entry Points: {analysis['entry_points']}")
        lines.append(f"  Potentially Unused: {len(analysis['unused_candidates'])}")
        lines.append(f"  Unused Size: {stats['unused_size_mb']:.2f} MB ({stats['unused_percentage']:.1f}%)")
        lines.append(f"  Potential Savings: {stats['potential_savings_mb']:.2f} MB")
        lines.append("")

        # File types
        lines.append("FILE TYPES:")
        for file_type, count in stats['file_types'].items():
            lines.append(f"  {file_type}: {count}")
        lines.append("")

        # Most used files
        if analysis['most_used_files']:
            lines.append("MOST USED FILES:")
            lines.append("-" * 70)
            for f in analysis['most_used_files'][:10]:
                size_kb = f['size_bytes'] / 1024
                lines.append(f"  {f['file_name']}: imported {f['import_count']} times ({size_kb:.1f} KB)")
            lines.append("")

        # Potentially unused files
        if analysis['unused_candidates']:
            lines.append("POTENTIALLY UNUSED FILES:")
            lines.append("-" * 70)
            for candidate in analysis['unused_candidates'][:20]:  # Limit to first 20
                file_name = os.path.basename(candidate.file_path)
                age_days = (datetime.now() - candidate.last_modified).days
                size_kb = candidate.size_bytes / 1024
                lines.append(f"  {file_name} ({candidate.confidence} confidence)")
                lines.append(f"    Size: {size_kb:.1f} KB, Last modified: {age_days} days ago")
                if candidate.reasons:
                    lines.append(f"    Reasons:")
                    for reason in candidate.reasons[:2]:
                        lines.append(f"      - {reason}")
                if candidate.suggestions:
                    lines.append(f"    Suggestion: {candidate.suggestions[0]}")
            if len(analysis['unused_candidates']) > 20:
                lines.append(f"  ... and {len(analysis['unused_candidates']) - 20} more")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def _generate_markdown_report(self, analysis: Dict) -> str:
        """Generate markdown format report."""
        lines = []
        lines.append("# File Usage Report")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Files**: {analysis['total_files']}")
        lines.append(f"- **Total Size**: {analysis['statistics']['total_size_mb']:.2f} MB")
        lines.append(f"- **Imported Files**: {analysis['imported_files']}")
        lines.append(f"- **Entry Points**: {analysis['entry_points']}")
        lines.append(f"- **Potentially Unused**: {len(analysis['unused_candidates'])}")
        lines.append(f"- **Potential Savings**: {analysis['statistics']['potential_savings_mb']:.2f} MB")
        lines.append("")

        # File types
        lines.append("## File Types")
        lines.append("")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for file_type, count in analysis['statistics']['file_types'].items():
            lines.append(f"| {file_type} | {count} |")
        lines.append("")

        # Most used files
        if analysis['most_used_files']:
            lines.append("## Most Used Files")
            lines.append("")
            lines.append("| File | Imports | Size (KB) | Type |")
            lines.append("|------|---------|-----------|------|")
            for f in analysis['most_used_files'][:10]:
                size_kb = f['size_bytes'] / 1024
                lines.append(f"| {f['file_name']} | {f['import_count']} | {size_kb:.1f} | {f['file_type']} |")
            lines.append("")

        # Potentially unused files
        if analysis['unused_candidates']:
            lines.append("## Potentially Unused Files")
            lines.append("")
            lines.append("| File | Confidence | Age (days) | Size (KB) | Reason |")
            lines.append("|------|------------|------------|-----------|--------|")
            for candidate in analysis['unused_candidates'][:20]:
                file_name = os.path.basename(candidate.file_path)
                age_days = (datetime.now() - candidate.last_modified).days
                size_kb = candidate.size_bytes / 1024
                reason = candidate.reasons[0] if candidate.reasons else "N/A"
                lines.append(f"| {file_name} | {candidate.confidence} | {age_days} | {size_kb:.1f} | {reason} |")
            if len(analysis['unused_candidates']) > 20:
                lines.append(f"| ... | ... | ... | ... | and {len(analysis['unused_candidates']) - 20} more |")
            lines.append("")

        return "\n".join(lines)

    def _find_all_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Find all relevant files in directory."""
        all_files = []

        if recursive:
            for root, dirs, files in os.walk(directory):
                # Skip common directories to ignore
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'venv', 'node_modules', '.idea']]
                for file in files:
                    # Include various file types
                    if any(file.endswith(ext) for ext in ['.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg']):
                        all_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if any(file.endswith(ext) for ext in ['.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg']):
                    all_files.append(os.path.join(directory, file))

        return all_files

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

    def _determine_file_type(self, file_path: str) -> str:
        """Determine the type of file."""
        filename = os.path.basename(file_path)
        dirname = os.path.dirname(file_path)

        # Test files
        if 'test' in filename.lower() or 'tests' in dirname.lower():
            return 'test'

        # Documentation files
        if any(filename.endswith(ext) for ext in ['.md', '.txt']):
            return 'documentation'

        # Configuration files
        if any(filename.endswith(ext) for ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg']):
            return 'config'

        # Python files
        if filename.endswith('.py'):
            return 'python'

        # Other
        return 'other'

    def _resolve_import_to_file(self, module_name: str, importing_file: str) -> Optional[str]:
        """
        Resolve an import statement to an actual file path.

        Args:
            module_name: Name of imported module
            importing_file: File that contains the import

        Returns:
            str: Resolved file path or None
        """
        # This is a simplified implementation
        # In practice, you'd need to handle:
        # - Relative imports
        # - Multiple possible locations
        # - Package vs module imports

        # For absolute imports within project
        if '.' in module_name:
            # Try to find the module file
            parts = module_name.split('.')
            for i in range(len(parts), 0, -1):
                test_module = '.'.join(parts[:i])
                test_path = os.path.join(self.project_root, *parts[:i] + ['__init__.py'])
                if os.path.exists(test_path):
                    return test_path

                test_path = os.path.join(self.project_root, *parts[:i] + [parts[i] + '.py'] if i < len(parts) else [parts[-1] + '.py'])
                if os.path.exists(test_path):
                    return test_path

        # Simple module name
        test_path = os.path.join(self.project_root, module_name + '.py')
        if os.path.exists(test_path):
            return test_path

        # Try package
        test_path = os.path.join(self.project_root, module_name, '__init__.py')
        if os.path.exists(test_path):
            return test_path

        return None