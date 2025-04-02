from django.contrib.auth.backends import BaseBackend
from .models import Users
from django.contrib.auth.hashers import check_password

class CustomUserBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Check if the user exists
            user = Users.objects.get(email=username)
            # Verify the password
            if user and user.password == password:  # Replace with hashed password check if applicable
                return user
        except Users.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            return None