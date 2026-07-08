# Тренажер операторов с AI-ready архитектурой

Проект переработан в учебную среду для операторов-стажеров. Стажер общается с локальным сценарным клиентом в интерфейсе, близком к операторским чатам Talkme: список диалогов, история сообщений, карточка клиента, цель кейса, подсказки и автооценка ответа.

Внешняя LLM пока не подключена намеренно. Вместо этого добавлен сервисный слой `client_engine`, который работает по сценариям и уже имеет понятную точку расширения для будущего AI-клиента.

## Возможности

- Авторизация стажеров и администраторов.
- Talkme-like рабочее окно оператора: диалоги слева, чат в центре, карточка сценария справа.
- Сценарии клиентов с шагами, подсказками, критериями и ключевыми словами.
- Локальная генерация ответов клиента без внешних API.
- Автооценка ответа оператора по критериям шага.
- Админка для управления сценариями, шагами, диалогами, сообщениями и оценками.
- Seed-команда с демонстрационными учебными кейсами.
- Архитектура, готовая к будущей AI-интеграции через отдельный provider/adapter.

## Стек

- Python 3.11+
- Django 5.2
- SQLite для локальной разработки
- Django templates
- Vanilla JavaScript
- CSS без frontend build-step

## Быстрый запуск

```bash
cd operator_trainer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_scenarios
python manage.py createsuperuser
python manage.py runserver
```

Откройте `http://127.0.0.1:8000/`.

## Настройки окружения

Можно оставить dev-defaults или переопределить:

```bash
set DJANGO_SECRET_KEY=change-me
set DJANGO_DEBUG=True
set DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
set AI_CLIENT_ENABLED=True
set AI_CLIENT_API_KEY=your-token
set AI_CLIENT_BASE_URL=https://api.openai.com/v1
set AI_CLIENT_MODEL=gpt-4o-mini
set KNOWLEDGE_BASE_URL=https://df11ef6.platrum.ru/wiki/space/dlya-operatorov
```

## Основная структура

```text
operator_trainer/
├── chat/
│   ├── management/commands/seed_scenarios.py
│   ├── services/
│   │   ├── client_engine.py
│   │   └── evaluator.py
│   ├── static/chat/
│   │   ├── css/style.css
│   │   └── js/script.js
│   ├── templates/chat/
│   ├── admin.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── operator_trainer/settings.py
└── manage.py
```

## Как устроен сценарий

Администратор создает `Scenario` и набор `ScenarioStep`.

- `Scenario.initial_message` отображается первым сообщением клиента.
- Текущий `ScenarioStep` описывает ожидаемый ответ оператора.
- `ScenarioStep.keywords` используются для локальной автооценки.
- `ScenarioStep.client_message` отправляется клиентом после ответа стажера.
- `ScenarioStep.is_final` завершает тренировочный диалог.

## Будущая AI-интеграция

Подключение LLM лучше делать не во `views.py`, а через сервисный слой. Уже подготовлены:

- `chat/services/ai_client.py` — OpenAI-compatible клиент, читает токен из `AI_CLIENT_API_KEY`.
- `chat/services/knowledge_base.py` — загрузчик контекста базы знаний.
- `chat/services/prompts.py` — промпты для роли клиента и оценки ответа оператора.

Токен не хранится в репозитории. Его нужно передавать через переменные окружения.

## Проверки

```bash
cd operator_trainer
python manage.py test
```
