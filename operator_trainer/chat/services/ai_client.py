import json
import urllib.error
import urllib.request

from django.conf import settings


class AIClientError(RuntimeError):
    pass


class AIClientNotConfigured(AIClientError):
    pass


def is_ai_enabled() -> bool:
    config = settings.AI_CLIENT
    return bool(config['ENABLED'] and config['API_KEY'])


def chat_completion(messages: list[dict], temperature: float = 0.4) -> str:
    config = settings.AI_CLIENT
    if not is_ai_enabled():
        raise AIClientNotConfigured("AI client is disabled or AI_CLIENT_API_KEY is empty.")

    endpoint = config['BASE_URL'].rstrip('/') + '/chat/completions'
    payload = {
        'model': config['MODEL'],
        'messages': messages,
        'temperature': temperature,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f"Bearer {config['API_KEY']}",
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=config['TIMEOUT']) as response:
            data = json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as exc:
        raise AIClientError(f"AI request failed: {exc}") from exc

    try:
        return data['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AIClientError("AI response has unexpected format.") from exc
