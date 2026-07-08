import logging
import json
import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.db.models import Avg, Case, Count, IntegerField, Prefetch, Value, When
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm
from .models import CustomUser, Dialog, Evaluation, Message, ResponseTemplate
from .services.avatars import ensure_dialog_client_avatar
from .services.client_engine import (
    get_or_create_active_dialog,
    get_next_available_scenario,
    handle_operator_turn,
    start_dialog_for_scenario,
)

logger = logging.getLogger(__name__)

ALLOWED_AVATAR_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat_trainer')
    else:
        form = RegisterForm()
    return render(request, 'chat/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('chat_trainer')
    else:
        form = LoginForm()
    return render(request, 'chat/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')


def serialize_message(message):
    sender = message.role
    if message.role == Message.ROLE_ADMIN:
        sender = Message.ROLE_ADMIN
    elif message.sender_id:
        sender = Message.ROLE_OPERATOR

    return {
        'id': message.id,
        'text': message.text,
        'sender': sender,
        'timestamp': timezone.localtime(message.timestamp).strftime("%H:%M"),
        'admin_comment': message.admin_comment,
        'score': message.score,
        'feedback': message.metadata.get('evaluation_feedback', ''),
        'sender_name': message.sender.username if message.sender_id else '',
        'sender_avatar': message.sender.avatar if message.sender_id else '',
        'client_avatar': ensure_dialog_client_avatar(message.dialog) if sender in {Message.ROLE_CLIENT, Message.ROLE_AI} else '',
    }


def get_dialogs_data_for_user(user):
    dialogs = apply_dialog_order(Dialog.objects.filter(user=user)).select_related('scenario').prefetch_related('messages')
    return [serialize_dialog_item(dialog) for dialog in dialogs]


def apply_dialog_order(queryset):
    return queryset.annotate(
        order_bucket=Case(
            When(is_closed=False, is_completed=False, then=Value(0)),
            When(status=Dialog.STATUS_COMPLETED, then=Value(1)),
            When(status=Dialog.STATUS_CLOSED, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        ),
    ).order_by('order_bucket', '-start_time')


def serialize_dialog_item(dialog):
    is_archived = dialog.is_completed or dialog.is_closed
    latest_evaluation = dialog.evaluations.order_by('-created_at').first()
    return {
        'id': dialog.id,
        'title': dialog.get_training_title(),
        'client_name': dialog.client_name,
        'last_message': dialog.get_last_message(),
        'unread_count': dialog.unread_count,
        'client_avatar': ensure_dialog_client_avatar(dialog),
        'status': dialog.status,
        'status_label': dialog.get_status_display(),
        'score': dialog.score,
        'is_closed': dialog.is_closed,
        'is_completed': dialog.is_completed,
        'is_archived': is_archived,
        'can_close': not dialog.is_closed,
        'needs_operator_response': dialog.needs_operator_response,
        'has_admin_evaluation': bool(latest_evaluation),
        'evaluation_score': latest_evaluation.score if latest_evaluation else 0,
        'evaluation_description': latest_evaluation.feedback if latest_evaluation else '',
    }


def get_training_panel_data(dialog):
    scenario = dialog.scenario
    if not scenario:
        return {
            'title': dialog.get_training_title(),
            'client_name': dialog.client_name,
            'client_status': 'online',
            'situation': '',
            'goal': '',
            'hints': [],
            'knowledge_base_url': '',
            'difficulty': 'medium',
        }

    step = scenario.steps.filter(step_number=dialog.current_step).first()
    hints = scenario.get_hints_list()
    if step and step.hint:
        hints = [step.hint, *hints]

    return {
        'title': scenario.title,
        'client_name': scenario.client_name,
        'client_status': scenario.client_status,
        'situation': scenario.situation,
        'goal': scenario.goal,
        'hints': hints,
        'knowledge_base_url': scenario.knowledge_base_url,
        'difficulty': scenario.get_difficulty_display(),
    }


@login_required
def chat_trainer(request):
    if request.user.is_staff:
        return redirect('operator_monitor')

    current_time = datetime.now().strftime("%H:%M")
    dialog = get_or_create_active_dialog(request.user)
    if not dialog:
        dialog = apply_dialog_order(Dialog.objects.filter(user=request.user)).select_related('scenario').first()
        if not dialog:
            return render(request, 'chat/no_more_dialogs.html', {
                'message': 'Активных обучающих сценариев пока нет. Попросите администратора добавить кейсы.'
            })

    current_client_avatar = ensure_dialog_client_avatar(dialog)
    dialogs = list(apply_dialog_order(Dialog.objects.filter(user=request.user)).select_related('scenario').prefetch_related('messages'))
    for item in dialogs:
        ensure_dialog_client_avatar(item)
    active_dialogs = [item for item in dialogs if not item.is_completed and not item.is_closed]
    archived_dialogs = [item for item in dialogs if item.is_completed or item.is_closed]

    messages = dialog.messages.all().order_by('timestamp')
    panel = get_training_panel_data(dialog)
    current_evaluation = dialog.evaluations.order_by('-created_at').first()

    return render(request, 'chat/index.html', {
        'messages': messages,
        'dialogs': dialogs,
        'active_dialogs': active_dialogs,
        'archived_dialogs': archived_dialogs,
        'current_dialog': dialog,
        'current_client_avatar': current_client_avatar,
        'current_time': current_time,
        'client_data': {
            'name': panel['client_name'],
            'avatar': current_client_avatar,
            'status': panel['client_status'],
        },
        'training_panel': panel,
        'user': request.user,
        'hints': panel['hints'],
        'admin_comment': '',
        'client_responses': [],
        'is_multi_step': dialog.is_multi_step,
        'current_step': dialog.current_step,
        'max_steps': dialog.get_max_steps(),
        'can_send': not dialog.is_closed and not dialog.is_completed,
        'current_evaluation': current_evaluation,
        'initial_dialogs_json': json.dumps(get_dialogs_data_for_user(request.user), ensure_ascii=False),
    })


@login_required
@require_POST
def send_message(request):
    try:
        user = request.user
        text = request.POST.get('text', '').strip()
        dialog_id = request.POST.get('dialog_id')

        if not text:
            return JsonResponse({'status': 'error', 'message': 'Текст сообщения не может быть пустым'}, status=400)

        dialog = Dialog.objects.filter(user=user, id=dialog_id, is_closed=False, is_completed=False).select_related('scenario').first()
        if not dialog:
            return JsonResponse({'status': 'error', 'message': 'Активный диалог не найден'}, status=404)

        turn = handle_operator_turn(dialog, text, user)
        next_dialog = None
        if not turn.continue_dialog:
            next_scenario = get_next_available_scenario(user)
            if next_scenario:
                from .services.client_engine import start_dialog_for_scenario
                next_dialog = start_dialog_for_scenario(user, next_scenario)

        response = {
            'status': 'ok',
            'continue_dialog': turn.continue_dialog,
            'message': turn.operator_message.text,
            'timestamp': timezone.localtime(turn.operator_message.timestamp).strftime("%H:%M"),
            'sender_avatar': user.avatar,
            'score': turn.operator_message.score,
            'feedback': turn.evaluation_feedback,
            'current_step': dialog.current_step,
            'max_steps': dialog.get_max_steps(),
            'new_dialog_id': next_dialog.id if next_dialog else None,
            'no_more_questions': not turn.continue_dialog and next_dialog is None,
            'dialogs': get_dialogs_data_for_user(user),
        }
        if turn.client_message:
            response.update({
                'new_message': turn.client_message.text,
                'new_timestamp': timezone.localtime(turn.client_message.timestamp).strftime("%H:%M"),
            })
        if turn.completion_message:
            response.update({
                'completion_message': turn.completion_message.text,
                'completion_timestamp': timezone.localtime(turn.completion_message.timestamp).strftime("%H:%M"),
            })
        return JsonResponse(response)

    except Exception as e:
        logger.error(f"Ошибка сохранения: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def get_dialog_data(request):
    if request.method == 'POST':
        try:
            dialog_id = request.POST.get('dialog_id')
            dialog_filter = {'id': dialog_id}
            if not request.user.is_staff:
                dialog_filter['user'] = request.user
            dialog = Dialog.objects.select_related('user', 'scenario').filter(**dialog_filter).first()
            if not dialog:
                return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)

            messages = [serialize_message(msg) for msg in dialog.messages.all()]
            dialogs_data = get_dialogs_data_for_user(request.user)
            panel = get_training_panel_data(dialog)
            latest_evaluation = dialog.evaluations.order_by('-created_at').first()

            return JsonResponse({
                'status': 'ok',
                'messages': messages,
                'dialogs': dialogs_data,
                'operator_name': dialog.user.username,
                'operator_avatar': dialog.user.avatar,
                'dialog_title': dialog.get_training_title(),
                'dialog_score': dialog.score,
                'evaluation_description': latest_evaluation.feedback if latest_evaluation else '',
                'has_admin_evaluation': bool(latest_evaluation),
                'evaluation_score': latest_evaluation.score if latest_evaluation else 0,
                'can_send': not dialog.is_closed and not dialog.is_completed,
                'dialog_status': dialog.status,
                'status_label': dialog.get_status_display(),
                'needs_operator_response': dialog.needs_operator_response,
                'is_multi_step': dialog.is_multi_step,
                'current_step': dialog.current_step,
                'max_steps': dialog.get_max_steps(),
                'admin_comment': dialog.messages.filter(admin_comment__isnull=False).first().admin_comment if dialog.messages.filter(admin_comment__isnull=False).exists() else "",
                'training_panel': panel,
                'client_avatar': ensure_dialog_client_avatar(dialog),
            })
        except Exception as e:
            logger.error(f"Ошибка получения данных: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def mark_read(request):
    if request.method == 'POST':
        try:
            dialog_id = request.POST.get('dialog_id')
            dialog = Dialog.objects.filter(user=request.user, id=dialog_id).first()
            if dialog:
                dialog.unread_count = 0
                dialog.messages.update(is_read=True)
                dialog.save()
                return JsonResponse({'status': 'ok'})
            return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)
        except Exception as e:
            logger.error(f"Ошибка сброса непрочитанных: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def close_dialog(request):
    if request.method == 'POST':
        try:
            dialog_id = request.POST.get('dialog_id')
            dialog = Dialog.objects.filter(user=request.user, id=dialog_id).first()
            if dialog:
                dialog.is_closed = True
                dialog.status = Dialog.STATUS_CLOSED
                dialog.save(update_fields=['is_closed', 'status'])

                new_dialog = None
                has_active_dialogs = Dialog.objects.filter(
                    user=request.user,
                    is_closed=False,
                    is_completed=False,
                ).exists()
                if not has_active_dialogs:
                    next_scenario = get_next_available_scenario(request.user)
                    if next_scenario:
                        new_dialog = start_dialog_for_scenario(request.user, next_scenario)

                return JsonResponse({
                    'status': 'ok',
                    'dialogs': get_dialogs_data_for_user(request.user),
                    'new_dialog_id': new_dialog.id if new_dialog else None,
                })
            return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)
        except Exception as e:
            logger.error(f"Ошибка закрытия диалога: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def dashboard_view(request):
    dialogs = Dialog.objects.filter(user=request.user)
    completed_dialogs = dialogs.filter(is_completed=True)
    evaluations = Evaluation.objects.filter(dialog__user=request.user)
    operator_messages = Message.objects.filter(dialog__user=request.user, role=Message.ROLE_OPERATOR)

    average_score = round(evaluations.aggregate(value=Avg('score'))['value'] or 0)
    completed_count = completed_dialogs.count()
    active_count = dialogs.filter(is_closed=False, is_completed=False).count()
    total_messages = operator_messages.count()
    best_score = evaluations.order_by('-score').values_list('score', flat=True).first() or 0

    achievements = [
        {
            'title': 'Первый контакт',
            'description': 'Отправить первый ответ клиенту',
            'is_unlocked': total_messages >= 1,
        },
        {
            'title': 'Закрытый кейс',
            'description': 'Завершить первый тренировочный диалог',
            'is_unlocked': completed_count >= 1,
        },
        {
            'title': 'Уверенный оператор',
            'description': 'Набрать среднюю оценку 70%+',
            'is_unlocked': average_score >= 70,
        },
        {
            'title': 'Отличный ответ',
            'description': 'Получить 90%+ за отдельный ответ',
            'is_unlocked': best_score >= 90,
        },
        {
            'title': 'Серия практики',
            'description': 'Завершить 3 диалога',
            'is_unlocked': completed_count >= 3,
        },
    ]

    recent_dialogs = dialogs.select_related('scenario').annotate(
        messages_count=Count('messages'),
    ).order_by('-start_time')[:6]

    return render(request, 'chat/dashboard.html', {
        'active_count': active_count,
        'completed_count': completed_count,
        'total_messages': total_messages,
        'average_score': average_score,
        'best_score': best_score,
        'achievements': achievements,
        'unlocked_count': sum(1 for achievement in achievements if achievement['is_unlocked']),
        'recent_dialogs': recent_dialogs,
    })


@login_required
def templates_library_view(request):
    return render(request, 'chat/templates_library.html')


@login_required
@require_POST
def update_avatar(request):
    avatar_file = request.FILES.get('avatar')
    if not avatar_file:
        return redirect('dashboard')

    extension = Path(avatar_file.name).suffix.lower()
    if extension not in ALLOWED_AVATAR_EXTENSIONS:
        return redirect('dashboard')

    storage = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
    filename = f"avatars/user-{request.user.id}-{uuid.uuid4().hex}{extension}"
    saved_name = storage.save(filename, avatar_file)
    request.user.avatar = storage.url(saved_name)
    request.user.save(update_fields=['avatar'])
    return redirect('dashboard')


def _require_staff(user):
    if not user.is_staff:
        raise PermissionDenied


@login_required
def operator_monitor_view(request):
    _require_staff(request.user)
    dialog_queryset = apply_dialog_order(Dialog.objects.all()).select_related('scenario').prefetch_related('messages')
    operators = CustomUser.objects.filter(is_staff=False).prefetch_related(Prefetch('dialogs', queryset=dialog_queryset)).order_by('username')
    first_dialog = apply_dialog_order(Dialog.objects.filter(user__is_staff=False)).select_related('user', 'scenario').first()
    return render(request, 'chat/operator_monitor.html', {
        'operators': operators,
        'first_dialog': first_dialog,
    })


@login_required
@require_POST
def admin_send_comment(request):
    _require_staff(request.user)
    dialog_id = request.POST.get('dialog_id')
    text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'status': 'error', 'message': 'Комментарий не может быть пустым'}, status=400)

    dialog = Dialog.objects.filter(id=dialog_id).first()
    if not dialog:
        return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)

    message = Message.objects.create(
        dialog=dialog,
        sender=request.user,
        role=Message.ROLE_ADMIN,
        text=text,
        metadata={'admin_comment': True},
    )
    return JsonResponse({
        'status': 'ok',
        'message': serialize_message(message),
    })


