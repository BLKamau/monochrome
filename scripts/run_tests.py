#!/usr/bin/env python
"""
Enhanced test runner with coverage and reporting.
"""

import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def run_tests(coverage=True, verbose=False):
    """Run tests with optional coverage."""
    print(f"{Colors.BOLD}=== Running Monochrome Tests ==={Colors.ENDC}\n")
    
    cmd = [sys.executable]
    
    if coverage:
        cmd.extend(['-m', 'coverage', 'run', '--source=.', 'manage.py', 'test'])
    else:
        cmd.extend(['manage.py', 'test'])
    
    if verbose:
        cmd.append('--verbosity=2')
    
    # Run tests
    print(f"{Colors.BLUE}Running tests...{Colors.ENDC}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"\n{Colors.GREEN}✓ All tests passed!{Colors.ENDC}")
        
        if coverage:
            # Show coverage report
            print(f"\n{Colors.BLUE}Coverage Report:{Colors.ENDC}")
            subprocess.run([sys.executable, '-m', 'coverage', 'report'])
            
            # Generate HTML report
            subprocess.run([sys.executable, '-m', 'coverage', 'html'])
            print(f"\n{Colors.GREEN}HTML coverage report generated in htmlcov/{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}✗ Tests failed!{Colors.ENDC}")
        return False
    
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run Monochrome tests')
    parser.add_argument('--no-coverage', action='store_true', help='Run without coverage')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    run_tests(coverage=not args.no_coverage, verbose=args.verbose)


if __name__ == "__main__":
    main()
