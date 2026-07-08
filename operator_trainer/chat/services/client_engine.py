from dataclasses import dataclass

from django.utils import timezone

from chat.models import Dialog, Message, Scenario, ScenarioStep
from chat.services.evaluator import persist_evaluation


@dataclass
class ClientTurn:
    operator_message: Message
    client_message: Message | None
    completion_message: Message | None
    evaluation_feedback: str
    continue_dialog: bool


def get_current_step(dialog: Dialog) -> ScenarioStep | None:
    if not dialog.scenario:
        return None
    return dialog.scenario.steps.filter(step_number=dialog.current_step).first()


def start_dialog_for_scenario(user, scenario: Scenario) -> Dialog:
    avatar = scenario.client_avatar or f"https://api.dicebear.com/8.x/pixel-art/png?seed=scenario-{scenario.id}"
    dialog = Dialog.objects.create(
        user=user,
        scenario=scenario,
        client_name=scenario.client_name,
        client_avatar=avatar,
        is_multi_step=scenario.steps.count() > 1,
        current_step=1,
        status=Dialog.STATUS_ACTIVE,
    )
    Message.objects.create(
        dialog=dialog,
        role=Message.ROLE_CLIENT,
        sender=None,
        text=scenario.initial_message,
        metadata={"source": "scenario.initial_message"},
    )
    return dialog


def get_next_available_scenario(user) -> Scenario | None:
    completed_scenario_ids = Dialog.objects.filter(
        user=user,
        scenario__isnull=False,
        is_completed=True,
    ).values_list('scenario_id', flat=True)
    return Scenario.objects.filter(is_active=True).exclude(id__in=completed_scenario_ids).order_by('?').first()


def get_or_create_active_dialog(user) -> Dialog | None:
    dialog = Dialog.objects.filter(user=user, is_closed=False, is_completed=False).order_by('start_time').first()
    if dialog:
        return dialog

    scenario = get_next_available_scenario(user)
    if not scenario:
        return None
    return start_dialog_for_scenario(user, scenario)


def complete_dialog(dialog: Dialog, text: str = "Тренировочный диалог завершен.") -> Message:
    dialog.is_completed = True
    dialog.status = Dialog.STATUS_COMPLETED
    dialog.end_time = timezone.now()
    dialog.score = _average_score(dialog)
    dialog.save(update_fields=['is_completed', 'status', 'end_time', 'score'])
    return Message.objects.create(
        dialog=dialog,
        role=Message.ROLE_SYSTEM,
        sender=None,
        text=text,
        metadata={"event": "dialog_completed"},
    )


def _average_score(dialog: Dialog) -> int:
    evaluations = dialog.evaluations.all()
    if not evaluations.exists():
        return 0
    return round(sum(item.score for item in evaluations) / evaluations.count())


def handle_operator_turn(dialog: Dialog, text: str, user) -> ClientTurn:
    operator_message = Message.objects.create(
        dialog=dialog,
        role=Message.ROLE_OPERATOR,
        sender=user,
        text=text,
    )

    scenario = dialog.scenario
    step = get_current_step(dialog)
    evaluation = persist_evaluation(operator_message, step)

    if scenario and any(word in text.lower() for word in scenario.get_stop_words_list()):
        completion = complete_dialog(dialog, "Диалог завершен по стоп-слову оператора.")
        return ClientTurn(operator_message, None, completion, evaluation.feedback, False)

    if not scenario:
        completion = complete_dialog(dialog)
        return ClientTurn(operator_message, None, completion, evaluation.feedback, False)

    if not step:
        completion = complete_dialog(dialog, "Клиент удовлетворен. Диалог завершен.")
        return ClientTurn(operator_message, None, completion, evaluation.feedback, False)

    client_message = Message.objects.create(
        dialog=dialog,
        role=Message.ROLE_CLIENT,
        sender=None,
        text=step.client_message,
        metadata={"source": "scenario.step", "step_number": step.step_number},
    )

    next_step_number = dialog.current_step + 1
    has_next_step = scenario.steps.filter(step_number=next_step_number).exists()
    if step.is_final or not has_next_step:
        completion = complete_dialog(dialog, "Клиент удовлетворен. Диалог завершен.")
        return ClientTurn(operator_message, client_message, completion, evaluation.feedback, False)

    dialog.current_step = next_step_number
    dialog.save(update_fields=['current_step'])
    return ClientTurn(operator_message, client_message, None, evaluation.feedback, True)
