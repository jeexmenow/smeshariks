from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
        avatar = models.URLField(default='https://i.pravatar.cc/150?img=3')
        is_trainer = models.BooleanField(default=False)

        def __str__(self):
            return self.username

class Question(models.Model):
    text = models.TextField("Текст вопроса")
    created_at = models.DateTimeField(auto_now_add=True)

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

    class Meta:
        ordering = ['timestamp']