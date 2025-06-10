from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    avatar = models.URLField(default='https://i.pravatar.cc/150?img=15')
    is_trainer = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class Question(models.Model):
    text = models.TextField("Текст вопроса")
    created_at = models.DateTimeField(auto_now_add=True)
    hints = models.TextField("Подсказки", blank=True, help_text="Через запятую, например: Подсказка 1, Подсказка 2")
    client_responses = models.TextField(
        "Варианты ответов клиента",
        blank=True,
        help_text="Через запятую, например: Ответ 1, Ответ 2. Если пусто, будут использованы стандартные ответы."
    )

    def get_hints_list(self):
        return [h.strip() for h in self.hints.split(',') if h.strip()] if self.hints else []

    def get_client_responses_list(self):
        if self.client_responses:
            return [r.strip() for r in self.client_responses.split(',') if r.strip()]
        return [
            "Спасибо за помощь!",
            "Понял, спасибо!",
            "Благодарю за разъяснение!",
            "Ясно, буду знать!",
            "Отлично, теперь всё понятно!"
        ]

    def __str__(self):
        return f"Вопрос #{self.id}"


class UserResponse(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Пользователь")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Вопрос")
    answer = models.TextField("Ответ пользователя")
    is_correct = models.BooleanField("Правильный ответ", null=True, blank=True)
    feedback = models.TextField("Комментарий оператора", blank=True)
    created_at = models.DateTimeField("Дата ответа", auto_now_add=True)
    updated_at = models.DateTimeField("Дата проверки", auto_now=True)

    class Meta:
        verbose_name = "Ответ пользователя"
        verbose_name_plural = "Ответы пользователей"
        ordering = ['-created_at']

    def __str__(self):
        return f"Ответ {self.user.username} на вопрос #{self.question.id}"


class Dialog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='dialogs')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    unread_count = models.IntegerField(default=0, help_text="Количество непрочитанных сообщений")
    client_avatar = models.URLField(default='https://i.pravatar.cc/150?img={random.randint(1, 20)}', help_text="Уникальная аватарка клиента")
    is_closed = models.BooleanField(default=False, help_text="Диалог закрыт и скрыт из чата")

    def __str__(self):
        return f"Диалог с {self.user.username} (ID: {self.id})"

    def get_last_message(self):
        return self.messages.last().text if self.messages.exists() else ""


class Message(models.Model):
    dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_correct = models.BooleanField(null=True, blank=True)
    admin_comment = models.TextField(blank=True)
    is_read = models.BooleanField(default=False, help_text="Прочитано ли сообщение")

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Сообщение в диалоге {self.dialog.id} от {self.sender or 'Клиент'}"