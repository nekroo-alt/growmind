"""
Dependency Analyzer Module (V5)

Analyzes and manages project dependencies:
- Identifies unused dependencies (installed but not imported)
- Identifies outdated dependencies (newer version available)
- Generates cleanup reports
- Supports safe removal with backup
"""

import os
import re
import ast
import subprocess
import json
import shutil
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    
    name: str
    version: Optional[str] = None
    latest_version: Optional[str] = None
    is_used: bool = False
    is_outdated: bool = False
    is_sub_dependency: bool = False
    import_count: int = 0
    import_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'version': self.version,
            'latest_version': self.latest_version,
            'is_used': self.is_used,
            'is_outdated': self.is_outdated,
            'is_sub_dependency': self.is_sub_dependency,
            'import_count': self.import_count,
            'import_files': self.import_files
        }


@dataclass
class DependencyReport:
    """Report from dependency analysis."""
    
    total_dependencies: int = 0
    used_dependencies: int = 0
    unused_dependencies: int = 0
    outdated_dependencies: int = 0
    sub_dependencies: int = 0
    dependencies: List[DependencyInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """Add an error to the report."""
        self.errors.append(error)
        logger.error(error)
    
    def get_unused(self) -> List[DependencyInfo]:
        """Get list of unused dependencies."""
        return [d for d in self.dependencies if not d.is_used and not d.is_sub_dependency]
    
    def get_outdated(self) -> List[DependencyInfo]:
        """Get list of outdated dependencies."""
        return [d for d in self.dependencies if d.is_outdated]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'total_dependencies': self.total_dependencies,
            'used_dependencies': self.used_dependencies,
            'unused_dependencies': self.unused_dependencies,
            'outdated_dependencies': self.outdated_dependencies,
            'sub_dependencies': self.sub_dependencies,
            'dependencies': [d.to_dict() for d in self.dependencies],
            'errors': self.errors
        }


