from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.home, name='app-home'),
    path("user_page/", views.user_page, name='app-user-page'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('chat/', views.chat_view, name='chat'),
    path('task/<int:task_id>/', views.task_detail_view, name='task-detail'),
]
