"""
Dead Code Analysis Script for V6 Task 3.2
Runs dead code detector on core modules and categorizes findings.
"""

from v5.logic import DeadCodeDetector
import os

def analyze_core_modules():
    """Run dead code analysis on core modules."""
    
    # Initialize detector
    project_root = os.path.dirname(os.getcwd())  # Go up to parent directory
    detector = DeadCodeDetector(project_root=project_root)
    
    print('=' * 70)
    print('DEAD CODE ANALYSIS FOR CORE MODULES (V6 Task 3.2)')
    print('=' * 70)
    print()
    
    # Analyze functions
    print('DEAD FUNCTIONS:')
    print('-' * 70)
    dead_functions = detector.detect_dead_functions(include_test_files=False)
    core_functions = [f for f in dead_functions if any(path in f.file_path for path in ['/v5/core/', '/v5/data/', '/v5/logic/'])]
    print(f'Total Dead Functions in Core Modules: {len(core_functions)}')
    
    # Categorize by confidence
    high_conf_funcs = [f for f in core_functions if f.confidence == 'high']
    medium_conf_funcs = [f for f in core_functions if f.confidence == 'medium']
    low_conf_funcs = [f for f in core_functions if f.confidence == 'low']
    
    print(f'  High Confidence (safe to delete): {len(high_conf_funcs)}')
    print(f'  Medium Confidence (review needed): {len(medium_conf_funcs)}')
    print(f'  Low Confidence (investigate): {len(low_conf_funcs)}')
    print()
    
    # Analyze classes
    print('DEAD CLASSES:')
    print('-' * 70)
    dead_classes = detector.detect_dead_classes(include_test_files=False)
    core_classes = [c for c in dead_classes if any(path in c.file_path for path in ['/v5/core/', '/v5/data/', '/v5/logic/'])]
    print(f'Total Dead Classes in Core Modules: {len(core_classes)}')
    
    # Categorize by confidence
    high_conf_classes = [c for c in core_classes if c.confidence == 'high']
    medium_conf_classes = [c for c in core_classes if c.confidence == 'medium']
    low_conf_classes = [c for c in core_classes if c.confidence == 'low']
    
    print(f'  High Confidence (safe to delete): {len(high_conf_classes)}')
    print(f'  Medium Confidence (review needed): {len(medium_conf_classes)}')
    print(f'  Low Confidence (investigate): {len(low_conf_classes)}')
    print()
    
    # Analyze variables
    print('UNUSED VARIABLES:')
    print('-' * 70)
    unused_vars = detector.detect_unused_variables(include_test_files=False)
    core_vars = [v for v in unused_vars if any(path in v.file_path for path in ['/v5/core/', '/v5/data/', '/v5/logic/'])]
    print(f'Total Unused Variables in Core Modules: {len(core_vars)}')
    
    # Categorize by confidence
    high_conf_vars = [v for v in core_vars if v.confidence == 'high']
    medium_conf_vars = [v for v in core_vars if v.confidence == 'medium']
    low_conf_vars = [v for v in core_vars if v.confidence == 'low']
    
    print(f'  High Confidence (safe to delete): {len(high_conf_vars)}')
    print(f'  Medium Confidence (review needed): {len(medium_conf_vars)}')
    print(f'  Low Confidence (investigate): {len(low_conf_vars)}')
    print()
    
    # Summary
    print('=' * 70)
    print('SUMMARY')
    print('=' * 70)
    print(f'Total Dead Functions: {len(core_functions)}')
    print(f'Total Dead Classes: {len(core_classes)}')
    print(f'Total Unused Variables: {len(core_vars)}')
    print()
    print('Deletion Candidates by Confidence:')
    print(f'  High Confidence (>0.9): {len(high_conf_funcs + high_conf_classes + high_conf_vars)} items')
    print(f'  Medium Confidence (0.7-0.9): {len(medium_conf_funcs + medium_conf_classes + medium_conf_vars)} items')
    print(f'  Low Confidence (<0.7): {len(low_conf_funcs + low_conf_classes + low_conf_vars)} items')
    print()
    print('Recommendation:')
    print('  1. Review HIGH CONFIDENCE items for safe deletion (Task 3.3)')
    print('  2. Review MEDIUM CONFIDENCE items carefully before deletion')
    print('  3. Keep LOW CONFIDENCE items (may be used in future)')
    print('=' * 70)
    
    return {
        'functions': core_functions,
        'classes': core_classes,
        'variables': core_vars,
        'high_conf': high_conf_funcs + high_conf_classes + high_conf_vars,
        'medium_conf': medium_conf_funcs + medium_conf_classes + medium_conf_vars,
        'low_conf': low_conf_funcs + low_conf_classes + low_conf_vars
    }

if __name__ == '__main__':
    analyze_core_modules()