class DependencyAnalyzer:
    """
    Analyzes and manages project dependencies.
    
    Identifies unused and outdated dependencies, supports safe removal.
    """
    
    def __init__(self, 
                 project_root: str = '.',
                 requirements_files: Optional[List[str]] = None):
        """
        Initialize dependency analyzer.
        
        Args:
            project_root: Root directory of the project
            requirements_files: List of requirements files to analyze
        """
        self.project_root = Path(project_root)
        self.requirements_files = requirements_files or self._find_requirements_files()
        
        # Package to import name mapping (e.g., 'fastapi' -> 'fastapi', 'Pillow' -> 'PIL')
        self._package_import_map = {}
        self._build_package_import_map()
    
    def _find_requirements_files(self) -> List[str]:
        """Find requirements files in the project."""
        files = []
        
        # Common requirements files
        candidates = [
            'requirements.txt',
            'requirements-dev.txt',
            'requirements-test.txt',
            'setup.py',
            'pyproject.toml',
            'setup.cfg',
            'Pipfile',
            'poetry.lock'
        ]
        
        for candidate in candidates:
            if (self.project_root / candidate).exists():
                files.append(candidate)
        
        return files
    
    def _build_package_import_map(self):
        """
        Build mapping from package names to import names.
        
        PyPI package names can differ from their import names.
        E.g., 'Pillow' imports as 'PIL', 'beautifulsoup4' as 'bs4'.
        """
        # Common mappings
        self._package_import_map = {
            'beautifulsoup4': 'bs4',
            'pillow': 'PIL',
            'pillow-simd': 'PIL',
            'pillow-heif': 'PIL',
            'opencv-python': 'cv2',
            'opencv-python-headless': 'cv2',
            'pyyaml': 'yaml',
            'python-dotenv': 'dotenv',
            'pytest-cov': 'pytest_cov',
            'pytest-xdist': 'xdist',
            'python-dateutil': 'dateutil',
            'google-auth-oauthlib': 'google.auth.transport.requests',
            'matplotlib': 'matplotlib.pyplot',
            'networkx': 'networkx',
            'numpy': 'numpy',
            'pandas': 'pandas',
            'scipy': 'scipy',
            'scikit-learn': 'sklearn',
        }
    
    def analyze(self, check_outdated: bool = False) -> DependencyReport:
        """
        Analyze dependencies to identify unused and outdated ones.
        
        Args:
            check_outdated: Whether to check for outdated versions (slower)
            
        Returns:
            DependencyReport with analysis results
        """
        logger.info("Starting dependency analysis")
        report = DependencyReport()
        
        # Get installed packages
        installed_packages = self._get_installed_packages()
        report.total_dependencies = len(installed_packages)
        
        if not installed_packages:
            report.add_error("No installed packages found")
            return report
        
        # Get used imports
        used_imports = self._get_used_imports()
        
        # Get sub-dependencies
        sub_dependencies = self._get_sub_dependencies(set(installed_packages.keys()))
        
        # Analyze each package
        for package_name, package_version in installed_packages.items():
            dep_info = DependencyInfo(name=package_name, version=package_version)
            
            # Get import name for this package
            import_name = self._get_import_name(package_name)
            
            # Check if package is used
            if import_name in used_imports:
                dep_info.is_used = True
                dep_info.import_count = used_imports[import_name]['count']
                dep_info.import_files = used_imports[import_name]['files']
                report.used_dependencies += 1
            else:
                report.unused_dependencies += 1
            
            # Check if package is a sub-dependency
            if package_name in sub_dependencies:
                dep_info.is_sub_dependency = True
                report.sub_dependencies += 1
            
            # Check if package is outdated
            if check_outdated:
                latest_version = self._get_latest_version(package_name)
                if latest_version and latest_version != package_version:
                    dep_info.latest_version = latest_version
                    dep_info.is_outdated = True
                    report.outdated_dependencies += 1
            
            report.dependencies.append(dep_info)
        
        logger.info(f"Dependency analysis complete: {report.used_dependencies} used, "
                   f"{report.unused_dependencies} unused, {report.outdated_dependencies} outdated")
        
        return report
    
    def cleanup_unused(self, 
                     dry_run: bool = True,
                     backup: bool = True,
                     requirements_file: str = 'requirements.txt') -> Tuple[bool, List[str]]:
        """
        Remove unused dependencies from requirements file.
        
        Args:
            dry_run: If True, preview changes without actually removing
            backup: If True, create backup of requirements file before modification
            requirements_file: Requirements file to clean up
            
        Returns:
            Tuple of (success, removed_packages)
        """
        logger.info(f"Cleaning up unused dependencies (dry_run={dry_run})")
        
        # Analyze dependencies
        report = self.analyze()
        unused_deps = report.get_unused()
        
        if not unused_deps:
            logger.info("No unused dependencies found")
            return True, []
        
        logger.info(f"Found {len(unused_deps)} unused dependencies")
        
        # Read requirements file
        req_file = self.project_root / requirements_file
        if not req_file.exists():
            logger.error(f"Requirements file not found: {requirements_file}")
            return False, []
        
        # Create backup
        if backup and not dry_run:
            backup_file = req_file.with_suffix('.txt.backup')
            shutil.copy2(req_file, backup_file)
            logger.info(f"Created backup: {backup_file}")
        
        # Read and filter requirements
        with open(req_file, 'r') as f:
            lines = f.readlines()
        
        # Remove unused dependencies
        removed_packages = []
        new_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                new_lines.append(line)
                continue
            
            # Extract package name
            package_match = re.match(r'^([a-zA-Z0-9_-]+)', line_stripped)
            if package_match:
                package_name = package_match.group(1).lower()
                
                # Check if this package is unused
                is_unused = any(
                    dep.name.lower() == package_name 
                    for dep in unused_deps
                )
                
                if is_unused:
                    removed_packages.append(package_name)
                    logger.info(f"Would remove: {package_name}")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # Write updated requirements
        if not dry_run:
            with open(req_file, 'w') as f:
                f.writelines(new_lines)
            logger.info(f"Removed {len(removed_packages)} unused dependencies")
        else:
            logger.info(f"[DRY RUN] Would remove {len(removed_packages)} unused dependencies")
        
        return True, removed_packages
    
    def _get_installed_packages(self) -> Dict[str, str]:
        """
        Get list of installed packages with versions.
        
        Returns:
            Dictionary mapping package name to version
        """
        try:
            # Use pip list to get installed packages
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            packages = json.loads(result.stdout)
            
            return {
                pkg['name'].lower(): pkg['version']
                for pkg in packages
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get installed packages: {e}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pip list output: {e}")
            return {}
    
    def _get_used_imports(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all imports used in Python files.
        
        Returns:
            Dictionary mapping import name to usage info
        """
        imports = {}
        
        # Find all Python files
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in [
                '.git', '__pycache__', '.tox', '.venv', 'venv',
                'node_modules', 'build', 'dist', '*.egg-info'
            ]]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        # Parse imports from each file
        for file_path in python_files:
            try:
                self._extract_imports_from_file(file_path, imports)
            except Exception as e:
                logger.warning(f"Failed to parse imports from {file_path}: {e}")
        
        return imports
    
    def _extract_imports_from_file(self, file_path: str, imports: Dict):
        """
        Extract imports from a Python file using AST.
        
        Args:
            file_path: Path to Python file
            imports: Dictionary to populate with import info
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read(), filename=file_path)
            except SyntaxError:
                # Skip files with syntax errors
                return
        
        # Walk AST to find imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Handle: import module
                for alias in node.names:
                    import_name = alias.name
                    self._record_import(import_name, file_path, imports)
            
            elif isinstance(node, ast.ImportFrom):
                # Handle: from module import name
                module = node.module or ''
                for alias in node.names:
                    import_name = f"{module}.{alias.name}" if module else alias.name
                    self._record_import(import_name, file_path, imports)
    
    def _record_import(self, import_name: str, file_path: str, imports: Dict):
        """
        Record an import in the imports dictionary.
        
        Args:
            import_name: Full import name (e.g., 'package.module')
            file_path: Path to file containing import
            imports: Dictionary to populate
        """
        # Get top-level package
        parts = import_name.split('.')
        top_level = parts[0]
        
        # Record import
        if top_level not in imports:
            imports[top_level] = {
                'count': 0,
                'files': []
            }
        
        imports[top_level]['count'] += 1
        imports[top_level]['files'].append(file_path)
    
    def _get_import_name(self, package_name: str) -> str:
        """
        Get the import name for a package.
        
        Args:
            package_name: Package name from requirements
            
        Returns:
            Import name used in Python code
        """
        # Check explicit mapping
        if package_name.lower() in self._package_import_map:
            import_name = self._package_import_map[package_name.lower()]
            # Get top-level import name
            return import_name.split('.')[0]
        
        # Default: use package name
        return package_name.lower()
    
    def _get_sub_dependencies(self, packages: Set[str]) -> Set[str]:
        """
        Identify sub-dependencies (dependencies of dependencies).
        
        Args:
            packages: Set of installed package names
            
        Returns:
            Set of sub-dependency names
        """
        sub_deps = set()
        
        try:
            # Use pip show to get dependencies
            for package in packages:
                result = subprocess.run(
                    ['pip', 'show', package],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    # Parse 'Requires' field
                    for line in result.stdout.splitlines():
                        if line.startswith('Requires:'):
                            requires_str = line.split(':', 1)[1].strip()
                            if requires_str:
                                # Parse dependencies (comma-separated, may have version specs)
                                for req in requires_str.split(','):
                                    req_name = re.sub(r'[\s<>=!~[].*$', '', req.strip())
                                    if req_name:
                                        sub_deps.add(req_name.lower())
            
        except Exception as e:
            logger.warning(f"Failed to get sub-dependencies: {e}")
        
        return sub_deps
    
    def _get_latest_version(self, package_name: str) -> Optional[str]:
        """
        Get latest version of a package from PyPI.
        
        Args:
            package_name: Package name
            
        Returns:
            Latest version string or None if not available
        """
        try:
            result = subprocess.run(
                ['pip', 'index', 'versions', package_name],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )
            
            if result.returncode == 0:
                # Output is space-separated list of versions
                versions = result.stdout.strip().split()
                if versions:
                    # Return last version (latest)
                    return versions[-1]
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking latest version for {package_name}")
        except Exception as e:
            logger.warning(f"Failed to get latest version for {package_name}: {e}")
        
        return None
    
    def generate_report(self, report: Optional[DependencyReport] = None) -> str:
        """
        Generate human-readable report.
        
        Args:
            report: Dependency report (generates if not provided)
            
        Returns:
            Formatted report string
        """
        if report is None:
            report = self.analyze()
        
        lines = []
        lines.append("=" * 70)
        lines.append("DEPENDENCY ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Summary
        lines.append("Summary:")
        lines.append(f"  Total Dependencies:    {report.total_dependencies}")
        lines.append(f"  Used:                 {report.used_dependencies}")
        lines.append(f"  Unused:               {report.unused_dependencies}")
        lines.append(f"  Outdated:             {report.outdated_dependencies}")
        lines.append(f"  Sub-dependencies:      {report.sub_dependencies}")
        lines.append("")
        
        # Unused dependencies
        unused = report.get_unused()
        if unused:
            lines.append("-" * 70)
            lines.append("UNUSED DEPENDENCIES (safe to remove):")
            lines.append("-" * 70)
            for dep in unused:
                lines.append(f"  - {dep.name} (version: {dep.version})")
            lines.append("")
        
        # Outdated dependencies
        outdated = report.get_outdated()
        if outdated:
            lines.append("-" * 70)
            lines.append("OUTDATED DEPENDENCIES:")
            lines.append("-" * 70)
            for dep in outdated:
                lines.append(f"  - {dep.name}")
                lines.append(f"    Current:  {dep.version}")
                lines.append(f"    Latest:   {dep.latest_version}")
            lines.append("")
        
        # Errors
        if report.errors:
            lines.append("-" * 70)
            lines.append("ERRORS:")
            lines.append("-" * 70)
            for error in report.errors:
                lines.append(f"  - {error}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)