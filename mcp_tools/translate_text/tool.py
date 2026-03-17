"""Translate text between languages using a translation API."""

import json

try:
    import requests
except ImportError:
    requests = None


def run(
    text: str,
    target_language: str,
    api_key: str,
    source_language: str = "auto",
    api_url: str = "https://libretranslate.com/translate",
) -> str:
    """Translate text from one language to another.

    Uses a LibreTranslate-compatible API endpoint.

    @param text: The text to translate.
    @param target_language: ISO 639-1 target language code (e.g. 'es').
    @param api_key: API key for the translation service.
    @param source_language: ISO 639-1 source language code, or 'auto' for detection.
    @param api_url: Translation API endpoint URL (default: LibreTranslate).
    @returns JSON string with translated text and detected source language.
    @throws ValueError: If api_key is not provided.
    @throws RuntimeError: If translation fails.
    """
    if requests is None:
        return "error: " + "The 'requests' package is required. Install it with: pip install requests"

    if not api_key:
        raise ValueError("api_key is required")

    payload = {
        "q": text,
        "source": source_language,
        "target": target_language,
        "api_key": api_key,
    }

    response = requests.post(api_url, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"Translation failed: {data['error']}")

    return json.dumps({
        "source_language": data.get("detectedLanguage", {}).get("language", source_language),
        "target_language": target_language,
        "original": text,
        "translated": data.get("translatedText", ""),
    }, indent=2)
