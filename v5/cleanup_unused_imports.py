#!/usr/bin/env python3
"""
Cleanup Unused Imports Script (Task 3.4)

Detects and removes unused imports, organizes imports by:
1. Standard library
2. Third-party
3. Local imports

Also sorts imports alphabetically within each section.
"""

import ast
import os
import sys
import re
from pathlib import Path
from collections import OrderedDict
from typing import Dict, List, Tuple, Set

# Standard library modules (subset)
STANDARD_LIBRARY = {
    'abc', 'argparse', 'array', 'ast', 'asyncio', 'base64', 'bisect', 'builtins',
    'calendar', 'cgi', 'collections', 'colorsys', 'compileall', 'concurrent',
    'configparser', 'contextlib', 'copy', 'csv', 'ctypes', 'dataclasses',
    'datetime', 'decimal', 'difflib', 'dis', 'doctest', 'email', 'enum',
    'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
    'formatter', 'fractions', 'ftplib', 'functools', 'gc', 'getopt',
    'getpass', 'gettext', 'glob', 'graphlib', 'grp', 'hashlib', 'heapq',
    'hmac', 'html', 'http', 'imaplib', 'imghdr', 'imp', 'importlib',
    'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3',
    'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap',
    'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder', 'msilib',
    'msvcrt', 'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers',
    'operator', 'optparse', 'os', 'ossaudiodev', 'pathlib', 'pdb', 'pickle',
    'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib',
    'posix', 'posixpath', 'pprint', 'profile', 'pstats', 'pty', 'pwd',
    'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri', 'random', 're',
    'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched',
    'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal',
    'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd',
    'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct',
    'subprocess', 'sunau', 'symbol', 'symtable', 'sys', 'sysconfig', 'syslog',
    'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test',
    'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token',
    'tokenize', 'tomllib', 'trace', 'traceback', 'tracemalloc', 'tty',
    'turtle', 'turtledemo', 'types', 'typing', 'typing_extensions', 'unicodedata',
    'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave',
    'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib',
    'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib',
}


class ImportUsage:
    """Track import usage across a file."""
    
    def __init__(self):
        self.imported: Dict[str, List[Tuple[int, str]]] = {}  # name -> [(line, full_import), ...]
        self.used: Set[str] = set()
    
    def add_import(self, name: str, line: int, full_import: str):
        """Add an imported name."""
        if name not in self.imported:
            self.imported[name] = []
        self.imported[name].append((line, full_import))
    
    def add_usage(self, name: str):
        """Mark an imported name as used."""
        self.used.add(name)
    
    def get_unused_imports(self) -> List[Tuple[int, str]]:
        """Get list of unused imports with line numbers."""
        unused = []
        for name, import_list in self.imported.items():
            # Check if any part of import is used
            used = False
            for used_name in self.used:
                if used_name.startswith(name) or name.startswith(used_name):
                    used = True
                    break
            
            if not used:
                for line, full_import in import_list:
                    unused.append((line, full_import))
        
        return sorted(unused, key=lambda x: x[0], reverse=True)


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to track imports and their usage."""
    
    def __init__(self, import_usage: ImportUsage):
        self.import_usage = import_usage
    
    def visit_Import(self, node: ast.Import):
        """Handle: import module"""
        for alias in node.names:
            # Track imported name
            name = alias.asname if alias.asname else alias.name
            self.import_usage.add_import(
                name,
                node.lineno,
                f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
            )
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Handle: from module import name"""
        module = node.module or ''
        
        for alias in node.names:
            # Track imported name
            name = alias.asname if alias.asname else alias.name
            full_import = f"from {module} import {alias.name}"
            if alias.asname:
                full_import += f" as {alias.asname}"
            
            self.import_usage.add_import(name, node.lineno, full_import)
        
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        """Track usage of names."""
        if node.id in self.import_usage.imported:
            self.import_usage.add_usage(node.id)
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Track class-level decorators (e.g., @dataclass)."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id in self.import_usage.imported:
                    self.import_usage.add_usage(decorator.id)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    if decorator.func.id in self.import_usage.imported:
                        self.import_usage.add_usage(decorator.func.id)
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function-level decorators and return type hints."""
        # Track decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id in self.import_usage.imported:
                    self.import_usage.add_usage(decorator.id)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    if decorator.func.id in self.import_usage.imported:
                        self.import_usage.add_usage(decorator.func.id)
        
        # Track return type annotation
        if node.returns:
            if isinstance(node.returns, ast.Name):
                if node.returns.id in self.import_usage.imported:
                    self.import_usage.add_usage(node.returns.id)
            elif isinstance(node.returns, ast.Subscript):
                # Handle List[int], Optional[str], etc.
                if isinstance(node.returns.value, ast.Name):
                    if node.returns.value.id in self.import_usage.imported:
                        self.import_usage.add_usage(node.returns.value.id)
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute):
        """Track usage of attributes (e.g., module.function)."""
        if isinstance(node.value, ast.Name):
            # e.g., module.function
            name = node.value.id
            if name in self.import_usage.imported:
                self.import_usage.add_usage(name)
        
        self.generic_visit(node)
    
    def visit_arg(self, node: ast.arg):
        """Track type hints in function arguments."""
        # Track annotation if it's a Name
        if node.annotation:
            if isinstance(node.annotation, ast.Name):
                if node.annotation.id in self.import_usage.imported:
                    self.import_usage.add_usage(node.annotation.id)
            elif isinstance(node.annotation, ast.Subscript):
                # Handle List[int], Optional[str], etc.
                if isinstance(node.annotation.value, ast.Name):
                    if node.annotation.value.id in self.import_usage.imported:
                        self.import_usage.add_usage(node.annotation.value.id)
        
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Track type hints in variable annotations."""
        if node.annotation:
            if isinstance(node.annotation, ast.Name):
                if node.annotation.id in self.import_usage.imported:
                    self.import_usage.add_usage(node.annotation.id)
            elif isinstance(node.annotation, ast.Subscript):
                # Handle List[int], Optional[str], etc.
                if isinstance(node.annotation.value, ast.Name):
                    if node.annotation.value.id in self.import_usage.imported:
                        self.import_usage.add_usage(node.annotation.value.id)
        
        self.generic_visit(node)


