#!/usr/bin/env python
"""
Development server script with comprehensive checks.
Ensures all prerequisites are met before starting the Django development server.
"""

import os
import sys
import socket
import subprocess
import time
import signal
from pathlib import Path
from typing import Tuple, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_status(message: str, status: str = "INFO"):
    """Print colored status messages."""
    colors = {
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "INFO": Colors.BLUE
    }
    color = colors.get(status, Colors.BLUE)
    print(f"{color}[{status}]{Colors.ENDC} {message}")


def check_python_version():
    """Check if Python version meets requirements."""
    print_status("Checking Python version...", "INFO")
    if sys.version_info < (3, 10):
        print_status(f"Python 3.10+ required. Current: {sys.version}", "ERROR")
        return False
    print_status(f"Python {sys.version.split()[0]} ✓", "SUCCESS")
    return True


def check_virtual_env():
    """Check if running in a virtual environment."""
    print_status("Checking virtual environment...", "INFO")
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_status("Not running in a virtual environment!", "WARNING")
        print("  Recommendation: Create and activate a virtual environment:")
        print("  python -m venv venv")
        print("  source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        return False
    print_status("Virtual environment active ✓", "SUCCESS")
    return True


def check_dependencies():
    """Check if all required packages are installed."""
    print_status("Checking dependencies...", "INFO")
    try:
        import django
        import rest_framework
        import jwt
        import dotenv
        print_status("Core dependencies installed ✓", "SUCCESS")
        return True
    except ImportError as e:
        print_status(f"Missing dependency: {e.name}", "ERROR")
        print("  Run: pip install -r requirements.txt")
        return False


def check_env_file():
    """Check if .env file exists and has required variables."""
    print_status("Checking environment configuration...", "INFO")
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        print_status(".env file not found!", "ERROR")
        print("  Run: cp .env.example .env")
        print("  Then edit .env with your configuration")
        return False
    
    # Load and check essential variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'DJANGO_SECRET_KEY',
        'DEBUG',
        'ALLOWED_HOSTS'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print_status(f"Missing environment variables: {', '.join(missing_vars)}", "ERROR")
        return False
    
    print_status("Environment configuration ✓", "SUCCESS")
    return True


def check_database_connection():
    """Check database connectivity."""
    print_status("Checking database connection...", "INFO")
    
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monochrome_backend.settings')
        import django
        django.setup()
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        print_status("Database connection successful ✓", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"Database connection failed: {str(e)}", "ERROR")
        print("  Check your database configuration in .env")
        print("  For PostgreSQL, ensure the database server is running")
        print("  You can run: python scripts/setup_database.py")
        return False


def check_migrations():
    """Check if there are pending migrations."""
    print_status("Checking migrations...", "INFO")
    
    try:
        result = subprocess.run(
            [sys.executable, 'manage.py', 'showmigrations', '--plan'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        output = result.stdout
        if '[ ]' in output:
            print_status("Pending migrations detected!", "WARNING")
            print("  Run: python manage.py migrate")
            
            # Ask if user wants to run migrations
            response = input("  Run migrations now? (y/N): ").lower()
            if response == 'y':
                print_status("Running migrations...", "INFO")
                subprocess.run([sys.executable, 'manage.py', 'migrate'])
                print_status("Migrations completed ✓", "SUCCESS")
            else:
                return False
        else:
            print_status("All migrations applied ✓", "SUCCESS")
        
        return True
    except Exception as e:
        print_status(f"Error checking migrations: {str(e)}", "ERROR")
        return False


def check_static_files():
    """Check if static files are collected."""
    print_status("Checking static files...", "INFO")
    
    static_root = Path(__file__).parent.parent / 'staticfiles'
    if not static_root.exists() or not any(static_root.iterdir()):
        print_status("Static files not collected", "WARNING")
        print("  Run: python manage.py collectstatic --noinput")
        
        response = input("  Collect static files now? (y/N): ").lower()
        if response == 'y':
            subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'])
            print_status("Static files collected ✓", "SUCCESS")
    else:
        print_status("Static files present ✓", "SUCCESS")
    
    return True


def check_port_availability(host: str = '127.0.0.1', port: int = 8000) -> Tuple[bool, Optional[int]]:
    """Check if the specified port is available."""
    print_status(f"Checking port {port} availability...", "INFO")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    
    for attempt_port in range(port, port + 10):
        try:
            result = sock.connect_ex((host, attempt_port))
            if result != 0:
                sock.close()
                if attempt_port != port:
                    print_status(f"Port {port} busy, using {attempt_port} instead", "WARNING")
                else:
                    print_status(f"Port {attempt_port} available ✓", "SUCCESS")
                return True, attempt_port
        except Exception:
            pass
    
    sock.close()
    print_status(f"No available ports found in range {port}-{port+9}", "ERROR")
    return False, None


def create_superuser_if_needed():
    """Check if superuser exists and offer to create one."""
    print_status("Checking for superuser account...", "INFO")
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(is_superuser=True).exists():
            print_status("No superuser account found!", "WARNING")
            response = input("  Create superuser now? (y/N): ").lower()
            if response == 'y':
                subprocess.run([sys.executable, 'manage.py', 'createsuperuser'])
                print_status("Superuser created ✓", "SUCCESS")
        else:
            print_status("Superuser account exists ✓", "SUCCESS")
    except Exception as e:
        print_status(f"Error checking superuser: {str(e)}", "WARNING")


def run_server(host: str = '127.0.0.1', port: int = 8000):
    """Run the Django development server."""
    print_status(f"\n{Colors.BOLD}Starting Monochrome Development Server...{Colors.ENDC}", "INFO")
    print(f"\n{Colors.GREEN}Server running at: http://{host}:{port}/{Colors.ENDC}")
    print(f"{Colors.GREEN}Admin interface: http://{host}:{port}/admin/{Colors.ENDC}")
    print(f"{Colors.GREEN}API documentation: http://{host}:{port}/api/docs/{Colors.ENDC}")
    print(f"\n{Colors.YELLOW}Press Ctrl+C to stop the server{Colors.ENDC}\n")
    
    try:
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            print(f"\n{Colors.YELLOW}Shutting down server...{Colors.ENDC}")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Run the server
        subprocess.run([
            sys.executable, 'manage.py', 'runserver', 
            f'{host}:{port}', '--noreload'
        ])
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Server stopped{Colors.ENDC}")
    except Exception as e:
        print_status(f"Server error: {str(e)}", "ERROR")


def main():
    """Main function to run all checks and start server."""
    print(f"\n{Colors.BOLD}=== Monochrome Development Server Pre-flight Checks ==={Colors.ENDC}\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_env),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Database Connection", check_database_connection),
        ("Migrations", check_migrations),
        ("Static Files", check_static_files),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        if not check_func():
            all_passed = False
            if check_name in ["Python Version", "Dependencies", "Environment File", "Database Connection"]:
                print_status(f"\n{check_name} check failed. Please fix before continuing.", "ERROR")
                sys.exit(1)
        print()  # Empty line between checks
    
    # Check for superuser
    create_superuser_if_needed()
    print()
    
    # Check port availability
    port_available, available_port = check_port_availability()
    if not port_available:
        print_status("No available ports found!", "ERROR")
        sys.exit(1)
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All checks passed!{Colors.ENDC}")
    
    # Ask to run server
    response = input(f"\n{Colors.BLUE}Start development server? (Y/n): {Colors.ENDC}").lower()
    if response != 'n':
        run_server(port=available_port)
    else:
        print_status("Server start cancelled", "INFO")


if __name__ == "__main__":
    main()