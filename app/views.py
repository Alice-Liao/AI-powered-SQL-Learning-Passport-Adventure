from uuid import UUID
import uuid
from django.shortcuts import render, redirect
from .models import Users
from django.db import connection
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout


def home(request):
  return render(request, "app/home.html", {"title": "Home"})

def testusers(request):
  cursor = connection.cursor()
  cursor.execute("SELECT * FROM users")
  rows = cursor.fetchall()
  context = {
    "data": rows
  }
  return render(request, "app/testusers.html", context={**context, "title": "List Users"})

def register(request):
  if request.method == "POST":
    email = request.POST.get("email")
    password = request.POST.get("password")
    confirm_password = request.POST.get("confirm_password")

    if password == confirm_password:
      if Users.objects.filter(email=email).exists():
        messages.error(request, "Email already exists.")
      else:
        Users.objects.create(name=str(uuid.uuid4()).replace("-", "")[:30], email=email, password=password)
        messages.success(request, "Registration successful.")
        return redirect("login")
    else:
      messages.error(request, "Passwords do not match.")
  
  return render(request, "app/register.html", {"title": "Register"})

def login_user(request):
  if request.method == "POST":
    email = request.POST.get("email")
    password = request.POST.get("password")

    try:
      user = Users.objects.get(email=email)
      print(user.email)
      print(user.password)
      if password == user.password:
        authenticate(request, username=email, password=password)
        login(request, user)
        return redirect("dashboard")
      else:
        messages.error(request, "Invalid email or password.")
    except Users.DoesNotExist:
      messages.error(request, "Invalid email or password.")

  return render(request, "app/login.html", {"title": "Login"})

def logout_user(request):
  logout(request)
  return redirect("login")

def dashboard(request):
  if request.user.is_authenticated:
    return render(request, "app/dashboard.html", {"title": "Dashboard"})

  return redirect("login")