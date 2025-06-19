#!/usr/bin/env python
"""
Database reset script for development.
WARNING: This will delete all data in the database!
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import subprocess
from pathlib import Path
from typing import Dict, Optional
import getpass
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes
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


def parse_database_url(database_url: str) -> Dict[str, str]:
    """Parse DATABASE_URL into components."""
    if not database_url:
        return {}
    
    parsed = urlparse(database_url)
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/') if parsed.path else '',
        'user': parsed.username or '',
        'password': parsed.password or ''
    }


def confirm_reset(db_name: str) -> bool:
    """Get user confirmation for database reset."""
    print(f"\n{Colors.RED}{Colors.BOLD}⚠️  WARNING: DESTRUCTIVE OPERATION ⚠️{Colors.ENDC}")
    print(f"\nThis will completely reset the database '{db_name}'")
    print("All data will be permanently deleted!")
    
    # First confirmation
    response = input(f"\n{Colors.YELLOW}Are you sure you want to continue? (yes/N): {Colors.ENDC}").lower()
    if response != 'yes':
        print_status("Reset cancelled", "INFO")
        return False
    
    # Second confirmation with database name
    db_confirm = input(f"\n{Colors.YELLOW}Type the database name '{db_name}' to confirm: {Colors.ENDC}")
    if db_confirm != db_name:
        print_status("Database name doesn't match. Reset cancelled", "INFO")
        return False
    
    # Final confirmation
    final = input(f"\n{Colors.RED}Final confirmation - type 'RESET' to proceed: {Colors.ENDC}")
    if final != 'RESET':
        print_status("Reset cancelled", "INFO")
        return False
    
    return True


def backup_database(db_config: Dict[str, str]) -> Optional[str]:
    """Create a backup of the database before reset."""
    print_status("\nCreating database backup...", "INFO")
    
    backup_dir = Path(__file__).parent.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"monochrome_backup_{timestamp}.sql"
    
    try:
        # Build pg_dump command
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['password']
        
        cmd = [
            'pg_dump',
            '-h', str(db_config['host']),
            '-p', str(db_config['port']),
            '-U', db_config['user'],
            '-d', db_config['database'],
            '-f', str(backup_file),
            '--verbose',
            '--clean',
            '--if-exists'
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            file_size = backup_file.stat().st_size / 1024 / 1024  # MB
            print_status(f"Backup created: {backup_file} ({file_size:.2f} MB) ✓", "SUCCESS")
            return str(backup_file)
        else:
            print_status(f"Backup failed: {result.stderr}", "ERROR")
            return None
            
    except FileNotFoundError:
        print_status("pg_dump not found. Skipping backup.", "WARNING")
        print("  Install PostgreSQL client tools to enable backups")
        return None
    except Exception as e:
        print_status(f"Backup error: {str(e)}", "ERROR")
        return None


def reset_using_django(db_config: Dict[str, str]) -> bool:
    """Reset database using Django management commands."""
    print_status("\nResetting database using Django...", "INFO")
    
    try:
        # Set database URL
        database_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        os.environ['DATABASE_URL'] = database_url
        os.environ['USE_SQLITE'] = 'False'
        
        # Remove all migration files (except __init__.py)
        print_status("Cleaning migration files...", "INFO")
        for app in ['users', 'common']:
            migrations_dir = Path(__file__).parent.parent / app / 'migrations'
            if migrations_dir.exists():
                for file in migrations_dir.glob('*.py'):
                    if file.name != '__init__.py':
                        file.unlink()
                for file in migrations_dir.glob('*.pyc'):
                    file.unlink()
        
        # Flush database
        print_status("Flushing database...", "INFO")
        result = subprocess.run(
            [sys.executable, 'manage.py', 'flush', '--noinput'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_status(f"Flush failed: {result.stderr}", "ERROR")
            return False
        
        # Create new migrations
        print_status("Creating fresh migrations...", "INFO")
        
        # Make migrations for each app
        for app in ['users', 'common']:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'makemigrations', app],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print_status(f"Migration creation failed for {app}: {result.stderr}", "ERROR")
                return False
        
        # Apply migrations
        print_status("Applying migrations...", "INFO")
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_status(f"Migration failed: {result.stderr}", "ERROR")
            return False
        
        print_status("Database reset completed ✓", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"Reset error: {str(e)}", "ERROR")
        return False


def reset_using_sql(db_config: Dict[str, str], admin_conn_params: Dict[str, str]) -> bool:
    """Reset database by dropping and recreating it."""
    print_status("\nResetting database using SQL...", "INFO")
    
    try:
        # Connect as admin to postgres database
        conn = psycopg2.connect(**admin_conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Terminate existing connections
        print_status("Terminating existing connections...", "INFO")
        cursor.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (db_config['database'],)
        )
        
        # Drop database
        print_status(f"Dropping database '{db_config['database']}'...", "INFO")
        cursor.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(db_config['database'])
            )
        )
        
        # Recreate database
        print_status(f"Creating database '{db_config['database']}'...", "INFO")
        cursor.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(db_config['database']),
                sql.Identifier(db_config['user'])
            )
        )
        
        # Grant permissions
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                sql.Identifier(db_config['database']),
                sql.Identifier(db_config['user'])
            )
        )
        
        cursor.close()
        conn.close()
        
        print_status("Database recreated ✓", "SUCCESS")
        
        # Run migrations
        print_status("Running migrations...", "INFO")
        database_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        os.environ['DATABASE_URL'] = database_url
        os.environ['USE_SQLITE'] = 'False'
        
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_status(f"Migration failed: {result.stderr}", "ERROR")
            return False
        
        print_status("Migrations completed ✓", "SUCCESS")
        return True
        
    except psycopg2.Error as e:
        print_status(f"SQL reset error: {str(e)}", "ERROR")
        return False


def create_default_superuser():
    """Offer to create a default superuser."""
    print_status("\nSuperuser Setup", "INFO")
    response = input("Create a superuser account? (Y/n): ").lower()
    
    if response != 'n':
        subprocess.run([sys.executable, 'manage.py', 'createsuperuser'])


def main():
    """Main reset function."""
    print(f"\n{Colors.BOLD}=== Monochrome Database Reset Tool ==={Colors.ENDC}\n")
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get database configuration
    database_url = os.getenv('DATABASE_URL', '')
    if not database_url:
        print_status("DATABASE_URL not found in .env file!", "ERROR")
        print("Run: python scripts/setup_database.py")
        sys.exit(1)
    
    db_config = parse_database_url(database_url)
    
    # Show current database
    print(f"{Colors.BOLD}Current Database:{Colors.ENDC}")
    print(f"  Host: {db_config['host']}")
    print(f"  Port: {db_config['port']}")
    print(f"  Database: {db_config['database']}")
    print(f"  User: {db_config['user']}")
    
    # Get confirmation
    if not confirm_reset(db_config['database']):
        sys.exit(0)
    
    # Offer backup
    backup_file = None
    response = input(f"\n{Colors.BLUE}Create backup before reset? (Y/n): {Colors.ENDC}").lower()
    if response != 'n':
        backup_file = backup_database(db_config)
    
    # Choose reset method
    print(f"\n{Colors.BOLD}Reset Methods:{Colors.ENDC}")
    print("1. Django flush (keeps structure, deletes data)")
    print("2. Full reset (drop and recreate database)")
    
    method = input(f"\n{Colors.BLUE}Choose method [1]: {Colors.ENDC}").strip() or '1'
    
    if method == '1':
        # Django flush method
        success = reset_using_django(db_config)
    else:
        # SQL drop/create method
        print_status("\nPostgreSQL admin credentials required", "INFO")
        admin_user = input("Admin username [postgres]: ").strip() or 'postgres'
        admin_password = getpass.getpass("Admin password: ").strip()
        
        admin_conn_params = {
            'host': db_config['host'],
            'port': db_config['port'],
            'database': 'postgres',
            'user': admin_user,
            'password': admin_password
        }
        
        success = reset_using_sql(db_config, admin_conn_params)
    
    if success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Database reset completed successfully!{Colors.ENDC}")
        
        if backup_file:
            print(f"\n{Colors.BOLD}Backup saved to:{Colors.ENDC}")
            print(f"  {backup_file}")
            print(f"\n{Colors.BOLD}To restore from backup:{Colors.ENDC}")
            print(f"  psql -h {db_config['host']} -p {db_config['port']} -U {db_config['user']} -d {db_config['database']} < {backup_file}")
        
        # Offer to create superuser
        create_default_superuser()
        
        # Offer to populate test data
        response = input(f"\n{Colors.BLUE}Populate with test data? (y/N): {Colors.ENDC}").lower()
        if response == 'y':
            print_status("Running test data script...", "INFO")
            subprocess.run([sys.executable, 'scripts/setup_test_data.py'])
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Database reset failed!{Colors.ENDC}")
        if backup_file:
            print(f"\nBackup available at: {backup_file}")


if __name__ == "__main__":
    main()