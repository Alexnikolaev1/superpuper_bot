import logging

from config import config
from services.http_client import request_with_retry

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

FREE_MODELS = {
    "default": "meta-llama/llama-3.3-8b-instruct:free",
    "smart": "deepseek/deepseek-r1:free",
    "fast": "google/gemma-3-27b-it:free",
    "creative": "mistralai/mistral-7b-instruct:free",
}

HEADERS = {
    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://t.me/contentbot_pro",
    "X-Title": "ContentBot Pro",
}


async def chat_completion(
    messages: list[dict],
    model_key: str = "smart",
    max_tokens: int = 1500,
) -> str:
    model = FREE_MODELS.get(model_key, FREE_MODELS["default"])
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    resp = await request_with_retry(
        "POST",
        f"{OPENROUTER_BASE}/chat/completions",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    data = resp.json()
    return data["choices"][0]["message"]["content"]
