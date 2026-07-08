import logging
from datetime import datetime

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm
from .models import Dialog, Message
from .services.client_engine import get_or_create_active_dialog, get_next_available_scenario, handle_operator_turn

logger = logging.getLogger(__name__)


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
    if message.sender_id:
        sender = Message.ROLE_OPERATOR

    return {
        'id': message.id,
        'text': message.text,
        'sender': sender,
        'timestamp': timezone.localtime(message.timestamp).strftime("%H:%M"),
        'admin_comment': message.admin_comment,
        'score': message.score,
        'feedback': message.metadata.get('evaluation_feedback', ''),
    }


def get_dialogs_data_for_user(user):
    dialogs = Dialog.objects.filter(user=user, is_closed=False).select_related('scenario').prefetch_related('messages')
    return [{
        'id': dialog.id,
        'title': dialog.get_training_title(),
        'client_name': dialog.client_name,
        'last_message': dialog.get_last_message(),
        'unread_count': dialog.unread_count,
        'client_avatar': dialog.client_avatar,
        'status': dialog.status,
        'score': dialog.score,
    } for dialog in dialogs]


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
    current_time = datetime.now().strftime("%H:%M")
    dialog = get_or_create_active_dialog(request.user)
    if not dialog:
        return render(request, 'chat/no_more_dialogs.html', {
            'message': 'Активных обучающих сценариев пока нет. Попросите администратора добавить кейсы.'
        })

    messages = dialog.messages.all().order_by('timestamp')
    panel = get_training_panel_data(dialog)

    return render(request, 'chat/index.html', {
        'messages': messages,
        'dialogs': Dialog.objects.filter(user=request.user, is_closed=False).select_related('scenario'),
        'current_dialog': dialog,
        'current_time': current_time,
        'client_data': {
            'name': panel['client_name'],
            'avatar': dialog.client_avatar,
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
            dialog = Dialog.objects.filter(user=request.user, id=dialog_id, is_closed=False).first()
            if not dialog:
                return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)

            messages = [serialize_message(msg) for msg in dialog.messages.all()]
            dialogs_data = get_dialogs_data_for_user(request.user)
            panel = get_training_panel_data(dialog)

            return JsonResponse({
                'status': 'ok',
                'messages': messages,
                'dialogs': dialogs_data,
                'is_multi_step': dialog.is_multi_step,
                'current_step': dialog.current_step,
                'max_steps': dialog.get_max_steps(),
                'admin_comment': dialog.messages.filter(admin_comment__isnull=False).first().admin_comment if dialog.messages.filter(admin_comment__isnull=False).exists() else "",
                'training_panel': panel,
                'client_avatar': dialog.client_avatar,
            })
        except Exception as e:
            logger.error(f"Ошибка получения данных: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def mark_read(request):
    if request.method == 'POST':
        try:
            dialog_id = request.POST.get('dialog_id')
            dialog = Dialog.objects.filter(user=request.user, id=dialog_id, is_closed=False).first()
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
            dialog = Dialog.objects.filter(user=request.user, id=dialog_id, is_closed=False).first()
            if dialog:
                dialog.is_closed = True
                dialog.status = Dialog.STATUS_CLOSED
                dialog.save(update_fields=['is_closed', 'status'])
                return JsonResponse({'status': 'ok', 'dialogs': get_dialogs_data_for_user(request.user)})
            return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)
        except Exception as e:
            logger.error(f"Ошибка закрытия диалога: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)