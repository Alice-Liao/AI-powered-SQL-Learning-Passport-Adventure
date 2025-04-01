from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name='app-home'),
    path("testusers/", views.testusers, name='app-testusers'),
    # path("user_page/<int:user_id>/", views.user_page, name='app-user-page'),
    path("user_page/", views.user_page, name='app-user-page'),
]
