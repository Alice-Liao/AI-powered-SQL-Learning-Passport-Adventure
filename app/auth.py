from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .models import Users
from django.contrib.auth.hashers import check_password

class EmailBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            # Check in your custom Users table
            custom_user = Users.objects.get(email=username)
            if custom_user.password == password:  # For now, use direct comparison
                # Get or create Django User
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    user = User.objects.create_user(
                        username=username,
                        email=username,
                        password=password
                    )
                    user.first_name = custom_user.name
                    user.save()
                return user
        except Users.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None 