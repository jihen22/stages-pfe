from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notifications_list, name='list'),
    path('tout-lu/', views.mark_all_read, name='mark_all_read'),
    path('<int:pk>/lire/', views.notification_read, name='read'),
]
