from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime
import random, logging, time
from django.http import JsonResponse
from .forms import RegisterForm, LoginForm
from .models import Dialog, Message, CustomUser, Question, UserResponse, DialogStep
import string
import random as random_module
from django.utils import timezone
from django.db.models import F
from django.views.decorators.http import require_POST

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

@login_required
def chat_trainer(request):
    current_time = datetime.now().strftime("%H:%M")
    client_data = {
        'name': 'Иван Петров',
        'avatar': 'https://i.pravatar.cc/150?img=10',
        'status': 'online'
    }

    dialog = Dialog.objects.filter(user=request.user, is_closed=False).first()

    if not dialog:
        # Используем только UserResponse для поиска отвеченных вопросов
        answered_questions = Question.objects.filter(
            userresponse__user=request.user
        ).distinct()
        available_questions = Question.objects.exclude(id__in=answered_questions.values_list('id', flat=True))

        if not available_questions.exists():
            return render(request, 'chat/no_more_dialogs.html', {'message': 'Диалогов больше нет :('})

        question = random.choice(available_questions)
        avatar_num = random_module.randint(1, 1000)
        dialog = Dialog.objects.create(
            user=request.user,
            question=question,
            is_multi_step=question.is_multi_step,
            client_avatar=f'https://api.dicebear.com/8.x/pixel-art/png?seed={avatar_num}'
        )
        Message.objects.create(
            dialog=dialog,
            sender=None,
            text=question.text
        )

    messages = dialog.messages.all()
    client_message = messages.filter(sender=None).first()

    question = None
    hints = []
    client_responses = []

    if client_message:
        question = dialog.question
        if question:
            hints = question.get_hints_list()
            client_responses = question.get_client_responses_list()

    admin_comment = ""
    if messages.filter(admin_comment__isnull=False).exists():
        admin_comment = messages.filter(admin_comment__isnull=False).first().admin_comment

    return render(request, 'chat/index.html', {
        'client_message': client_message.text if client_message else "",
        'messages': messages,
        'dialogs': Dialog.objects.filter(user=request.user, is_closed=False),
        'current_dialog': dialog,
        'current_time': current_time,
        'client_data': client_data,
        'user': request.user,
        'hints': hints,
        'admin_comment': admin_comment,
        'client_responses': client_responses,
        'is_multi_step': dialog.is_multi_step,
        'current_step': dialog.current_step,
        'max_steps': dialog.question.max_steps if dialog.question else 1
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

        dialog = Dialog.objects.filter(user=user, id=dialog_id, is_closed=False).first()
        if not dialog:
            return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)

        question = dialog.question
        if not question:
            return JsonResponse({'status': 'error', 'message': 'Вопрос для диалога не найден'}, status=404)

        # Сохраняем ответ оператора
        message = Message.objects.create(
            dialog=dialog,
            sender=user,
            text=text
        )

        # Проверяем на стоп-слова
        stop_words = [sw.strip().lower() for sw in question.stop_words.split(',') if sw.strip()]
        if any(sw in text.lower() for sw in stop_words):
            dialog.is_completed = True
            dialog.end_time = timezone.now()
            dialog.save()
            completion_message = Message.objects.create(dialog=dialog, sender=None, text="Диалог завершен по стоп-слову.")
            # Логика создания нового диалога
            return create_new_dialog_response(user, dialog, message, completion_message)

        # Логика многошагового диалога
        if dialog.is_multi_step:
            # Находим текущий и следующий шаг
            current_step_number = dialog.current_step
            next_step_number = current_step_number + 1

            # Сохраняем ответ оператора
            user_response_obj = UserResponse.objects.create(
                user=user,
                question=question,
                answer=text,
                # is_correct можно будет реализовать позже, сравнив с expected_operator_response
            )

            # Пытаемся найти следующий шаг
            next_step = DialogStep.objects.filter(question=question, step_number=next_step_number).first()

            if next_step:
                # Если есть следующий шаг, продолжаем диалог
                dialog.current_step = next_step_number
                dialog.save()

                # Имитируем задержку на "печать"
                delay = min(len(next_step.client_message) * 0.05, 2.5)
                time.sleep(delay)

                client_msg = Message.objects.create(dialog=dialog, sender=None, text=next_step.client_message)

                return JsonResponse({
                    'status': 'ok',
                    'continue_dialog': True,
                    'message': message.text,
                    'timestamp': timezone.localtime(message.timestamp).strftime("%H:%M"),
                    'new_message': client_msg.text,
                    'new_timestamp': timezone.localtime(client_msg.timestamp).strftime("%H:%M"),
                    'current_step': dialog.current_step,
                    'max_steps': question.steps.count() + 1,
                    'dialogs': get_dialogs_data_for_user(user)
                })
            else:
                # Если следующего шага нет, завершаем диалог
                dialog.is_completed = True
                dialog.end_time = timezone.now()
                dialog.save()
                completion_text = "Вы молодец! Диалог завершен."
                # Имитируем задержку на "печать"
                delay = min(len(completion_text) * 0.05, 2.5)
                time.sleep(delay)
                completion_message = Message.objects.create(dialog=dialog, sender=None, text=completion_text)
                return create_new_dialog_response(user, dialog, message, completion_message)

        # Если не многошаговый диалог, то завершаем как обычно
        dialog.is_completed = True
        dialog.end_time = timezone.now()
        dialog.save()

        UserResponse.objects.create(user=user, question=question, answer=text)

        completion_text = "Вы молодец! Диалог завершен."
        # Имитируем задержку на "печать"
        delay = min(len(completion_text) * 0.05, 2.5)
        time.sleep(delay)

        completion_message = Message.objects.create(dialog=dialog, sender=None, text=completion_text)
        return create_new_dialog_response(user, dialog, message, completion_message)

    except Exception as e:
        logger.error(f"Ошибка сохранения: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def create_new_dialog_response(user, old_dialog, operator_message, completion_message):
    answered_questions_ids = UserResponse.objects.filter(user=user).values_list('question_id', flat=True)
    available_questions = Question.objects.exclude(id__in=answered_questions_ids)

    new_dialog = None
    if available_questions.exists():
        new_question = random.choice(available_questions)
        avatar_num = random.randint(1, 1000)
        new_dialog = Dialog.objects.create(
            user=user,
            question=new_question,
            is_multi_step=new_question.is_multi_step,
            client_avatar=f'https://api.dicebear.com/8.x/pixel-art/png?seed={avatar_num}'
        )
        Message.objects.create(dialog=new_dialog, sender=None, text=new_question.text)

    return JsonResponse({
        'status': 'ok',
        'continue_dialog': False,
        'message': operator_message.text,
        'timestamp': timezone.localtime(operator_message.timestamp).strftime("%H:%M"),
        'completion_message': completion_message.text,
        'completion_timestamp': timezone.localtime(completion_message.timestamp).strftime("%H:%M"),
        'new_dialog_id': new_dialog.id if new_dialog else None,
        'no_more_questions': not available_questions.exists(),
        'dialogs': get_dialogs_data_for_user(user)
    })

def get_dialogs_data_for_user(user):
    return [{
        'id': d.id,
        'last_message': d.messages.last().text if d.messages.exists() else '',
        'unread_count': d.unread_count,
        'client_avatar': d.client_avatar
    } for d in Dialog.objects.filter(user=user, is_closed=False)]


@login_required
@require_POST
def get_dialog_data(request):
    if request.method == 'POST':
        try:
            dialog_id = request.POST.get('dialog_id')
            dialog = Dialog.objects.filter(user=request.user, id=dialog_id, is_closed=False).first()
            if not dialog:
                return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)

            question = dialog.question
            messages = [{
                'text': msg.text,
                'sender': 'operator' if msg.sender else 'client',
                'timestamp': timezone.localtime(msg.timestamp).strftime("%H:%M"),
                'admin_comment': msg.admin_comment if msg.admin_comment else ''
            } for msg in dialog.messages.all()]
            dialogs_data = get_dialogs_data_for_user(request.user)
            
            return JsonResponse({
                'status': 'ok',
                'messages': messages,
                'dialogs': dialogs_data,
                'is_multi_step': dialog.is_multi_step,
                'current_step': dialog.current_step,
                'max_steps': question.max_steps if question else 1,
                'admin_comment': dialog.messages.filter(admin_comment__isnull=False).first().admin_comment if dialog.messages.filter(admin_comment__isnull=False).exists() else "",
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
                dialog.save()
                return JsonResponse({'status': 'ok'})
            return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)
        except Exception as e:
            logger.error(f"Ошибка закрытия диалога: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Это тестовый комментарий для проверки Git.