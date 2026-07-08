import re
import urllib.error
import urllib.request

from django.conf import settings


def fetch_knowledge_base_context(url: str | None = None, limit: int = 4000) -> str:
    source_url = url or settings.KNOWLEDGE_BASE_URL
    if not source_url:
        return ""

    request = urllib.request.Request(
        source_url,
        headers={'User-Agent': 'operator-trainer/1.0'},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw_html = response.read().decode('utf-8', errors='ignore')
    except (urllib.error.URLError, ValueError):
        return ""

    text = re.sub(r'<script[\s\S]*?</script>', ' ', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'<style[\s\S]*?</style>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]
