#!/usr/bin/env python
"""
Test script to verify all imports work correctly.
"""

import os
import sys
import django

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monochrome_backend.settings')
django.setup()

# Test imports
try:
    from users.models import User, TOTPDevice, BackupCode, LoginHistory
    print("✅ User models imported successfully")
    
    from users.serializers import UserRegistrationSerializer, UserSerializer
    print("✅ User serializers imported successfully")
    
    from users.views import UserRegistrationView, CustomTokenObtainPairView
    print("✅ User views imported successfully")
    
    from users.services import UserService, MFAService
    print("✅ User services imported successfully")
    
    from common.utils import StandardResponseMixin
    print("✅ Common utils imported successfully")
    
    from common.middleware import MFARequiredMiddleware
    print("✅ Common middleware imported successfully")
    
    print("\n🎉 All imports successful! The project is ready to use.")
    
except Exception as e:
    print(f"\n❌ Import error: {str(e)}")
    import traceback
    traceback.print_exc()
