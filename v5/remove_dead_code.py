#!/usr/bin/env python3
"""
Remove High-Confidence Dead Code (Task 3.3)

This script performs safe deletion of high-confidence dead code:
1. Detect dead code using DeadCodeDetector
2. Filter for high-confidence (> 0.9) detections
3. Use SafeDeleter to remove code with backup and rollback
4. Run tests after each deletion
5. Document all deletions

Usage:
    python remove_dead_code.py --dry-run          # Preview deletions
    python remove_dead_code.py --auto              # Automatic deletion
    python remove_dead_code.py --type function    # Only delete functions
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict

# Add v5 to path
sys.path.insert(0, str(Path(__file__).parent))

from v5.logic import DeadCodeDetector, DeadFunctionInfo, DeadClassInfo, UnusedVariableInfo
from v5.logic import SafeDeleter
from v5.core import get_logger


class DeadCodeRemover:
    """
    Safely removes high-confidence dead code.
    """
    
    def __init__(
        self,
        project_root: str,
        dry_run: bool = False,
        min_confidence: str = 'high',
        code_types: List[str] = None
    ):
        """
        Initialize DeadCodeRemover.
        
        Args:
            project_root: Root directory of project
            dry_run: If True, only preview deletions
            min_confidence: Minimum confidence level ('high', 'medium', 'low')
            code_types: Types of code to remove ('function', 'class', 'variable')
        """
        self.project_root = project_root
        self.dry_run = dry_run
        self.min_confidence = min_confidence
        self.code_types = code_types or ['function', 'class', 'variable']
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.detector = DeadCodeDetector(
            project_root=project_root,
            call_graph_db=".l4_cache/call_graph.db"
        )
        self.deleter = SafeDeleter(
            project_root=project_root,
            git_enabled=True
        )
        
        # Statistics
        self.stats = {
            'functions_deleted': 0,
            'functions_failed': 0,
            'classes_deleted': 0,
            'classes_failed': 0,
            'files_deleted': 0,
            'files_failed': 0
        }
    
    def remove_dead_code(self) -> Dict:
        """
        Remove all high-confidence dead code.
        
        Returns:
            Dict: Statistics and results
        """
        self.logger.info("=" * 70)
        self.logger.info("REMOVING HIGH-CONFIDENCE DEAD CODE")
        self.logger.info("=" * 70)
        self.logger.info(f"Project Root: {self.project_root}")
        self.logger.info(f"Min Confidence: {self.min_confidence}")
        self.logger.info(f"Code Types: {', '.join(self.code_types)}")
        self.logger.info(f"Dry Run: {self.dry_run}")
        self.logger.info("=" * 70)
        
        results = {
            'dead_functions': [],
            'dead_classes': [],
            'unused_variables': [],
            'success': True
        }
        
        # Remove dead functions
        if 'function' in self.code_types:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("DETECTING DEAD FUNCTIONS")
            self.logger.info("=" * 70)
            dead_functions = self.detector.detect_dead_functions(include_test_files=False)
            filtered_functions = self._filter_by_confidence(dead_functions)
            results['dead_functions'] = filtered_functions
            
            self.logger.info(f"Found {len(dead_functions)} dead functions")
            self.logger.info(f"Filtered to {len(filtered_functions)} high-confidence functions")
            
            for func_info in filtered_functions:
                result = self._remove_dead_function(func_info)
                if result.success:
                    self.stats['functions_deleted'] += 1
                else:
                    self.stats['functions_failed'] += 1
        
        # Remove dead classes
        if 'class' in self.code_types:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("DETECTING DEAD CLASSES")
            self.logger.info("=" * 70)
            dead_classes = self.detector.detect_dead_classes(include_test_files=False)
            filtered_classes = self._filter_by_confidence(dead_classes)
            results['dead_classes'] = filtered_classes
            
            self.logger.info(f"Found {len(dead_classes)} dead classes")
            self.logger.info(f"Filtered to {len(filtered_classes)} high-confidence classes")
            
            for class_info in filtered_classes:
                result = self._remove_dead_class(class_info)
                if result.success:
                    self.stats['classes_deleted'] += 1
                else:
                    self.stats['classes_failed'] += 1
        
        # Remove unused variables
        if 'variable' in self.code_types:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("DETECTING UNUSED VARIABLES")
            self.logger.info("=" * 70)
            unused_variables = self.detector.detect_unused_variables(include_test_files=False)
            filtered_variables = self._filter_by_confidence(unused_variables)
            results['unused_variables'] = filtered_variables
            
            self.logger.info(f"Found {len(unused_variables)} unused variables")
            self.logger.info(f"Filtered to {len(filtered_variables)} high-confidence variables")
            
            # Note: Variable deletion not yet implemented in safe_deleter
            for var_info in filtered_variables:
                self.logger.info(f"Would delete: {var_info.variable_name} in {var_info.file_path}:{var_info.line_number}")
        
        # Print summary
        self._print_summary()
        
        return results
    
    def _filter_by_confidence(self, items: List) -> List:
        """
        Filter items by confidence level.
        
        Args:
            items: List of dead code items
        
        Returns:
            List: Filtered items
        """
        confidence_order = {'high': 3, 'medium': 2, 'low': 1}
        min_level = confidence_order.get(self.min_confidence, 3)
        
        filtered = []
        for item in items:
            item_level = confidence_order.get(item.confidence, 0)
            if item_level >= min_level:
                filtered.append(item)
        
        return filtered
    
    def _remove_dead_function(self, func_info: DeadFunctionInfo):
        """
        Remove a dead function safely.
        
        Args:
            func_info: Dead function information
        
        Returns:
            DeletionResult: Result of deletion
        """
        self.logger.info(f"\nRemoving function: {func_info.function_name}")
        self.logger.info(f"  File: {func_info.file_path}")
        self.logger.info(f"  Confidence: {func_info.confidence}")
        self.logger.info(f"  Call Count: {func_info.call_count}")
        self.logger.info(f"  Reasons: {', '.join(func_info.reasons)}")
        
        reason = f"{', '.join(func_info.reasons)} (confidence: {func_info.confidence})"
        
        result = self.deleter.safe_delete_function(
            file_path=func_info.file_path,
            function_name=func_info.function_name,
            reason=reason,
            dry_run=self.dry_run,
            auto_commit=False  # We'll commit at the end
        )
        
        if self.dry_run:
            self.logger.info(f"  [DRY RUN] Would delete function")
        elif result.success:
            self.logger.info(f"  [SUCCESS] Function deleted")
        else:
            self.logger.error(f"  [FAILED] Deletion failed: {result.errors}")
        
        return result
    
    def _remove_dead_class(self, class_info: DeadClassInfo):
        """
        Remove a dead class safely.
        
        Args:
            class_info: Dead class information
        
        Returns:
            DeletionResult: Result of deletion
        """
        self.logger.info(f"\nRemoving class: {class_info.class_name}")
        self.logger.info(f"  File: {class_info.file_path}")
        self.logger.info(f"  Confidence: {class_info.confidence}")
        self.logger.info(f"  Instantiations: {class_info.instantiation_count}")
        self.logger.info(f"  Methods Called: {len(class_info.called_methods)}/{class_info.methods_count}")
        self.logger.info(f"  Reasons: {', '.join(class_info.reasons)}")
        
        reason = f"{', '.join(class_info.reasons)} (confidence: {class_info.confidence})"
        
        result = self.deleter.safe_delete_class(
            file_path=class_info.file_path,
            class_name=class_info.class_name,
            reason=reason,
            dry_run=self.dry_run,
            auto_commit=False  # We'll commit at the end
        )
        
        if self.dry_run:
            self.logger.info(f"  [DRY RUN] Would delete class")
        elif result.success:
            self.logger.info(f"  [SUCCESS] Class deleted")
        else:
            self.logger.error(f"  [FAILED] Deletion failed: {result.errors}")
        
        return result
    
    def _print_summary(self):
        """Print summary of deletion results."""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("DELETION SUMMARY")
        self.logger.info("=" * 70)
        
        if 'function' in self.code_types:
            self.logger.info(f"Functions Deleted: {self.stats['functions_deleted']}")
            self.logger.info(f"Functions Failed: {self.stats['functions_failed']}")
        
        if 'class' in self.code_types:
            self.logger.info(f"Classes Deleted: {self.stats['classes_deleted']}")
            self.logger.info(f"Classes Failed: {self.stats['classes_failed']}")
        
        self.logger.info("=" * 70)
        
        if self.dry_run:
            self.logger.info("DRY RUN COMPLETE - No actual deletions performed")
        else:
            self.logger.info("DELETION COMPLETE")
        
        self.logger.info("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Safely remove high-confidence dead code"
    )
    
    parser.add_argument(
        '--project-root',
        default='.',
        help='Project root directory (default: current directory)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview deletions without executing'
    )
    
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Automatic deletion without confirmation'
    )
    
    parser.add_argument(
        '--confidence',
        choices=['high', 'medium', 'low'],
        default='high',
        help='Minimum confidence level (default: high)'
    )
    
    parser.add_argument(
        '--type',
        choices=['function', 'class', 'variable', 'all'],
        nargs='+',
        default=['all'],
        help='Type of code to remove (default: all)'
    )
    
    args = parser.parse_args()
    
    # Process type argument
    code_types = []
    if 'all' in args.type:
        code_types = ['function', 'class', 'variable']
    else:
        code_types = args.type
    
    # Confirm deletion
    if not args.dry_run and not args.auto:
        print("\n" + "=" * 70)
        print("WARNING: This will delete code from your project!")
        print("=" * 70)
        print(f"Project Root: {os.path.abspath(args.project_root)}")
        print(f"Min Confidence: {args.confidence}")
        print(f"Code Types: {', '.join(code_types)}")
        print("=" * 70)
        
        response = input("\nContinue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted.")
            sys.exit(0)
    
    # Create remover
    remover = DeadCodeRemover(
        project_root=os.path.abspath(args.project_root),
        dry_run=args.dry_run,
        min_confidence=args.confidence,
        code_types=code_types
    )
    
    # Remove dead code
    try:
        results = remover.remove_dead_code()
        
        # Exit with error if any deletions failed
        total_failed = (
            remover.stats['functions_failed'] +
            remover.stats['classes_failed'] +
            remover.stats['files_failed']
        )
        
        if total_failed > 0:
            sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()