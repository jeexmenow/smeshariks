from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    avatar = models.URLField(default='https://github.com/identicons/default.png')
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
    is_multi_step = models.BooleanField("Многошаговый", default=False, help_text="Активируйте, если у вопроса несколько шагов")
    max_steps = models.IntegerField("Макс. шагов", default=1, help_text="Количество шагов в этом вопросе (для многошаговых диалогов)")
    stop_words = models.CharField(max_length=255, blank=True, help_text="Стоп-слова для завершения диалога, через запятую")

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


class Scenario(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Легкий'),
        ('medium', 'Средний'),
        ('hard', 'Сложный'),
    ]

    title = models.CharField("Название кейса", max_length=180)
    client_name = models.CharField("Имя клиента", max_length=120, default="Клиент")
    client_status = models.CharField("Статус клиента", max_length=120, default="online")
    client_avatar = models.URLField("Аватар клиента", blank=True)
    situation = models.TextField("Ситуация клиента", blank=True)
    goal = models.TextField("Цель оператора", blank=True)
    initial_message = models.TextField("Первое сообщение клиента")
    hints = models.TextField("Подсказки", blank=True, help_text="Каждая подсказка с новой строки")
    knowledge_base_url = models.URLField("Ссылка на базу знаний", blank=True)
    difficulty = models.CharField("Сложность", max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    is_active = models.BooleanField("Активен", default=True)
    stop_words = models.CharField("Стоп-слова", max_length=255, blank=True, help_text="Через запятую")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Сценарий"
        verbose_name_plural = "Сценарии"
        ordering = ['title']

    def get_hints_list(self):
        return [hint.strip() for hint in self.hints.splitlines() if hint.strip()]

    def get_stop_words_list(self):
        return [word.strip().lower() for word in self.stop_words.split(',') if word.strip()]

    def total_steps(self):
        return max(self.steps.count(), 1)

    def __str__(self):
        return self.title


class ScenarioStep(models.Model):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='steps')
    step_number = models.PositiveIntegerField("Номер шага")
    client_message = models.TextField("Ответ клиента")
    expected_operator_response = models.TextField("Ожидаемое действие оператора", blank=True)
    evaluation_criteria = models.TextField(
        "Критерии оценки",
        blank=True,
        help_text="Каждый критерий с новой строки: приветствие, уточнение проблемы, решение"
    )
    keywords = models.TextField("Ключевые слова", blank=True, help_text="Через запятую")
    hint = models.TextField("Подсказка к шагу", blank=True)
    is_final = models.BooleanField("Финальный шаг", default=False)

    class Meta:
        verbose_name = "Шаг сценария"
        verbose_name_plural = "Шаги сценария"
        ordering = ['step_number']
        unique_together = ('scenario', 'step_number')

    def get_keywords_list(self):
        return [keyword.strip().lower() for keyword in self.keywords.split(',') if keyword.strip()]

    def get_criteria_list(self):
        return [criterion.strip() for criterion in self.evaluation_criteria.splitlines() if criterion.strip()]

    def __str__(self):
        return f"{self.scenario.title}: шаг {self.step_number}"


