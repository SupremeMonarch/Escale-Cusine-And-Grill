#!/usr/bin/env python
"""
Debug script to test staff login and verify password reset worked
"""
import os
import django
import sys

# Setup Django
os.chdir('ECAG_site')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECAG_site.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

def test_staff_login(username: str, password: str):
    """Test if a staff member can login with given credentials"""
    print(f"\n=== Testing Staff Login ===")
    print(f"Username: {username}")
    print(f"Password: {password}")
    
    # Check if user exists
    try:
        user = User.objects.get(username=username)
        print(f"✓ User found: {user.email}")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - is_superuser: {user.is_superuser}")
    except User.DoesNotExist:
        print(f"✗ User '{username}' not found")
        return False
    
    # Try to authenticate
    auth_user = authenticate(username=username, password=password)
    if auth_user:
        print(f"✓ Authentication SUCCESSFUL")
        return True
    else:
        print(f"✗ Authentication FAILED - password is incorrect")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_staff_login.py <username> <password>")
        print("\nExample: python test_staff_login.py john_staff myTempPassword123")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    success = test_staff_login(username, password)
    sys.exit(0 if success else 1)
