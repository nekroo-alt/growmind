#!/usr/bin/env python3
"""
Consolidated test runner for L4D V2 AST analysis components

This script runs all unit tests and generates coverage reports for the new AST analysis modules.
Ensures >80% code coverage for new modules.
"""
import sys
import os
import subprocess
import argparse


def run_pytest(coverage: bool = True, verbose: bool = False):
    """Run pytest with coverage"""
    # Get directory paths
    test_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(test_dir)
    
    # Add parent directory to path
    sys.path.insert(0, parent_dir)
    
    # Build pytest command
    cmd = [
        "python", "-m", "pytest",
        test_dir,  # Run tests from this directory
        os.path.join(parent_dir, "test_*.py"),  # Also run existing test files in v1/
    ]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_html",
            "--cov-fail-under=80"
        ])
    
    # Coverage configuration - focus on new modules
    if coverage:
        os.environ["COVERAGE_FILE"] = ".coverage.v2"
    
    print(f"\n{'='*60}")
    print("Running L4D V2 Test Suite")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    
    return result.returncode


def check_coverage():
    """Check if coverage meets the 80% threshold"""
    print(f"\n{'='*60}")
    print("Coverage Summary")
    print(f"{'='*60}\n")
    
    # Check if coverage file exists
    coverage_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".coverage.v2")
    
    if not os.path.exists(coverage_file):
        print("Warning: Coverage file not found")
        return False
    
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run L4D V2 test suite")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Run tests
    return_code = run_pytest(coverage=not args.no_coverage, verbose=args.verbose)
    
    if not args.no_coverage:
        check_coverage()
    
    sys.exit(return_code)


if __name__ == "__main__":
    main()
