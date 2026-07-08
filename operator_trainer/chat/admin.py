from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CustomUser,
    Dialog,
    DialogStep,
    Evaluation,
    Message,
    Question,
    Scenario,
    ScenarioStep,
    UserResponse,
)


class ScenarioStepInline(admin.TabularInline):
    model = ScenarioStep
    extra = 1
    fields = (
        'step_number',
        'client_message',
        'expected_operator_response',
        'keywords',
        'evaluation_criteria',
        'hint',
        'is_final',
    )
    ordering = ('step_number',)


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('title', 'client_name', 'difficulty', 'is_active', 'steps_count', 'updated_at')
    list_filter = ('difficulty', 'is_active', 'created_at')
    search_fields = ('title', 'client_name', 'situation', 'goal')
    inlines = [ScenarioStepInline]
    fieldsets = (
        ('Клиент и кейс', {
            'fields': ('title', 'client_name', 'client_status', 'client_avatar', 'difficulty', 'is_active')
        }),
        ('Сценарий', {
            'fields': ('situation', 'goal', 'initial_message', 'hints', 'knowledge_base_url', 'stop_words')
        }),
    )

    def steps_count(self, obj):
        return obj.steps.count()

    steps_count.short_description = 'Шагов'


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('role', 'sender', 'text', 'score', 'timestamp', 'short_feedback')
    fields = ('role', 'sender', 'text', 'score', 'is_correct', 'admin_comment', 'short_feedback', 'timestamp')

    def short_feedback(self, obj):
        return obj.metadata.get('evaluation_feedback', '-') if obj.metadata else '-'

    short_feedback.short_description = 'Автооценка'


@admin.register(Dialog)
class DialogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'scenario_title', 'client_name', 'status', 'score', 'current_step', 'start_time', 'end_time')
    list_filter = ('status', 'is_completed', 'is_closed', 'scenario__difficulty', 'start_time')
    search_fields = ('user__username', 'user__email', 'client_name', 'scenario__title')
    readonly_fields = ('score', 'current_step', 'start_time', 'end_time')
    list_select_related = ('user', 'scenario')
    inlines = [MessageInline]

    def scenario_title(self, obj):
        return obj.get_training_title()

    scenario_title.short_description = 'Кейс'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('get_dialog_info', 'role', 'sender_info', 'short_text', 'score', 'is_correct', 'timestamp')
    list_filter = ('role', 'is_correct', 'timestamp')
    search_fields = ('text', 'sender__username', 'dialog__user__email', 'dialog__scenario__title')
    readonly_fields = ('get_dialog_info', 'sender_info', 'metadata')
    list_select_related = ('dialog__user', 'dialog__scenario', 'sender')

    def get_dialog_info(self, obj):
        return format_html(
            '{}<br><small>{}</small>',
            obj.dialog.get_training_title(),
            obj.dialog.user.email or obj.dialog.user.username,
        )

    get_dialog_info.short_description = 'Диалог'

    def sender_info(self, obj):
        if obj.sender:
            return obj.sender.username
        return obj.get_role_display()

    sender_info.short_description = 'Отправитель'

    def short_text(self, obj):
        return obj.text[:70] + '...' if len(obj.text) > 70 else obj.text

    short_text.short_description = 'Текст'


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('dialog', 'scenario_step', 'score', 'max_score', 'created_at')
    list_filter = ('created_at', 'score')
    search_fields = ('dialog__user__username', 'dialog__scenario__title', 'feedback')
    readonly_fields = ('matched_keywords', 'missed_keywords', 'created_at')
    list_select_related = ('dialog', 'scenario_step')


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_trainer', 'date_joined', 'is_active', 'last_login')
    list_filter = ('is_trainer', 'is_active', 'date_joined')
    search_fields = ('username', 'email')


class LegacyDialogStepInline(admin.TabularInline):
    model = DialogStep
    extra = 0
    fields = ('step_number', 'trigger_keywords', 'client_message', 'expected_operator_response', 'response_variation')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'max_steps', 'created_at')
    search_fields = ('text',)
    list_filter = ('created_at', 'max_steps')
    inlines = [LegacyDialogStepInline]

    def text_preview(self, obj):
        return obj.text[:70] + '...' if len(obj.text) > 70 else obj.text

    text_preview.short_description = 'Legacy-вопрос'


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'scenario', 'question', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'created_at')
    search_fields = ('user__username', 'answer', 'feedback')
