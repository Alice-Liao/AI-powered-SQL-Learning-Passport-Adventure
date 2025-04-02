from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home, name='home'),
    path("testusers/", views.testusers, name='app-testusers'),
    path("login/", views.login_user, name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_user, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard")
]
