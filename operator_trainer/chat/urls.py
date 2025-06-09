from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_trainer, name='chat_trainer'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('send/', views.send_message, name='send_message'),

]