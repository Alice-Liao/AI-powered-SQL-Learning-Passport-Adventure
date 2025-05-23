from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import board_view

urlpatterns = [
    path("", views.home, name='app-home'),
    path("user_page/", views.user_page, name='app-user-page'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('chat/', views.chat_view, name='chat'),
    path('task/<int:task_id>/', views.task_detail_view, name='task-detail'),
    path('llm_query/', views.llm_query_view, name='llm_query'),
    path('instructor_signup/', views.instructor_signup_view, name='instructor_signup'),
    path('board/', board_view, name='board'),
    path('game/<int:task_id>/', views.game_page, name='game_page'),
    path('execute-query/<int:task_id>/', views.execute_query, name='execute-query'),
    path('tasks/', views.task_list, name='task-list'),
    path('instructor-dashboard/', views.instructor_dashboard, name='instructor-dashboard'),
    path('send_message/', views.send_message, name='send_message'),
    path('message_inbox/', views.message_inbox, name='message_inbox'),
    path('reply_message/', views.reply_message, name='reply_message'),
    path('instructor-messages/', views.instructor_message_inbox, name='instructor_message_inbox'),
]
