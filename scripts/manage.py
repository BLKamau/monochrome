#!/usr/bin/env python
"""
Monochrome Script Manager
Central management interface for all development scripts.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# Script definitions
SCRIPTS = {
    'server': {
        'name': 'Development Server',
        'script': 'dev_server.py',
        'description': 'Start development server with pre-flight checks',
        'category': 'Development'
    },
    'setup-db': {
        'name': 'Setup Database',
        'script': 'setup_database.py',
        'description': 'Configure PostgreSQL database for Monochrome',
        'category': 'Database'
    },
    'reset-db': {
        'name': 'Reset Database',
        'script': 'reset_db.py',
        'description': 'Reset database (WARNING: Deletes all data!)',
        'category': 'Database'
    },
    'test-data': {
        'name': 'Setup Test Data',
        'script': 'setup_test_data.py',
        'description': 'Populate database with test/synthetic data',
        'category': 'Database'
    },
    'test': {
        'name': 'Run Tests',
        'script': 'run_tests.py',
        'description': 'Run test suite with coverage reporting',
        'category': 'Testing'
    },
    'security': {
        'name': 'Security Check',
        'script': 'check_security.py',
        'description': 'Check for security issues in configuration',
        'category': 'Security'
    },
    'docs': {
        'name': 'Export API Docs',
        'script': 'export_api_docs.py',
        'description': 'Export API documentation to JSON/Markdown',
        'category': 'Documentation'
    },
    'monitor': {
        'name': 'Performance Monitor',
        'script': 'monitor_performance.py',
        'description': 'Check system and application performance',
        'category': 'Monitoring'
    }
}

# Quick commands
QUICK_COMMANDS = {
    'migrate': {
        'name': 'Run Migrations',
        'command': [sys.executable, 'manage.py', 'migrate'],
        'description': 'Apply database migrations'
    },
    'makemigrations': {
        'name': 'Make Migrations',
        'command': [sys.executable, 'manage.py', 'makemigrations'],
        'description': 'Create new migrations'
    },
    'shell': {
        'name': 'Django Shell',
        'command': [sys.executable, 'manage.py', 'shell'],
        'description': 'Open Django interactive shell'
    },
    'dbshell': {
        'name': 'Database Shell',
        'command': [sys.executable, 'manage.py', 'dbshell'],
        'description': 'Open database shell'
    },
    'createsuperuser': {
        'name': 'Create Superuser',
        'command': [sys.executable, 'manage.py', 'createsuperuser'],
        'description': 'Create admin superuser account'
    },
    'collectstatic': {
        'name': 'Collect Static',
        'command': [sys.executable, 'manage.py', 'collectstatic', '--noinput'],
        'description': 'Collect static files'
    }
}


def print_header():
    """Print the header banner."""
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════╗
║       {Colors.BOLD}Monochrome Script Manager{Colors.ENDC}{Colors.CYAN}         ║
║    Secure Authentication Backend         ║
╚══════════════════════════════════════════╝{Colors.ENDC}
""")


def print_menu():
    """Print the main menu."""
    # Group scripts by category
    categories = {}
    for key, script in SCRIPTS.items():
        category = script['category']
        if category not in categories:
            categories[category] = []
        categories[category].append((key, script))
    
    print(f"{Colors.BOLD}Available Scripts:{Colors.ENDC}\n")
    
    # Print scripts by category
    for category, scripts in categories.items():
        print(f"{Colors.BLUE}{Colors.BOLD}{category}:{Colors.ENDC}")
        for key, script in scripts:
            print(f"  {Colors.GREEN}{key:<12}{Colors.ENDC} - {script['description']}")
        print()
    
    # Print quick commands
    print(f"{Colors.BLUE}{Colors.BOLD}Quick Commands:{Colors.ENDC}")
    for key, cmd in QUICK_COMMANDS.items():
        print(f"  {Colors.MAGENTA}{key:<12}{Colors.ENDC} - {cmd['description']}")
    
    print(f"\n{Colors.BLUE}{Colors.BOLD}Other Options:{Colors.ENDC}")
    print(f"  {Colors.YELLOW}all{Colors.ENDC}         - Run all setup scripts in sequence")
    print(f"  {Colors.YELLOW}status{Colors.ENDC}      - Check system status")
    print(f"  {Colors.YELLOW}help{Colors.ENDC}        - Show this menu")
    print(f"  {Colors.YELLOW}exit{Colors.ENDC}        - Exit script manager")


