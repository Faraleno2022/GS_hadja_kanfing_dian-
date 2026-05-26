from django.urls import path

from . import views


app_name = 'synchronisation'

urlpatterns = [
    path('health/', views.health, name='health'),
    path('devices/register/', views.register_device, name='register_device'),
    path('push/', views.push, name='push'),
    path('pull/', views.pull, name='pull'),
]
