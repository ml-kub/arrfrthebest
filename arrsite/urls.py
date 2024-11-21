from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.register, name='register'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('profile/<str:iin_bin>/', views.profile, name='profile'),
    path('notifications/management/', views.notifications_management, name='notifications_management'),
    path('notifications/create/', views.create_notification, name='create_notification'),
    path('notifications/reply/', views.create_notification_reply, name='create_notification_reply'),
    path('logout/', views.logout_view, name='logout'),
    path('announcements/management/', views.announcements_management, name='announcements_management'),
    path('announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/<int:announcement_id>/', views.get_announcement, name='get_announcement'),
    path('announcements/<int:announcement_id>/edit/', views.edit_announcement, name='edit_announcement'),
    path('announcements/<int:announcement_id>/delete/', views.delete_announcement, name='delete_announcement'),
] 