def is_standard_library(module_name: str) -> bool:
    """Check if module is from standard library."""
    # Get top-level package
    top_level = module_name.split('.')[0]
    return top_level in STANDARD_LIBRARY


def is_local_import(module_name: str, project_root: Path) -> bool:
    """Check if module is from local project."""
    # Get top-level package
    top_level = module_name.split('.')[0]
    
    # Check if top-level package exists in project
    package_dir = project_root / top_level
    return package_dir.exists() and package_dir.is_dir()


def categorize_import(module_name: str, project_root: Path) -> str:
    """Categorize import as standard, third-party, or local."""
    if is_standard_library(module_name):
        return 'standard'
    elif is_local_import(module_name, project_root):
        return 'local'
    else:
        return 'third-party'


def extract_import_line(import_statement: str) -> Tuple[str, str]:
    """
    Extract import line and categorize it.
    
    Returns:
        Tuple of (import_line, category)
    """
    # Determine category based on module name
    match = re.match(r'^(?:from\s+)?([a-zA-Z0-9_]+)', import_statement)
    if match:
        module_name = match.group(1)
        category = categorize_import(module_name, Path('.'))
        return (import_statement, category)
    
    return (import_statement, 'third-party')


def reorganize_imports(content: str, project_root: Path) -> str:
    """
    Reorganize imports in a Python file.
    
    Groups imports by:
    1. Standard library
    2. Third-party
    3. Local
    
    And sorts alphabetically within each group.
    """
    lines = content.split('\n')
    
    # Find import section
    import_lines = []
    docstring_lines = []
    non_import_lines = []
    
    in_docstring = False
    import_section_ended = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for module docstring
        if not import_section_ended and i == 0 and (stripped.startswith('"""') or stripped.startswith("'''")):
            in_docstring = True
            docstring_lines.append(line)
            # Check if docstring ends on same line
            if (stripped.endswith('"""') or stripped.endswith("'''")) and len(stripped) > 3:
                in_docstring = False
            continue
        
        # End of docstring
        if in_docstring and (stripped.endswith('"""') or stripped.endswith("'''")):
            docstring_lines.append(line)
            in_docstring = False
            continue
        
        # In docstring
        if in_docstring:
            docstring_lines.append(line)
            continue
        
        # Check for import statements
        if not import_section_ended and (stripped.startswith('import ') or stripped.startswith('from ')):
            import_lines.append(line)
        else:
            # Empty line ends import section (unless we haven't started imports yet)
            if not import_lines and not stripped:
                # Still before imports, add to docstring/output
                if docstring_lines:
                    docstring_lines.append(line)
                else:
                    non_import_lines.append(line)
            elif import_lines:
                # End of import section
                if not stripped:
                    # Keep separator blank line
                    import_section_ended = True
                    non_import_lines.append(line)
                else:
                    import_section_ended = True
                    non_import_lines.append(line)
            else:
                import_section_ended = True
                non_import_lines.append(line)
    
    # Categorize and sort imports
    standard_imports = OrderedDict()
    third_party_imports = OrderedDict()
    local_imports = OrderedDict()
    
    for line in import_lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Skip comments
        if stripped.startswith('#'):
            continue
        
        # Categorize import
        module_match = re.match(r'^(?:from\s+)?([a-zA-Z0-9_]+)', stripped)
        if module_match:
            module_name = module_match.group(1)
            category = categorize_import(module_name, project_root)
            
            # Extract the full import statement (with original indentation)
            # Remove trailing comments
            import_clean = re.sub(r'\s+#.*$', '', line)
            import_clean = import_clean.rstrip()
            
            # Add to appropriate category
            if category == 'standard':
                # Use stripped version for sorting, keep original for output
                key = import_clean.strip()
                standard_imports[key] = import_clean
            elif category == 'local':
                key = import_clean.strip()
                local_imports[key] = import_clean
            else:
                key = import_clean.strip()
                third_party_imports[key] = import_clean
        else:
            # Can't categorize, add to third-party as default
            import_clean = re.sub(r'\s+#.*$', '', line)
            import_clean = import_clean.rstrip()
            key = import_clean.strip()
            third_party_imports[key] = import_clean
    
    # Sort imports alphabetically within each category
    standard_sorted = sorted(standard_imports.items(), key=lambda x: x[0])
    third_party_sorted = sorted(third_party_imports.items(), key=lambda x: x[0])
    local_sorted = sorted(local_imports.items(), key=lambda x: x[0])
    
    # Rebuild file content
    new_lines = []
    
    # Docstring
    new_lines.extend(docstring_lines)
    if docstring_lines:
        new_lines.append('')
    
    # Imports (standard, third-party, local)
    all_imports = []
    
    if standard_sorted:
        for _, import_line in standard_sorted:
            all_imports.append(import_line)
    
    if third_party_sorted:
        if all_imports:
            all_imports.append('')  # Blank line between categories
        for _, import_line in third_party_sorted:
            all_imports.append(import_line)
    
    if local_sorted:
        if all_imports:
            all_imports.append('')  # Blank line between categories
        for _, import_line in local_sorted:
            all_imports.append(import_line)
    
    # Add blank line after imports if there's code
    if all_imports and non_import_lines:
        all_imports.append('')
    
    new_lines.extend(all_imports)
    new_lines.extend(non_import_lines)
    
    return '\n'.join(new_lines)


