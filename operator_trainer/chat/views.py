from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime
import random, logging
from .forms import RegisterForm, LoginForm
from django.http import JsonResponse
from .models import Dialog, Message, CustomUser

DIALOGS = {
    "Клиент: Здравствуйте, у меня проблема с заказом.": [
        "Оператор: Здравствуйте! Пришлите, пожалуйста, ваш номер заказа. Проверим! (далее скрипт проверили ваш заказ)",
        "Оператор: Здравствуйте! Уточните, пожалуйста, детальнее, в чём конкретно возникает проблема?",
        "Другие варианты могут быть тут."
    ],
    "Клиент: Привет. Заказ до сих пор не активировался, что делать?": [
        "Оператор: Здравствуйте! Приношу извинения. Пришлите, пожалуйста, ваш номер заказа. Проверим!",
        "Оператор: Здравствуйте! Уточните, пожалуйста, номер заказа.",
        "Другие варианты могут быть тут."
    ],

    "Клиент: Привет! У меня прокси Германии, а показывает ОАЭ. Что делать? ": [
        "Оператор: Здравствуйте! Пришлите, пожалуйста, скриншот некорректной геолокации и ваш номер заказа. Проверим!",
        "Оператор: Здравствуйте! Уточните, пожалуйста, номер заказа.",
        "Другие варианты могут быть тут."
    ]
}


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
        'avatar': 'https://i.pravatar.cc/150?img=5',
        'status': 'online'
    }

    if request.method == 'POST':
        user_answer = request.POST.get("user_answer")
        client_message = request.session.get('current_question', '')

        # Получаем текущий активный диалог или создаем новый
        dialog, created = Dialog.objects.get_or_create(
            user=request.user,
            is_completed=False,
            defaults={'user': request.user}
        )

        # Сохраняем сообщение клиента (если еще не сохранено)
        if created or not Message.objects.filter(dialog=dialog, text=client_message).exists():
            Message.objects.create(
                dialog=dialog,
                sender=None,  # None = сообщение от клиента (не от пользователя)
                text=client_message
            )

        # Сохраняем ответ пользователя (оператора)
        Message.objects.create(
            dialog=dialog,
            sender=request.user,  # Ответ от текущего пользователя
            text=f"Оператор: {user_answer}"
        )

        return render(request, 'chat/index.html', {
            'client_message': client_message,
            'user_answer': f"Оператор: {user_answer}",
            'hints': DIALOGS.get(client_message, []),
            'current_time': current_time,
            'client_data': client_data,
            'user': request.user
        })

    # Если GET-запрос (начало нового диалога)
    current_question = random.choice(list(DIALOGS.keys()))
    request.session['current_question'] = current_question

    # Закрываем предыдущий диалог (если был незавершенный)
    Dialog.objects.filter(user=request.user, is_completed=False).update(is_completed=True)

    # Создаем новый диалог
    dialog = Dialog.objects.create(user=request.user)

    # Сохраняем первый вопрос клиента
    Message.objects.create(
        dialog=dialog,
        sender=None,  # None = сообщение от клиента
        text=current_question
    )

    return render(request, 'chat/index.html', {
        'client_message': current_question,
        'current_time': current_time,
        'client_data': client_data,
        'user': request.user
    })

logger = logging.getLogger(__name__)


def send_message(request):
    if request.method == 'POST':
        logger.info(f"Получено сообщение: {request.POST}")
        try:
            user = request.user
            text = request.POST.get('text', '')

            dialog = Dialog.objects.filter(user=user, is_completed=False).first()
            if not dialog:
                dialog = Dialog.objects.create(user=user)
                logger.info(f"Создан новый диалог: {dialog.id}")

            msg = Message.objects.create(
                dialog=dialog,
                sender=user,
                text=text
            )
            logger.info(f"Создано сообщение ID {msg.id} в диалоге {dialog.id}")

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}")
            return JsonResponse({'status': 'error'}, status=500)