from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.register, name='register'),
    path('profile/<str:iin_bin>/', views.profile, name='profile'),
    path('notifications/management/', views.notifications_management, name='notifications_management'),
    path('notifications/create/', views.create_notification, name='create_notification'),
    path('notifications/reply/', views.create_notification_reply, name='create_notification_reply'),
] 