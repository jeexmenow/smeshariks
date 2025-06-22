import re
from typing import List, Optional, Tuple
from .models import DialogStep, Question


def analyze_operator_message(message: str, dialog_steps: List[DialogStep]) -> Optional[DialogStep]:
    # анализирует сообщение оператора и возвращает следующий шаг диалога
    message_lower = message.lower()
    
    for step in dialog_steps:
        keywords = step.get_trigger_keywords_list()
        for keyword in keywords:
            if keyword in message_lower:
                return step
    
    return None


def generate_client_response(operator_message: str, current_step: DialogStep, question: Question) -> str:

    # генерирует ответ клиента на основе сообщения оператора и текущего шага
    if current_step.client_follow_up:
        return current_step.client_follow_up
    
    # проверяем, содержит ли сообщение оператора ожидаемые ключевые слова
    if current_step.expected_operator_response:
        expected_lower = current_step.expected_operator_response.lower()
        message_lower = operator_message.lower()
        
        # если оператор дал ожидаемый ответ, переходим к следующему шагу
        if any(keyword in message_lower for keyword in expected_lower.split()):
            return current_step.client_message
    
    # если нет специального follow-up, возвращаем стандартное сообщение шага
    return current_step.client_message


def should_continue_dialog(dialog, question: Question) -> bool:

    # определяет, должен ли диалог продолжаться

    if not question.is_multi_step:
        return False
    
    if dialog.current_step >= dialog.max_steps:
        return False
    
    # проверяем, есть ли еще шаги для этого вопроса
    next_step = DialogStep.objects.filter(
        question=question,
        step_number=dialog.current_step + 1
    ).first()
    
    return next_step is not None


def get_dialog_context(dialog) -> dict:
    messages = dialog.messages.all()
    operator_messages = [msg.text for msg in messages if msg.sender]
    client_messages = [msg.text for msg in messages if not msg.sender]
    
    return {
        'operator_messages': operator_messages,
        'client_messages': client_messages,
        'current_step': dialog.current_step,
        'total_messages': len(messages)
    }


def extract_keywords_from_message(message: str) -> List[str]:
    # убираем знаки препинания и приводим к нижнему регистру
    clean_message = re.sub(r'[^\w\s]', '', message.lower())
    words = clean_message.split()
    
    # фильтруем стоп-слова (можно расширить список)
    stop_words = {'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'притом', 'будет', 'очень', 'мой', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'притом', 'будет', 'очень'}
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    return keywords


def find_matching_step(operator_message: str, question: Question, current_step: int) -> Optional[DialogStep]:
    # получаем все шаги для этого вопроса
    dialog_steps = DialogStep.objects.filter(question=question).order_by('step_number')
    
    # ищем шаг, который соответствует текущему номеру шага
    for step in dialog_steps:
        if step.step_number == current_step:
            # проверяем, подходит ли сообщение оператора для этого шага
            keywords = step.get_trigger_keywords_list()
            message_lower = operator_message.lower()
            
            for keyword in keywords:
                if keyword in message_lower:
                    return step
    
    return None 