def run_script(script_name: str) -> bool:
    """Run a script by name."""
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"{Colors.RED}Error: Script {script_name} not found!{Colors.ENDC}")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(script_path)])
        return result.returncode == 0
    except Exception as e:
        print(f"{Colors.RED}Error running script: {str(e)}{Colors.ENDC}")
        return False


def run_command(command: List[str]) -> bool:
    """Run a command."""
    try:
        result = subprocess.run(command)
        return result.returncode == 0
    except Exception as e:
        print(f"{Colors.RED}Error running command: {str(e)}{Colors.ENDC}")
        return False


def check_status():
    """Check the current system status."""
    print(f"\n{Colors.BOLD}=== System Status ==={Colors.ENDC}\n")
    
    # Check Python version
    print(f"Python: {sys.version.split()[0]}")
    
    # Check Django
    try:
        import django
        print(f"Django: {django.__version__}")
    except ImportError:
        print(f"{Colors.RED}Django: Not installed{Colors.ENDC}")
    
    # Check database
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print(f"{Colors.GREEN}Database: Connected{Colors.ENDC}")
    except Exception:
        print(f"{Colors.RED}Database: Not connected{Colors.ENDC}")
    
    # Check .env file
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        print(f"{Colors.GREEN}.env file: Found{Colors.ENDC}")
    else:
        print(f"{Colors.RED}.env file: Not found{Colors.ENDC}")
    
    # Check migrations
    try:
        result = subprocess.run(
            [sys.executable, 'manage.py', 'showmigrations', '--plan'],
            capture_output=True,
            text=True
        )
        if '[ ]' in result.stdout:
            print(f"{Colors.YELLOW}Migrations: Pending{Colors.ENDC}")
        else:
            print(f"{Colors.GREEN}Migrations: Up to date{Colors.ENDC}")
    except Exception:
        print(f"{Colors.RED}Migrations: Unable to check{Colors.ENDC}")


def run_all_setup():
    """Run all setup scripts in sequence."""
    print(f"\n{Colors.BOLD}Running complete setup...{Colors.ENDC}\n")
    
    setup_sequence = [
        ('setup-db', 'Setting up database...'),
        ('migrate', 'Running migrations...'),
        ('createsuperuser', 'Creating superuser...'),
        ('test-data', 'Creating test data...'),
        ('collectstatic', 'Collecting static files...'),
    ]
    
    for key, message in setup_sequence:
        print(f"\n{Colors.BLUE}{message}{Colors.ENDC}")
        
        if key in SCRIPTS:
            success = run_script(SCRIPTS[key]['script'])
        elif key in QUICK_COMMANDS:
            success = run_command(QUICK_COMMANDS[key]['command'])
        else:
            success = False
        
        if not success:
            print(f"{Colors.RED}Setup failed at: {key}{Colors.ENDC}")
            return False
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Complete setup finished successfully!{Colors.ENDC}")
    return True


def main():
    """Main script manager loop."""
    print_header()
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent)
    
    while True:
        print_menu()
        
        try:
            choice = input(f"\n{Colors.CYAN}Enter command: {Colors.ENDC}").strip().lower()
            
            if choice == 'exit':
                print(f"{Colors.YELLOW}Goodbye!{Colors.ENDC}")
                break
            
            elif choice == 'help':
                continue
            
            elif choice == 'status':
                check_status()
            
            elif choice == 'all':
                run_all_setup()
            
            elif choice in SCRIPTS:
                script = SCRIPTS[choice]
                print(f"\n{Colors.BLUE}Running {script['name']}...{Colors.ENDC}\n")
                run_script(script['script'])
            
            elif choice in QUICK_COMMANDS:
                cmd = QUICK_COMMANDS[choice]
                print(f"\n{Colors.BLUE}Running {cmd['name']}...{Colors.ENDC}\n")
                run_command(cmd['command'])
            
            else:
                print(f"{Colors.RED}Invalid command. Type 'help' for options.{Colors.ENDC}")
            
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            print("\n" + "="*50 + "\n")
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted. Type 'exit' to quit.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error: {str(e)}{Colors.ENDC}")


if __name__ == "__main__":
    main()