class UserResponse(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Пользователь")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Вопрос")
    scenario = models.ForeignKey(Scenario, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Сценарий")
    dialog = models.ForeignKey('Dialog', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Диалог")
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


class DialogStep(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='steps')
    step_number = models.PositiveIntegerField("Номер шага")
    trigger_keywords = models.TextField("Триггерные слова", blank=True, help_text="Ключевые слова клиента для этого шага (через запятую).")
    client_message = models.TextField("Сообщение клиента", help_text="Точное сообщение, которое отправит клиент на этом шаге.")
    expected_operator_response = models.TextField("Ожидаемый ответ оператора", blank=True, help_text="Правильный ответ, который должен дать оператор.")
    response_variation = models.TextField("Вариации ответа", blank=True, help_text="Допустимые вариации ответа оператора (через точку с запятой).")

    class Meta:
        ordering = ['step_number']
        unique_together = ('question', 'step_number')

    def __str__(self):
        return f"Шаг {self.step_number} для вопроса #{self.question.id}"


class Dialog(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Активен'),
        (STATUS_COMPLETED, 'Завершен'),
        (STATUS_CLOSED, 'Закрыт'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='dialogs')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='dialogs', null=True, blank=True)
    scenario = models.ForeignKey(Scenario, on_delete=models.SET_NULL, related_name='dialogs', null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    unread_count = models.IntegerField(default=0, help_text="Количество непрочитанных сообщений")
    client_avatar = models.URLField(default='https://i.pravatar.cc/150?img={random.randint(1, 20)}', help_text="Уникальная аватарка клиента")
    is_closed = models.BooleanField(default=False, help_text="Диалог закрыт и скрыт из чата")
    is_multi_step = models.BooleanField(default=False, help_text="Это многошаговый диалог?")
    current_step = models.IntegerField(default=1, help_text="Текущий шаг в многошаговом диалоге")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    client_name = models.CharField(max_length=120, default="Клиент")
    ai_mode = models.CharField(max_length=40, default="scenario", help_text="Зарезервировано для будущей AI-интеграции")
    score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Диалог с {self.user.username} (ID: {self.id})"

    def get_last_message(self):
        return self.messages.last().text if self.messages.exists() else ""

    def get_training_title(self):
        if self.scenario:
            return self.scenario.title
        if self.question:
            return str(self.question)
        return f"Диалог #{self.id}"

    def get_max_steps(self):
        if self.scenario:
            return self.scenario.total_steps()
        if self.question:
            return self.question.max_steps
        return 1

    @property
    def needs_operator_response(self):
        has_client_message = self.messages.filter(role__in=[Message.ROLE_CLIENT, Message.ROLE_AI]).exists()
        has_operator_message = self.messages.filter(role=Message.ROLE_OPERATOR).exists()
        return has_client_message and not has_operator_message


class Message(models.Model):
    ROLE_CLIENT = 'client'
    ROLE_OPERATOR = 'operator'
    ROLE_SYSTEM = 'system'
    ROLE_AI = 'ai'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_CLIENT, 'Клиент'),
        (ROLE_OPERATOR, 'Оператор'),
        (ROLE_SYSTEM, 'Система'),
        (ROLE_AI, 'AI-клиент'),
        (ROLE_ADMIN, 'Администратор'),
    ]

    dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_correct = models.BooleanField(null=True, blank=True)
    admin_comment = models.TextField(blank=True)
    is_read = models.BooleanField(default=False, help_text="Прочитано ли сообщение")
    score = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Сообщение в диалоге {self.dialog.id} от {self.sender or self.get_role_display()}"


class ResponseTemplate(models.Model):
    title = models.CharField("Название", max_length=255)
    category = models.CharField("Категория", max_length=120, blank=True)
    keywords = models.TextField("Ключевые слова", blank=True)
    text = models.TextField("Текст шаблона")
    html = models.TextField("HTML шаблон", blank=True)
    source = models.CharField("Источник", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Шаблон ответа"
        verbose_name_plural = "Шаблоны ответов"
        ordering = ['category', 'title']

    def __str__(self):
        return self.title


class Evaluation(models.Model):
    dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE, related_name='evaluations')
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='evaluation')
    scenario_step = models.ForeignKey(ScenarioStep, on_delete=models.SET_NULL, null=True, blank=True)
    score = models.PositiveIntegerField("Оценка", default=0)
    max_score = models.PositiveIntegerField("Максимум", default=100)
    matched_keywords = models.JSONField("Найденные критерии", default=list, blank=True)
    missed_keywords = models.JSONField("Пропущенные критерии", default=list, blank=True)
    feedback = models.TextField("Обратная связь", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Оценка ответа"
        verbose_name_plural = "Оценки ответов"
        ordering = ['-created_at']

    @property
    def percent(self):
        if not self.max_score:
            return 0
        return round(self.score / self.max_score * 100)

    def __str__(self):
        return f"Оценка {self.score}/{self.max_score} для диалога #{self.dialog_id}"