#!/usr/bin/env python
"""
Script to populate database with test/synthetic data for development.
Creates users with different roles, MFA setups, and login histories.
"""

import os
import sys
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import pyotp
from faker import Faker

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monochrome_backend.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from users.models import UserType, TOTPDevice, BackupCode, LoginHistory
from users.services import MFAService

# Initialize Faker
fake = Faker()

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


User = get_user_model()

# Test user configurations
TEST_USERS = [
    # Admin users
    {
        'username': 'admin',
        'email': 'admin@monochrome.test',
        'password': 'Admin123!@#',
        'user_type': UserType.ADMIN,
        'first_name': 'Admin',
        'last_name': 'User',
        'is_superuser': True,
        'is_staff': True,
        'has_mfa': True,
        'is_active': True,
    },
    {
        'username': 'admin2',
        'email': 'admin2@monochrome.test',
        'password': 'Admin123!@#',
        'user_type': UserType.ADMIN,
        'first_name': 'Secondary',
        'last_name': 'Admin',
        'has_mfa': True,
        'is_active': True,
    },
    # Staff users
    {
        'username': 'staff1',
        'email': 'staff1@monochrome.test',
        'password': 'Staff123!@#',
        'user_type': UserType.STAFF,
        'first_name': 'John',
        'last_name': 'Staff',
        'has_mfa': True,
        'is_active': True,
    },
    {
        'username': 'staff2',
        'email': 'staff2@monochrome.test',
        'password': 'Staff123!@#',
        'user_type': UserType.STAFF,
        'first_name': 'Jane',
        'last_name': 'Staff',
        'has_mfa': False,  # MFA not set up
        'is_active': True,
    },
    # Regular users
    {
        'username': 'user1',
        'email': 'user1@monochrome.test',
        'password': 'User123!@#',
        'user_type': UserType.USER,
        'first_name': 'Alice',
        'last_name': 'Johnson',
        'has_mfa': True,
        'is_active': True,
    },
    {
        'username': 'user2',
        'email': 'user2@monochrome.test',
        'password': 'User123!@#',
        'user_type': UserType.USER,
        'first_name': 'Bob',
        'last_name': 'Smith',
        'has_mfa': True,
        'is_active': True,
    },
    {
        'username': 'user3',
        'email': 'user3@monochrome.test',
        'password': 'User123!@#',
        'user_type': UserType.USER,
        'first_name': 'Charlie',
        'last_name': 'Brown',
        'has_mfa': False,
        'is_active': True,
    },
    # Special test cases
    {
        'username': 'unverified',
        'email': 'unverified@monochrome.test',
        'password': 'User123!@#',
        'user_type': UserType.USER,
        'first_name': 'Unverified',
        'last_name': 'User',
        'has_mfa': False,
        'is_active': False,  # Email not verified
    },
    {
        'username': 'locked',
        'email': 'locked@monochrome.test',
        'password': 'User123!@#',
        'user_type': UserType.USER,
        'first_name': 'Locked',
        'last_name': 'Account',
        'has_mfa': True,
        'is_active': True,
        'is_locked': True,  # Account locked
    },
]


def generate_random_users(count: int = 10) -> List[Dict[str, Any]]:
    """Generate random user data."""
    random_users = []
    
    for i in range(count):
        username = fake.user_name() + str(random.randint(100, 999))
        random_users.append({
            'username': username,
            'email': f"{username}@monochrome.test",
            'password': 'User123!@#',
            'user_type': random.choice([UserType.USER, UserType.USER, UserType.STAFF]),  # More regular users
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'has_mfa': random.choice([True, True, False]),  # 66% have MFA
            'is_active': random.choice([True] * 9 + [False]),  # 90% verified
            'phone_number': fake.phone_number() if random.random() > 0.5 else None,
        })
    
    return random_users


def create_user(user_data: Dict[str, Any]) -> User:
    """Create a user with given data."""
    # Extract special flags
    is_locked = user_data.pop('is_locked', False)
    has_mfa = user_data.pop('has_mfa', False)
    
    # Create user
    password = user_data.pop('password')
    user = User.objects.create_user(password=password, **user_data)
    
    # Handle locked account
    if is_locked:
        user.failed_login_attempts = 5
        user.locked_until = timezone.now() + timedelta(hours=1)
        user.save()
    
    # Set up MFA if needed
    if has_mfa and user.is_active:
        setup_mfa_for_user(user)
    
    return user


def setup_mfa_for_user(user: User):
    """Set up MFA for a user."""
    # Generate TOTP device
    secret = pyotp.random_base32()
    device = TOTPDevice.objects.create(
        user=user,
        name=f"{user.username}'s Phone",
        key=secret,
        verified=True
    )
    device.last_used_at = timezone.now() - timedelta(days=random.randint(0, 30))
    device.save()
    
    # Enable MFA for user
    user.is_mfa_enabled = True
    user.is_mfa_verified = True
    user.save()
    
    # Generate backup codes
    MFAService.generate_backup_codes(user, count=5)
    
    # Use some backup codes randomly
    if random.random() > 0.7:
        codes = user.backup_codes.all()[:random.randint(1, 2)]
        for code in codes:
            code.mark_as_used()


