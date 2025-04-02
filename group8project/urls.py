from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("app_dev/", include("app.urls")),
    # path('login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    # path('logout/', auth_views.LogoutView.as_view(template_name='app/logout.html'), name='logout')
]
