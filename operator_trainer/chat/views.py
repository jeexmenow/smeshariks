from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime
import random, logging
from django.http import JsonResponse
from .forms import RegisterForm, LoginForm
from .models import Dialog, Message, CustomUser, Question, UserResponse
import string
import random as random_module
from django.utils import timezone
from django.db.models import F

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
        avatar_num = random_module.randint(1, 20)
        dialog = Dialog.objects.create(
            user=request.user,
            client_avatar=f'https://i.pravatar.cc/150?img={avatar_num}'
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
        question = Question.objects.filter(text=client_message.text).first()
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
        'client_responses': client_responses
    })


@login_required
def send_message(request):
    if request.method == 'POST':
        try:
            user = request.user
            text = request.POST.get('text', '').strip()
            dialog_id = request.POST.get('dialog_id')

            if not text:
                return JsonResponse({'status': 'error', 'message': 'Текст сообщения не может быть пустым'}, status=400)

            dialog = Dialog.objects.filter(user=user, id=dialog_id, is_closed=False).first()
            if not dialog:
                return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)

            # Сохраняем ответ оператора
            message = Message.objects.create(
                dialog=dialog,
                sender=user,
                text=f"Оператор: {text}"
            )

            # Сохраняем в UserResponse
            client_message = dialog.messages.filter(sender=None).first()
            if client_message:
                question = Question.objects.filter(text=client_message.text).first()
                if question:
                    UserResponse.objects.create(
                        user=user,
                        question=question,
                        answer=text
                    )

            # Выбираем случайный ответ клиента
            question = Question.objects.filter(text=client_message.text).first() if client_message else None
            client_responses = question.get_client_responses_list() if question else [
                "Спасибо за помощь!",
                "Понял, спасибо!",
                "Благодарю за разъяснение!",
                "Ясно, буду знать!",
                "Отлично, теперь всё понятно!"
            ]

            client_response = random.choice(client_responses)
            client_msg = Message.objects.create(
                dialog=dialog,
                sender=None,
                text=client_response
            )

            # Помечаем текущий диалог как завершенный
            dialog.is_completed = True
            dialog.end_time = timezone.now()
            dialog.save()

            # Добавляем сообщение о завершении диалога
            completion_message = Message.objects.create(
                dialog=dialog,
                sender=None,
                text="Вы молодец! Диалог завершен."
            )

            # Создаем новый диалог с новым вопросом
            new_dialog = None
            # Получаем все вопросы, на которые пользователь уже отвечал
            answered_questions = Question.objects.filter(
                userresponse__user=user
            ).distinct()

            # Получаем все доступные вопросы, исключая уже отвеченные
            available_questions = Question.objects.exclude(
                id__in=answered_questions.values_list('id', flat=True)
            )

            if available_questions.exists():
                new_question = random.choice(available_questions)
                avatar_num = random_module.randint(1, 20)
                new_dialog = Dialog.objects.create(
                    user=user,
                    client_avatar=f'https://i.pravatar.cc/150?img={avatar_num}'
                )
                Message.objects.create(
                    dialog=new_dialog,
                    sender=None,
                    text=new_question.text
                )

            return JsonResponse({
                'status': 'ok',
                'message': message.text,
                'sender': 'operator',
                'timestamp': message.timestamp.strftime("%H:%M"),
                'dialog_id': dialog.id,
                'new_dialog_id': new_dialog.id if new_dialog else None,
                'new_message': client_msg.text,
                'new_sender': 'client',
                'new_timestamp': client_msg.timestamp.strftime("%H:%M"),
                'completion_message': completion_message.text,
                'completion_timestamp': completion_message.timestamp.strftime("%H:%M"),
                'admin_comment': dialog.messages.filter(admin_comment__isnull=False).first().admin_comment
                if dialog.messages.filter(admin_comment__isnull=False).exists() else "",
                'client_responses': client_responses,
                'dialogs': [{
                    'id': d.id,
                    'last_message': d.messages.last().text if d.messages.last() else '',
                    'unread_count': d.unread_count,
                    'client_avatar': d.client_avatar
                } for d in Dialog.objects.filter(user=user, is_closed=False)],
                'no_more_questions': not available_questions.exists()
            })
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Недопустимый метод'}, status=400)

@login_required
def get_dialog_data(request):
    if request.method == 'POST':
        try:
            dialog_id = request.POST.get('dialog_id')
            dialog = Dialog.objects.filter(user=request.user, id=dialog_id, is_closed=False).first()
            if not dialog:
                return JsonResponse({'status': 'error', 'message': 'Диалог не найден'}, status=404)

            messages = [{
                'text': msg.text,
                'sender': 'operator' if msg.sender else 'client',
                'timestamp': msg.timestamp.strftime("%H:%M"),
                'admin_comment': msg.admin_comment if msg.admin_comment else ''
            } for msg in dialog.messages.all()]
            dialogs = [{
                'id': d.id,
                'last_message': d.messages.last().text if d.messages.last() else '',
                'unread_count': d.unread_count,
                'client_avatar': d.client_avatar
            } for d in Dialog.objects.filter(user=request.user, is_closed=False)]
            client_message = dialog.messages.filter(sender=None).first()
            question = Question.objects.filter(text=client_message.text).first() if client_message else None
            client_responses = question.get_client_responses_list() if question and question.client_responses else []
            return JsonResponse({
                'status': 'ok',
                'messages': messages,
                'dialogs': dialogs,
                'admin_comment': dialog.messages.filter(admin_comment__isnull=False).first().admin_comment if dialog.messages.filter(admin_comment__isnull=False).exists() else "",
                'client_responses': client_responses
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