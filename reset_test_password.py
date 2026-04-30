import os
import django

os.chdir('ECAG_site')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECAG_site.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

# Get the user
u = User.objects.get(username='lamiguel35')

# Set a new simple password
new_pass = 'TestPassword123'
u.set_password(new_pass)
u.save()
print(f"Password reset to: {new_pass}")

# Test authentication
auth_result = authenticate(username='lamiguel35', password=new_pass)
if auth_result:
    print(f"✓ Authentication SUCCESS")
else:
    print(f"✗ Authentication FAILED")

# Also test the original password
auth_result2 = authenticate(username='lamiguel35', password='CFfAZlHXJJiNiSrU')
if auth_result2:
    print(f"✓ Original password still works")
else:
    print(f"✗ Original password doesn't work")
