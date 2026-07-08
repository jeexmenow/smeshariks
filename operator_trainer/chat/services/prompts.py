from chat.models import Dialog, Message, ScenarioStep
from chat.services.knowledge_base import fetch_knowledge_base_context


def _dialog_history(dialog: Dialog) -> str:
    lines = []
    for message in dialog.messages.order_by('timestamp'):
        if message.role == Message.ROLE_OPERATOR or message.sender_id:
            role = 'Оператор'
        elif message.role == Message.ROLE_SYSTEM:
            role = 'Система'
        else:
            role = 'Клиент'
        lines.append(f"{role}: {message.text}")
    return "\n".join(lines)


def build_ai_client_messages(dialog: Dialog, operator_message: str) -> list[dict]:
    scenario = dialog.scenario
    knowledge_base = fetch_knowledge_base_context(scenario.knowledge_base_url if scenario else None)
    system_prompt = (
        "Ты играешь роль реального клиента в тренажере операторов поддержки PROXYS.IO. "
        "Отвечай естественно, коротко и в рамках ситуации. Не подсказывай оператору напрямую. "
        "Если оператор решил проблему, подтверди это как клиент."
    )
    user_prompt = (
        f"Ситуация клиента: {scenario.situation if scenario else 'Тренировочный диалог'}\n"
        f"Цель оператора: {scenario.goal if scenario else ''}\n"
        f"База знаний:\n{knowledge_base or 'Контекст базы знаний пока недоступен.'}\n\n"
        f"История диалога:\n{_dialog_history(dialog)}\n\n"
        f"Последний ответ оператора: {operator_message}\n"
        "Сформулируй следующий ответ клиента."
    )
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]


def build_evaluation_messages(dialog: Dialog, message: Message, step: ScenarioStep | None) -> list[dict]:
    scenario = dialog.scenario
    knowledge_base = fetch_knowledge_base_context(scenario.knowledge_base_url if scenario else None)
    criteria = "\n".join(step.get_criteria_list()) if step else "Оцени корректность, полноту, тон и следование базе знаний."
    system_prompt = (
        "Ты оцениваешь ответ оператора в учебном тренажере. "
        "Верни JSON с полями score от 0 до 100, feedback для администратора и short_reason."
    )
    user_prompt = (
        f"Ситуация: {scenario.situation if scenario else ''}\n"
        f"Критерии:\n{criteria}\n"
        f"База знаний:\n{knowledge_base or 'Контекст базы знаний пока недоступен.'}\n\n"
        f"История диалога:\n{_dialog_history(dialog)}\n\n"
        f"Оцени ответ оператора: {message.text}"
    )
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]
