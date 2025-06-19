#!/usr/bin/env python
"""
Test script to verify all imports work correctly in the Monochrome project.
Run this after setting up the project to ensure everything is configured properly.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monochrome_backend.settings')

print("🔍 Testing Monochrome imports...\n")

# Test Django setup
try:
    import django
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

# Test core imports
test_imports = [
    # Django and DRF
    ("Django", "from django.conf import settings"),
    ("Django REST Framework", "from rest_framework import serializers"),
    ("Django Allauth", "from allauth.account.adapter import DefaultAccountAdapter"),
    ("Django OTP", "from django_otp.models import Device"),
    ("Simple JWT", "from rest_framework_simplejwt.tokens import RefreshToken"),
    
    # Models
    ("User Model", "from users.models import User, UserType, TOTPDevice, BackupCode, LoginHistory"),
    
    # Serializers
    ("User Registration Serializer", "from users.serializers import UserRegistrationSerializer"),
    ("User Serializer", "from users.serializers import UserSerializer"),
    ("Token Serializer", "from users.serializers import CustomTokenObtainPairSerializer"),
    ("MFA Serializers", "from users.serializers import MFASetupSerializer, MFAVerifySerializer, MFALoginSerializer"),
    
    # Views
    ("Registration View", "from users.views import UserRegistrationView"),
    ("Login View", "from users.views import CustomTokenObtainPairView"),
    ("MFA Views", "from users.views import MFASetupView, MFAVerifyView, MFALoginView"),
    
    # Services
    ("User Service", "from users.services import UserService"),
    ("MFA Service", "from users.services import MFAService"),
    ("Security Service", "from users.services import SecurityService"),
    
    # Permissions
    ("Custom Permissions", "from users.permissions import IsOwner, IsAdmin, IsMFAVerified"),
    
    # Common utilities
    ("Standard Response", "from common.utils import StandardResponseMixin"),
    ("Common Middleware", "from common.middleware import MFARequiredMiddleware"),
    ("Custom Exceptions", "from common.exceptions import MonochromeAPIException"),
    
    # URLs
    ("Main URLs", "from monochrome_backend.urls import urlpatterns"),
    ("User URLs", "from users.urls import urlpatterns as user_urls"),
    
    # External libraries
    ("PyOTP", "import pyotp"),
    ("QRCode", "import qrcode"),
    ("Cryptography", "from cryptography.fernet import Fernet"),
    ("Faker", "from faker import Faker"),
]

failed_imports = []

for name, import_statement in test_imports:
    try:
        exec(import_statement)
        print(f"✅ {name}")
    except ImportError as e:
        print(f"❌ {name}: {e}")
        failed_imports.append((name, str(e)))
    except Exception as e:
        print(f"⚠️  {name}: {type(e).__name__}: {e}")
        failed_imports.append((name, str(e)))

# Test database connection
print("\n🔍 Testing database connection...")
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
    print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")

# Test migrations
print("\n🔍 Checking migrations...")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command('showmigrations', '--plan', stdout=out)
    output = out.getvalue()
    if '[ ]' in output:
        print("⚠️  Pending migrations detected")
        print("   Run: python manage.py migrate")
    else:
        print("✅ All migrations applied")
except Exception as e:
    print(f"❌ Error checking migrations: {e}")

# Summary
print("\n" + "="*50)
if failed_imports:
    print(f"\n❌ {len(failed_imports)} import(s) failed:")
    for name, error in failed_imports:
        print(f"   - {name}: {error}")
    print("\n💡 Suggestions:")
    print("   1. Ensure all dependencies are installed: pip install -r requirements.txt")
    print("   2. Check that all app files are created properly")
    print("   3. Verify PYTHONPATH includes the project root")
else:
    print("\n🎉 All imports successful! The project is ready to use.")
    print("\n📋 Next steps:")
    print("   1. Run migrations: python manage.py migrate")
    print("   2. Create superuser: python manage.py createsuperuser")
    print("   3. Run test data setup: python scripts/setup_test_data.py")
    print("   4. Start development server: python scripts/dev_server.py")

print("\n" + "="*50)