from django.urls import path
from . import views
from .views import instructor_signup_view
from django.contrib.auth import views as auth_views
from .views import llm_query_view

urlpatterns = [
    path("", views.home, name='app-home'),
    path("testusers/", views.testusers, name='app-testusers'),
    # path("user_page/<int:user_id>/", views.user_page, name='app-user-page'),
    path("user_page/", views.user_page, name='app-user-page'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('chat/', views.chat_view, name='chat'),
    path('llm_query/', llm_query_view, name='llm_query'),
    path('instructor_signup/', views.instructor_signup_view, name='instructor_signup'),
]