def analyze_file(file_path: str, project_root: Path) -> ImportUsage:
    """Analyze a Python file for unused imports."""
    import_usage = ImportUsage()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=file_path)
        
        # Track imports and usage
        analyzer = ImportAnalyzer(import_usage)
        analyzer.visit(tree)
        
    except SyntaxError as e:
        print(f"  Syntax error in {file_path}: {e}")
    except Exception as e:
        print(f"  Error analyzing {file_path}: {e}")
    
    return import_usage


def remove_unused_imports(file_path: str, unused_imports: List[Tuple[int, str]], dry_run: bool = True):
    """Remove unused imports from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Remove unused imports (process in reverse line order to preserve line numbers)
        lines_to_remove = set(line_num - 1 for line_num, _ in unused_imports)
        
        new_lines = []
        for i, line in enumerate(lines):
            if i in lines_to_remove:
                # Check if this line is just an import (not part of multi-line import)
                stripped = line.strip()
                if not stripped.startswith('import ') and not stripped.startswith('from '):
                    # Keep's line
                    new_lines.append(line)
                # Skip import line
            else:
                new_lines.append(line)
        
        # Remove consecutive blank lines caused by removal
        cleaned_lines = []
        prev_blank = False
        for line in new_lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            cleaned_lines.append(line)
            prev_blank = is_blank
        
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
    
    except Exception as e:
        print(f"  Error modifying {file_path}: {e}")


def main():
    """Main cleanup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup unused imports in Python files')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    parser.add_argument('--directory', default='v5', help='Directory to scan (default: v5)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    project_root = Path(args.directory)
    if not project_root.exists():
        print(f"Error: Directory not found: {project_root}")
        return 1
    
    print(f"Scanning directory: {project_root}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip common non-code directories
        dirs[:] = [d for d in dirs if d not in [
            '.git', '__pycache__', '.tox', '.venv', 'venv',
            'node_modules', 'build', 'dist', '*.egg-info', '.pytest_cache'
        ]]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files")
    print()
    
    total_unused = 0
    total_files = 0
    
    for file_path in python_files:
        if args.verbose:
            print(f"Analyzing: {file_path}")
        
        # Analyze imports
        import_usage = analyze_file(file_path, project_root)
        unused = import_usage.get_unused_imports()
        
        if unused:
            relative_path = os.path.relpath(file_path, '.')
            print(f"  {relative_path}: {len(unused)} unused import(s)")
            
            if args.verbose:
                for line_num, import_stmt in unused:
                    print(f"    Line {line_num}: {import_stmt}")
            
            # Remove unused imports
            if not args.dry_run:
                remove_unused_imports(file_path, unused, dry_run=False)
            
            # Reorganize imports
            if not args.dry_run:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = reorganize_imports(content, project_root)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                except Exception as e:
                    print(f"  Error reorganizing imports: {e}")
            
            total_unused += len(unused)
            total_files += 1
    
    print()
    print("=" * 70)
    print(f"Summary:")
    print(f"  Total files processed:    {len(python_files)}")
    print(f"  Files with unused imports: {total_files}")
    print(f"  Total unused imports:     {total_unused}")
    print("=" * 70)
    
    if args.dry_run:
        print()
        print("[DRY RUN] No files were modified. Run without --dry-run to apply changes.")
    else:
        print()
        print(f"Modified {total_files} file(s) with {total_unused} unused import(s) removed.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())