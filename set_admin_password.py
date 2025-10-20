from django.contrib.auth.models import User

# Set password for admin user
try:
    u = User.objects.get(username='admin')
    u.set_password('admin123')
    u.save()
    print('Password set successfully for admin user')
    print('Username: admin')
    print('Password: admin123')
except User.DoesNotExist:
    print('Admin user not found')
