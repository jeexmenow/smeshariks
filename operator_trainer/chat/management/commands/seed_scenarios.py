from django.core.management.base import BaseCommand

from chat.models import Scenario, ScenarioStep


SCENARIOS = [
    {
        "title": "Клиент не может войти в личный кабинет",
        "client_name": "Иван Петров",
        "client_status": "online",
        "difficulty": "easy",
        "situation": "Клиент пишет в поддержку, потому что после ввода пароля видит ошибку авторизации.",
        "goal": "Поздороваться, уточнить детали, предложить безопасное восстановление доступа и закрыть диалог.",
        "initial_message": "Здравствуйте. Не могу войти в личный кабинет, пишет что пароль неверный, хотя я уверен, что ввожу правильно.",
        "hints": "Не просите пароль у клиента.\nУточните email или логин.\nПредложите восстановление доступа и проверку раскладки клавиатуры.",
        "stop_words": "спасибо,до свидания,всего доброго",
        "steps": [
            {
                "step_number": 1,
                "client_message": "Email тот же, доступ к почте есть. Ссылку на восстановление могу получить.",
                "expected_operator_response": "Оператор приветствует клиента, не просит пароль, уточняет логин/email и доступ к почте.",
                "keywords": "здравствуйте,пароль,email,почт",
                "evaluation_criteria": "Приветствие\nБезопасность\nУточнение данных",
                "hint": "Начните с приветствия и не запрашивайте пароль.",
            },
            {
                "step_number": 2,
                "client_message": "Понял, попробую восстановить. А если письмо не придет?",
                "expected_operator_response": "Оператор объясняет восстановление, проверку спама и повторную отправку письма.",
                "keywords": "восстанов,спам,письмо,повтор",
                "evaluation_criteria": "Инструкция\nАльтернативный путь\nСпокойный тон",
                "hint": "Дайте короткую пошаговую инструкцию.",
            },
            {
                "step_number": 3,
                "client_message": "Хорошо, спасибо. Теперь понятно, что делать.",
                "expected_operator_response": "Оператор резюмирует решение и корректно завершает диалог.",
                "keywords": "проверьте,если,помогу,обращайтесь",
                "evaluation_criteria": "Резюме\nГотовность помочь\nЗавершение",
                "hint": "Завершите диалог доброжелательно.",
                "is_final": True,
            },
        ],
    },
    {
        "title": "Клиент недоволен задержкой ответа",
        "client_name": "Мария Смирнова",
        "client_status": "online",
        "difficulty": "medium",
        "situation": "Клиент раздражен долгим ожиданием и хочет понять, почему вопрос не решен.",
        "goal": "Снизить напряжение, признать ожидание, уточнить проблему и предложить следующий шаг.",
        "initial_message": "Я уже третий раз пишу. Почему мне никто нормально не отвечает?",
        "hints": "Сначала признайте эмоцию клиента.\nНе спорьте и не перекладывайте ответственность.\nДайте понятный следующий шаг.",
        "stop_words": "спасибо,ладно,поняла",
        "steps": [
            {
                "step_number": 1,
                "client_message": "Мне важно, чтобы вопрос наконец решили, а не просто извинились.",
                "expected_operator_response": "Оператор извиняется за ожидание, признает неудобство и просит коротко описать проблему.",
                "keywords": "извин,понима,ожидан,уточн",
                "evaluation_criteria": "Эмпатия\nПризнание ожидания\nУточняющий вопрос",
                "hint": "Сначала снизьте напряжение, затем переходите к сути.",
            },
            {
                "step_number": 2,
                "client_message": "Заказ завис в статусе обработки, деньги списали вчера.",
                "expected_operator_response": "Оператор уточняет номер заказа и обещает проверить статус оплаты/обработки.",
                "keywords": "номер,заказ,провер,оплат",
                "evaluation_criteria": "Сбор данных\nПонятное действие\nБез обещаний без проверки",
                "hint": "Не обещайте мгновенное решение, если нужна проверка.",
            },
            {
                "step_number": 3,
                "client_message": "Хорошо, номер заказа отправила. Буду ждать информацию.",
                "expected_operator_response": "Оператор фиксирует следующий шаг, срок ответа и благодарит клиента.",
                "keywords": "проверю,срок,вернусь,спасибо",
                "evaluation_criteria": "Фиксация срока\nСледующий шаг\nКорректный тон",
                "hint": "Назовите ожидаемый срок следующего ответа.",
                "is_final": True,
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Create demo training scenarios for the operator trainer."

    def handle(self, *args, **options):
        created = 0
        for item in SCENARIOS:
            data = item.copy()
            steps = data.pop("steps")
            scenario, was_created = Scenario.objects.update_or_create(
                title=data["title"],
                defaults=data,
            )
            scenario.steps.all().delete()
            for step in steps:
                ScenarioStep.objects.create(scenario=scenario, **step)
            created += int(was_created)

        self.stdout.write(self.style.SUCCESS(f"Demo scenarios are ready. Created: {created}"))
