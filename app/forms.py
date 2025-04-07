# ✅ app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Users
from django.contrib.auth.hashers import make_password
from .models import Admins

class BaseSignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True)
    name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ('email', 'name', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check in custom Users model
        if Users.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        # Check in Django User model
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Users.objects.create(
                name=self.cleaned_data['name'],
                email=self.cleaned_data['email'],
                password=make_password(self.cleaned_data['password1'])
            )
        return user

class SignUpForm(BaseSignUpForm):
    pass

class InstructorSignUpForm(BaseSignUpForm):
    def save(self, commit=True):
        user = super().save(commit)
        # 插入 Admins 表
        db_user = Users.objects.get(email=user.email)
        Admins.objects.create(user=db_user)
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(max_length=254, required=True)
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False)
