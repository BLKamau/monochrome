#!/usr/bin/env python
"""
Database setup script for PostgreSQL.
Creates database, user, and verifies the setup.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple
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


def check_postgresql_installed() -> bool:
    """Check if PostgreSQL client is installed."""
    print_status("Checking PostgreSQL installation...", "INFO")
    try:
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_status(f"PostgreSQL found: {version} ✓", "SUCCESS")
            return True
    except FileNotFoundError:
        pass
    
    print_status("PostgreSQL client not found!", "ERROR")
    print("  Install PostgreSQL:")
    print("  - Ubuntu/Debian: sudo apt-get install postgresql postgresql-client")
    print("  - MacOS: brew install postgresql")
    print("  - Windows: Download from https://www.postgresql.org/download/windows/")
    return False


def test_connection(conn_params: Dict[str, str]) -> Tuple[bool, Optional[str]]:
    """Test database connection with given parameters."""
    try:
        conn = psycopg2.connect(
            host=conn_params.get('host', 'localhost'),
            port=conn_params.get('port', 5432),
            database=conn_params.get('database', 'postgres'),
            user=conn_params.get('user'),
            password=conn_params.get('password')
        )
        conn.close()
        return True, None
    except psycopg2.Error as e:
        return False, str(e)


def create_database_and_user(admin_conn_params: Dict[str, str], db_config: Dict[str, str]) -> bool:
    """Create database and user with proper permissions."""
    try:
        # Connect to PostgreSQL as admin
        conn = psycopg2.connect(**admin_conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute(
            "SELECT 1 FROM pg_user WHERE usename = %s",
            (db_config['user'],)
        )
        user_exists = cursor.fetchone() is not None
        
        if not user_exists:
            print_status(f"Creating user '{db_config['user']}'...", "INFO")
            cursor.execute(
                sql.SQL("CREATE USER {} WITH PASSWORD %s").format(
                    sql.Identifier(db_config['user'])
                ),
                (db_config['password'],)
            )
            print_status(f"User '{db_config['user']}' created ✓", "SUCCESS")
        else:
            print_status(f"User '{db_config['user']}' already exists", "WARNING")
            # Update password
            cursor.execute(
                sql.SQL("ALTER USER {} WITH PASSWORD %s").format(
                    sql.Identifier(db_config['user'])
                ),
                (db_config['password'],)
            )
            print_status("Password updated ✓", "SUCCESS")
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_config['database'],)
        )
        db_exists = cursor.fetchone() is not None
        
        if not db_exists:
            print_status(f"Creating database '{db_config['database']}'...", "INFO")
            cursor.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(db_config['database']),
                    sql.Identifier(db_config['user'])
                )
            )
            print_status(f"Database '{db_config['database']}' created ✓", "SUCCESS")
        else:
            print_status(f"Database '{db_config['database']}' already exists", "WARNING")
            # Grant permissions
            cursor.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                    sql.Identifier(db_config['database']),
                    sql.Identifier(db_config['user'])
                )
            )
            print_status("Permissions granted ✓", "SUCCESS")
        
        # Grant additional permissions
        cursor.execute(
            sql.SQL("ALTER USER {} CREATEDB").format(
                sql.Identifier(db_config['user'])
            )
        )
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print_status(f"Database setup error: {str(e)}", "ERROR")
        return False


def verify_database_setup(db_config: Dict[str, str]) -> bool:
    """Verify the database setup is correct."""
    print_status("\nVerifying database setup...", "INFO")
    
    # Test connection with created credentials
    success, error = test_connection(db_config)
    if not success:
        print_status(f"Connection test failed: {error}", "ERROR")
        return False
    
    print_status("Connection test passed ✓", "SUCCESS")
    
    try:
        # Connect and check permissions
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Test table creation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _test_permissions (
                id SERIAL PRIMARY KEY,
                test_field VARCHAR(50)
            )
        """)
        
        # Test insert
        cursor.execute(
            "INSERT INTO _test_permissions (test_field) VALUES (%s)",
            ('test',)
        )
        
        # Test select
        cursor.execute("SELECT * FROM _test_permissions")
        cursor.fetchall()
        
        # Clean up
        cursor.execute("DROP TABLE _test_permissions")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print_status("Permission tests passed ✓", "SUCCESS")
        return True
        
    except psycopg2.Error as e:
        print_status(f"Permission test failed: {str(e)}", "ERROR")
        return False