def create_login_history(user: User, count: int = 20):
    """Create login history for a user."""
    login_entries = []
    
    # Generate IP addresses
    ip_addresses = [
        fake.ipv4() for _ in range(5)
    ]
    
    # Common user agents
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)',
        'Mozilla/5.0 (Android 11; Mobile; rv:89.0) Gecko/89.0 Firefox/89.0',
    ]
    
    for i in range(count):
        # Time spread over last 30 days
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        login_time = timezone.now() - timedelta(days=days_ago, hours=hours_ago)
        
        # 90% success rate
        success = random.random() > 0.1
        
        login_entry = LoginHistory(
            user=user,
            ip_address=random.choice(ip_addresses),
            user_agent=random.choice(user_agents),
            login_time=login_time,
            success=success,
            failure_reason='' if success else random.choice([
                'Invalid credentials',
                'Account locked',
                'MFA token invalid',
                'Password expired'
            ]),
            location=fake.city() + ', ' + fake.country()
        )
        login_entries.append(login_entry)
    
    LoginHistory.objects.bulk_create(login_entries)


def create_test_data():
    """Create all test data."""
    print_status("Creating test users...", "INFO")
    
    # Combine predefined and random users
    all_users = TEST_USERS + generate_random_users(20)
    
    created_users = []
    with transaction.atomic():
        for user_data in all_users:
            try:
                user = create_user(user_data.copy())
                created_users.append(user)
                print(f"  ✓ Created user: {user.username} ({user.user_type})")
            except Exception as e:
                print_status(f"  ✗ Failed to create {user_data['username']}: {str(e)}", "ERROR")
    
    print_status(f"Created {len(created_users)} users", "SUCCESS")
    
    # Create login history
    print_status("\nCreating login history...", "INFO")
    for user in created_users:
        if user.is_active:  # Only for active users
            create_login_history(user, count=random.randint(5, 30))
    
    print_status("Login history created", "SUCCESS")
    
    return created_users


def print_test_credentials(users: List[User]):
    """Print test user credentials."""
    print(f"\n{Colors.BOLD}=== Test User Credentials ==={Colors.ENDC}")
    
    # Group by user type
    admins = [u for u in users if u.user_type == UserType.ADMIN]
    staff = [u for u in users if u.user_type == UserType.STAFF]
    regular = [u for u in users if u.user_type == UserType.USER]
    
    def print_user_group(title: str, users: List[User], password: str):
        print(f"\n{Colors.BOLD}{title}:{Colors.ENDC}")
        for user in users[:5]:  # Show first 5 of each type
            mfa_status = "✓" if user.is_mfa_enabled else "✗"
            active_status = "✓" if user.is_active else "✗"
            locked_status = " [LOCKED]" if user.is_account_locked else ""
            print(f"  Username: {user.username:<15} Password: {password:<15} MFA: {mfa_status} Active: {active_status}{locked_status}")
    
    print_user_group("Admin Users", admins, "Admin123!@#")
    print_user_group("Staff Users", staff, "Staff123!@#")
    print_user_group("Regular Users", regular, "User123!@#")
    
    # Special accounts
    print(f"\n{Colors.BOLD}Special Test Accounts:{Colors.ENDC}")
    print(f"  Unverified: username: unverified, password: User123!@# (email not verified)")
    print(f"  Locked:     username: locked, password: User123!@# (too many failed attempts)")
    
    # Statistics
    print(f"\n{Colors.BOLD}Statistics:{Colors.ENDC}")
    total = len(users)
    print(f"  Total users: {total}")
    print(f"  Admins: {len(admins)}")
    print(f"  Staff: {len(staff)}")
    print(f"  Regular: {len(regular)}")
    print(f"  With MFA: {len([u for u in users if u.is_mfa_enabled])}")
    print(f"  Verified: {len([u for u in users if u.is_active])}")


def main():
    """Main function."""
    print(f"\n{Colors.BOLD}=== Monochrome Test Data Setup ==={Colors.ENDC}\n")
    
    # Check if data already exists
    existing_users = User.objects.filter(email__endswith='@monochrome.test').count()
    if existing_users > 0:
        print_status(f"Found {existing_users} existing test users", "WARNING")
        response = input(f"\n{Colors.YELLOW}Delete existing test data? (y/N): {Colors.ENDC}").lower()
        
        if response == 'y':
            print_status("Deleting existing test data...", "INFO")
            User.objects.filter(email__endswith='@monochrome.test').delete()
            print_status("Existing test data deleted", "SUCCESS")
    
    # Create test data
    try:
        users = create_test_data()
        
        # Print summary
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Test data created successfully!{Colors.ENDC}")
        
        # Print credentials
        print_test_credentials(users)
        
        # Additional info
        print(f"\n{Colors.BOLD}Notes:{Colors.ENDC}")
        print("- All test emails end with @monochrome.test")
        print("- MFA-enabled users have TOTP already set up")
        print("- Login history has been generated for active users")
        print("- Some users have used backup codes")
        print(f"\n{Colors.BOLD}Testing Scenarios:{Colors.ENDC}")
        print("1. Normal login: Use admin/Admin123!@#")
        print("2. MFA required: Use user1/User123!@#")
        print("3. Email not verified: Use unverified/User123!@#")
        print("4. Account locked: Use locked/User123!@#")
        print("5. No MFA setup: Use staff2/Staff123!@#")
        
    except Exception as e:
        print_status(f"Error creating test data: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()