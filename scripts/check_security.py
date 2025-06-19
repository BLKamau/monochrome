#!/usr/bin/env python
"""
Security checker script.
Checks for common security issues in the configuration.
"""

import os
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def check_env_security():
    """Check .env file for security issues."""
    print(f"{Colors.BOLD}Checking environment security...{Colors.ENDC}")
    
    env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        print(f"{Colors.RED}✗ .env file not found{Colors.ENDC}")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    issues = []
    
    # Check DEBUG setting
    if 'DEBUG=True' in content or 'DEBUG=true' in content:
        issues.append("DEBUG is set to True (should be False in production)")
    
    # Check secret key
    if 'SECRET_KEY=django-insecure' in content or 'SECRET_KEY=your-secret-key' in content:
        issues.append("Using default/insecure SECRET_KEY")
    
    # Check allowed hosts
    if 'ALLOWED_HOSTS=*' in content:
        issues.append("ALLOWED_HOSTS is set to * (too permissive)")
    
    # Check database password
    if 'password@localhost' in content or 'PASSWORD=password' in content:
        issues.append("Weak or default database password detected")
    
    if issues:
        print(f"{Colors.YELLOW}Security issues found:{Colors.ENDC}")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print(f"{Colors.GREEN}✓ Environment configuration looks secure{Colors.ENDC}")
        return True


def check_dependencies():
    """Check for known vulnerable dependencies."""
    print(f"\n{Colors.BOLD}Checking dependencies...{Colors.ENDC}")
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'check'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ No known vulnerabilities in dependencies{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.YELLOW}Dependency issues found:{Colors.ENDC}")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"{Colors.RED}Error checking dependencies: {e}{Colors.ENDC}")
        return False


def main():
    print(f"\n{Colors.BOLD}=== Monochrome Security Check ==={Colors.ENDC}\n")
    
    all_good = True
    all_good &= check_env_security()
    all_good &= check_dependencies()
    
    if all_good:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All security checks passed!{Colors.ENDC}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some security issues found{Colors.ENDC}")
        print("Please address these issues before deploying to production")


if __name__ == "__main__":
    main()

