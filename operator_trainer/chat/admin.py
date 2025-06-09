from django.contrib import admin
from django.contrib.auth.models import User
from .models import Dialog, Message, CustomUser
from django.utils.html import format_html


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'timestamp', 'get_user_email')
    fields = ('sender', 'get_user_email', 'text', 'is_correct', 'admin_comment', 'timestamp')

    def get_user_email(self, obj):
        return obj.dialog.user.email if obj.dialog and obj.dialog.user else '-'

    get_user_email.short_description = 'Email'


@admin.register(Dialog)
class DialogAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_email', 'start_time', 'end_time', 'is_completed', 'message_count')
    list_select_related = ('user',)
    inlines = [MessageInline]
    list_filter = ('is_completed', 'start_time', 'user__email')  # Фильтр для группировки по пользователю
    search_fields = ('user__username', 'user__email')

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = 'Сообщений'

    # Сортировка для группировки диалогов по пользователю
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').order_by('user__email', 'start_time')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('get_dialog_info', 'sender_info', 'short_text', 'is_correct', 'timestamp')
    list_editable = ('is_correct',)
    search_fields = ('text', 'sender__username', 'dialog__user__email', 'dialog__user__username')
    list_filter = ('is_correct', 'sender', 'dialog__user')
    readonly_fields = ('get_dialog_info', 'sender_info')
    list_select_related = ('dialog__user', 'sender')

    def get_dialog_info(self, obj):
        if obj.dialog:
            return format_html(
                '{}<br><small>{}</small>',
                obj.dialog.user.username,
                obj.dialog.user.email
            )
        return '-'

    get_dialog_info.short_description = 'Диалог (Пользователь)'
    get_dialog_info.admin_order_field = 'dialog__user__username'

    def sender_info(self, obj):
        if obj.sender:
            return format_html(
                '{}<br><small>{}</small>',
                obj.sender.username,
                obj.sender.email if obj.sender.email else '-'
            )
        return 'Клиент'

    sender_info.short_description = 'Отправитель'
    sender_info.admin_order_field = 'sender__username'

    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text

    short_text.short_description = 'Текст'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('dialog__user', 'sender')


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_trainer', 'date_joined', 'is_active', 'last_login')
    list_filter = ('is_trainer', 'is_active', 'date_joined')
    search_fields = ('username', 'email')
    list_select_related = True