def update_env_file(database_url: str):
    """Update .env file with database URL."""
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        print_status(".env file not found, creating from template...", "WARNING")
        env_example = Path(__file__).parent.parent / '.env.example'
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_path)
        else:
            # Create basic .env file
            with open(env_path, 'w') as f:
                f.write("# Monochrome Environment Configuration\n")
                f.write("DJANGO_SECRET_KEY=your-secret-key-here\n")
                f.write("DEBUG=True\n")
                f.write("ALLOWED_HOSTS=localhost,127.0.0.1\n")
    
    # Read current content
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Update DATABASE_URL
    lines = content.split('\n')
    updated = False
    new_lines = []
    
    for line in lines:
        if line.startswith('DATABASE_URL='):
            new_lines.append(f'DATABASE_URL={database_url}')
            updated = True
        elif line.startswith('USE_SQLITE='):
            new_lines.append('USE_SQLITE=False')
        else:
            new_lines.append(line)
    
    if not updated:
        # Add DATABASE_URL if not present
        new_lines.append(f'\n# Database Configuration')
        new_lines.append('USE_SQLITE=False')
        new_lines.append(f'DATABASE_URL={database_url}')
    
    # Write back
    with open(env_path, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print_status(".env file updated ✓", "SUCCESS")


def main():
    """Main setup function."""
    print(f"\n{Colors.BOLD}=== Monochrome PostgreSQL Database Setup ==={Colors.ENDC}\n")
    
    # Check PostgreSQL installation
    if not check_postgresql_installed():
        sys.exit(1)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get database configuration
    database_url = os.getenv('DATABASE_URL', '')
    if database_url and database_url != 'postgresql://user:password@localhost:5432/monochrome_db':
        db_config = parse_database_url(database_url)
        print_status("Found DATABASE_URL in .env file", "INFO")
        
        # Ask if user wants to use existing config
        response = input(f"\nUse existing configuration for database '{db_config['database']}'? (Y/n): ").lower()
        if response == 'n':
            db_config = {}
    else:
        db_config = {}
    
    # Get database configuration from user if needed
    if not db_config:
        print_status("\nDatabase Configuration", "INFO")
        db_config = {
            'host': input("PostgreSQL host [localhost]: ").strip() or 'localhost',
            'port': input("PostgreSQL port [5432]: ").strip() or '5432',
            'database': input("Database name [monochrome_db]: ").strip() or 'monochrome_db',
            'user': input("Database user [monochrome_user]: ").strip() or 'monochrome_user',
            'password': getpass.getpass("Database password: ").strip()
        }
        
        if not db_config['password']:
            print_status("Password cannot be empty!", "ERROR")
            sys.exit(1)
    
    # Get PostgreSQL admin credentials
    print_status("\nPostgreSQL Admin Credentials (for creating database/user)", "INFO")
    print("Leave empty to use default 'postgres' user")
    
    admin_user = input("Admin username [postgres]: ").strip() or 'postgres'
    admin_password = getpass.getpass("Admin password: ").strip()
    
    admin_conn_params = {
        'host': db_config['host'],
        'port': db_config['port'],
        'database': 'postgres',
        'user': admin_user,
        'password': admin_password
    }
    
    # Test admin connection
    print_status("\nTesting admin connection...", "INFO")
    success, error = test_connection(admin_conn_params)
    if not success:
        print_status(f"Admin connection failed: {error}", "ERROR")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running")
        print("2. Check admin credentials")
        print("3. Check pg_hba.conf allows connections")
        sys.exit(1)
    
    print_status("Admin connection successful ✓", "SUCCESS")
    
    # Create database and user
    if not create_database_and_user(admin_conn_params, db_config):
        sys.exit(1)
    
    # Verify setup
    if not verify_database_setup(db_config):
        print_status("\nDatabase setup verification failed!", "ERROR")
        print("The database and user were created but permissions may be incorrect.")
        sys.exit(1)
    
    # Build DATABASE_URL
    database_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    
    # Update .env file
    response = input(f"\n{Colors.BLUE}Update .env file with database configuration? (Y/n): {Colors.ENDC}").lower()
    if response != 'n':
        update_env_file(database_url)
    
    # Show summary
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Database setup completed successfully!{Colors.ENDC}")
    print(f"\n{Colors.BOLD}Database Details:{Colors.ENDC}")
    print(f"  Host: {db_config['host']}")
    print(f"  Port: {db_config['port']}")
    print(f"  Database: {db_config['database']}")
    print(f"  User: {db_config['user']}")
    print(f"\n{Colors.BOLD}Connection String:{Colors.ENDC}")
    print(f"  {database_url}")
    
    # Next steps
    print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
    print("1. Run migrations: python manage.py migrate")
    print("2. Create superuser: python manage.py createsuperuser")
    print("3. Start server: python scripts/dev_server.py")
    
    # Ask to run migrations
    response = input(f"\n{Colors.BLUE}Run migrations now? (Y/n): {Colors.ENDC}").lower()
    if response != 'n':
        print_status("\nRunning migrations...", "INFO")
        os.environ['DATABASE_URL'] = database_url
        subprocess.run([sys.executable, 'manage.py', 'migrate'])
        print_status("Migrations completed ✓", "SUCCESS")


if __name__ == "__main__":
    main()