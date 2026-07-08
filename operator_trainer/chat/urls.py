from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_trainer, name='chat_trainer'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('templates-library/', views.templates_library_view, name='templates_library'),
    path('dashboard/avatar/', views.update_avatar, name='update_avatar'),
    path('operator-monitor/', views.operator_monitor_view, name='operator_monitor'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('send/', views.send_message, name='send_message'),
    path('get_dialog_data/', views.get_dialog_data, name='get_dialog_data'),
    path('admin_send_comment/', views.admin_send_comment, name='admin_send_comment'),
    path('admin_rate_dialog/', views.admin_rate_dialog, name='admin_rate_dialog'),
    path('template_suggestions/', views.template_suggestions, name='template_suggestions'),
    path('mark_read/', views.mark_read, name='mark_read'),
    path('close_dialog/', views.close_dialog, name='close_dialog'),
]