@login_required
@require_POST
def admin_rate_dialog(request):
    _require_staff(request.user)
    dialog_id = request.POST.get('dialog_id')
    description = request.POST.get('description', '').strip()

    try:
        score = int(request.POST.get('score', '0'))
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Оценка должна быть числом'}, status=400)

    if score < 0 or score > 100:
        return JsonResponse({'status': 'error', 'message': 'Оценка должна быть от 0 до 100'}, status=400)

    dialog = Dialog.objects.filter(id=dialog_id).first()
    if not dialog:
        return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)

    message = dialog.messages.filter(role=Message.ROLE_OPERATOR).order_by('-timestamp').first()
    if not message:
        return JsonResponse({'status': 'error', 'message': 'В диалоге пока нет ответа оператора для оценки'}, status=400)

    message.score = score
    message.metadata['admin_evaluation_feedback'] = description
    message.save(update_fields=['score', 'metadata'])

    Evaluation.objects.update_or_create(
        dialog=dialog,
        message=message,
        defaults={
            'score': score,
            'max_score': 100,
            'feedback': description,
        },
    )
    dialog.score = score
    dialog.save(update_fields=['score'])

    return JsonResponse({
        'status': 'ok',
        'score': score,
        'description': description,
    })


@login_required
def template_suggestions(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'status': 'ok', 'templates': []})

    templates = ResponseTemplate.objects.filter(
        title__icontains=query,
    ) | ResponseTemplate.objects.filter(
        keywords__icontains=query,
    ) | ResponseTemplate.objects.filter(
        text__icontains=query,
    )

    return JsonResponse({
        'status': 'ok',
        'templates': [
            {
                'id': template.id,
                'title': template.title,
                'category': template.category,
                'text': template.text,
            }
            for template in templates.distinct()[:5]
        ],
    })