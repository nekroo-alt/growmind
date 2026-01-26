#!/usr/bin/env python
"""
Script to update imports in test files after moving to subdirectories.
"""

import re
from pathlib import Path


def update_imports(file_path):
    """Update imports in a test file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track if any changes were made
    original_content = content
    
    # Update imports from data, logic, core, retro, llm_base, cli modules
    # Pattern: from data.X import -> from v5.data.X import
    # Pattern: from logic.X import -> from v5.logic.X import
    # etc.
    
    modules = ['data', 'logic', 'core', 'retro', 'llm_base', 'cli', 'utilities']
    
    for module in modules:
        # Match: from <module>. import
        pattern = rf'\bfrom {module}\.'
        replacement = f'from v5.{module}.'
        content = re.sub(pattern, replacement, content)
    
    # If changes were made, write back
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False


def fix_all_imports(tests_dir):
    """Fix imports in all test files in subdirectories."""
    fixed_files = []
    skipped_files = []
    
    # Iterate over test files in subdirectories
    for subdir in tests_dir.iterdir():
        if not subdir.is_dir():
            continue
        
        # Process all Python files in subdirectory
        for test_file in subdir.glob('test_*.py'):
            if update_imports(test_file):
                fixed_files.append(test_file.relative_to(tests_dir))
            else:
                skipped_files.append(test_file.relative_to(tests_dir))
    
    # Print summary
    print("\n" + "="*60)
    print("IMPORT FIX SUMMARY")
    print("="*60)
    
    if fixed_files:
        print(f"\nFixed imports in ({len(fixed_files)} files):")
        for file in sorted(fixed_files):
            print(f"  {file}")
    
    if skipped_files:
        print(f"\nSkipped ({len(skipped_files)} files - no changes needed):")
        for file in sorted(skipped_files)[:10]:  # Show first 10
            print(f"  {file}")
        if len(skipped_files) > 10:
            print(f"  ... and {len(skipped_files) - 10} more")
    
    print("\n" + "="*60)
    
    return len(fixed_files)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix imports in test files")
    parser.add_argument("--dry-run", action="store_true", default=False,
                       help="Show what would be done without actually making changes")
    
    args = parser.parse_args()
    
    # Get tests directory
    script_dir = Path(__file__).parent
    tests_dir = script_dir / "tests" / "unit"
    
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
        exit(1)
    
    if args.dry_run:
        print("DRY RUN - Use without --dry-run to actually fix imports")
        # Just check which files would be modified
        modified = 0
        for subdir in tests_dir.iterdir():
            if not subdir.is_dir():
                continue
            for test_file in subdir.glob('test_*.py'):
                with open(test_file, 'r') as f:
                    content = f.read()
                modules = ['data', 'logic', 'core', 'retro', 'llm_base', 'cli', 'utilities']
                for module in modules:
                    pattern = rf'\bfrom {module}\.'
                    if re.search(pattern, content):
                        modified += 1
                        print(f"Would fix: {test_file.relative_to(tests_dir)}")
                        break
        print(f"\nTotal files to fix: {modified}")
    else:
        print("FIXING IMPORTS IN TEST FILES")
        fixed_count = fix_all_imports(tests_dir)
        print(f"\nFixed imports in {fixed_count} files")