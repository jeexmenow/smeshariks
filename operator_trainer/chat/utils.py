import re
from typing import Iterable

from .models import Dialog, Message, ScenarioStep


STOP_WORDS = {
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то',
    'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за',
    'бы', 'по', 'только', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет',
    'о', 'из', 'если', 'или', 'для', 'мы', 'их', 'чем', 'без', 'кто', 'это',
}


def extract_keywords_from_message(message: str) -> list[str]:
    clean_message = re.sub(r'[^\w\s]', '', message.lower())
    words = clean_message.split()
    return [word for word in words if word not in STOP_WORDS and len(word) > 2]


def analyze_operator_message(message: str, steps: Iterable[ScenarioStep]) -> ScenarioStep | None:
    message_lower = message.lower()
    for step in steps:
        if any(keyword in message_lower for keyword in step.get_keywords_list()):
            return step
    return None


def generate_client_response(current_step: ScenarioStep | None) -> str:
    if not current_step:
        return "Спасибо, я понял. Буду ждать решения."
    return current_step.client_message


def should_continue_dialog(dialog: Dialog) -> bool:
    if dialog.is_completed or dialog.is_closed or not dialog.scenario:
        return False
    return dialog.scenario.steps.filter(step_number=dialog.current_step).exists()


def get_dialog_context(dialog: Dialog) -> dict:
    messages = list(dialog.messages.all())
    return {
        'operator_messages': [msg.text for msg in messages if msg.role == Message.ROLE_OPERATOR or msg.sender_id],
        'client_messages': [msg.text for msg in messages if msg.role in {Message.ROLE_CLIENT, Message.ROLE_AI}],
        'system_messages': [msg.text for msg in messages if msg.role == Message.ROLE_SYSTEM],
        'current_step': dialog.current_step,
        'total_messages': len(messages),
        'scenario': dialog.scenario.title if dialog.scenario else None,
    }


def find_matching_step(operator_message: str, dialog: Dialog) -> ScenarioStep | None:
    if not dialog.scenario:
        return None
    return analyze_operator_message(operator_message, dialog.scenario.steps.order_by('step_number'))
