from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Users
from django.contrib.auth.hashers import make_password

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True)
    name = forms.CharField(max_length=30, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'name', 'password1', 'password2')
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Users.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create record in Users table with hashed password
            Users.objects.create(
                name=self.cleaned_data['name'],
                email=self.cleaned_data['email'],
                password=make_password(self.cleaned_data['password1'])  # Hash the password
            )
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(max_length=254, required=True)
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False) 