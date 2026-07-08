from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, format_html

from .models import CustomUser, Dialog, Message


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_superuser', 'is_trainer', 'is_active', 'last_login')
    list_filter = ('is_staff', 'is_superuser', 'is_trainer', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Профиль тренажера', {
            'fields': ('avatar', 'is_trainer')
        }),
    )


@admin.register(Dialog)
class DialogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'scenario_title', 'client_name', 'status', 'score', 'start_time', 'end_time')
    list_filter = ('status', 'is_completed', 'is_closed', 'start_time')
    search_fields = ('user__username', 'user__email', 'client_name', 'scenario__title', 'messages__text')
    readonly_fields = ('conversation_transcript', 'score', 'current_step', 'start_time', 'end_time')
    list_select_related = ('user', 'scenario')
    fieldsets = (
        ('Диалог', {
            'fields': ('conversation_transcript',)
        }),
        ('Сводка', {
            'fields': ('user', 'scenario', 'client_name', 'status', 'score', 'current_step', 'start_time', 'end_time')
        }),
    )

    def scenario_title(self, obj):
        return obj.get_training_title()

    scenario_title.short_description = 'Кейс'

    def conversation_transcript(self, obj):
        if not obj.pk:
            return '-'

        rows = []
        for message in obj.messages.order_by('timestamp'):
            if message.sender_id:
                sender = 'Оператор'
            elif message.role == Message.ROLE_SYSTEM:
                sender = 'Система'
            else:
                sender = obj.client_name or 'Клиент'

            timestamp = message.timestamp.strftime('%d.%m.%Y %H:%M')
            score = f" · {message.score}%" if message.score else ""
            rows.append(
                "<div class='admin-transcript-row' style='"
                "padding:10px 12px;margin:0 0 10px;border:1px solid #dbe7d4;"
                "border-radius:12px;background:#f8fbf6;'>"
                f"<strong>{escape(sender)}</strong> "
                f"<span style='color:#64705f;font-size:12px;'>{escape(timestamp)}{escape(score)}</span>"
                f"<p style='margin:6px 0 0;white-space:pre-wrap;'>{escape(message.text)}</p>"
                "</div>"
            )

        if not rows:
            return 'Сообщений пока нет.'

        return format_html(
            "<div style='max-width:920px;'>{}</div>",
            format_html(''.join(rows)),
        )

    conversation_transcript.short_description = 'Стенограмма диалога'
