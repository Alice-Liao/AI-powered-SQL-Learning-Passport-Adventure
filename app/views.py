from django.shortcuts import render
from .models import Users
from django.db import connection

# Create your views here.

def testusers(request):
  cursor = connection.cursor()
  cursor.execute("SELECT * FROM users")
  rows = cursor.fetchall()
  context = {
    "data": rows
  }
  return render(request, "testusers.html", context)