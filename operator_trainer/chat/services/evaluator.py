import re
from dataclasses import dataclass

from chat.models import Evaluation, Message, ScenarioStep


@dataclass
class EvaluationResult:
    score: int
    max_score: int
    matched_keywords: list[str]
    missed_keywords: list[str]
    feedback: str


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower()).strip()


def evaluate_operator_message(message: Message, step: ScenarioStep | None) -> EvaluationResult:
    if not step:
        return EvaluationResult(
            score=50,
            max_score=100,
            matched_keywords=[],
            missed_keywords=[],
            feedback="Ответ сохранен. Для этого шага нет настроенных критериев оценки.",
        )

    expected = step.get_keywords_list()
    text = normalize_text(message.text)
    matched = [keyword for keyword in expected if keyword in text]
    missed = [keyword for keyword in expected if keyword not in text]

    if expected:
        score = round(len(matched) / len(expected) * 100)
    else:
        score = 80 if len(text) >= 20 else 50

    return EvaluationResult(
        score=score,
        max_score=100,
        matched_keywords=matched,
        missed_keywords=missed,
        feedback="",
    )


def persist_evaluation(message: Message, step: ScenarioStep | None) -> Evaluation:
    result = evaluate_operator_message(message, step)
    message.score = result.score
    message.is_correct = result.score >= 70
    message.metadata = {
        **message.metadata,
        "evaluation_feedback": result.feedback,
        "matched_keywords": result.matched_keywords,
        "missed_keywords": result.missed_keywords,
    }
    message.save(update_fields=['score', 'is_correct', 'metadata'])

    return Evaluation.objects.create(
        dialog=message.dialog,
        message=message,
        scenario_step=step,
        score=result.score,
        max_score=result.max_score,
        matched_keywords=result.matched_keywords,
        missed_keywords=result.missed_keywords,
        feedback=result.feedback,
    )
