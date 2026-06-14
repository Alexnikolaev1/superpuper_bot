import logging

import httpx

from services import openrouter_service, together_service

logger = logging.getLogger(__name__)

_FALLBACK_STATUSES = {404, 429, 500, 502, 503, 504}


def _should_fallback(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _FALLBACK_STATUSES
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


async def chat_completion(
    messages: list[dict],
    model_key: str = "deepseek",
    *,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    allow_fallback: bool = True,
) -> str:
    if model_key == "openrouter":
        return await openrouter_service.chat_completion(
            messages=messages,
            model_key="smart",
            max_tokens=max_tokens,
        )

    try:
        return await together_service.chat_completion(
            messages=messages,
            model_key=model_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:
        if not allow_fallback or not _should_fallback(exc):
            raise
        logger.warning("Together.ai unavailable (%s), falling back to OpenRouter", exc)
        return await openrouter_service.chat_completion(
            messages=messages,
            model_key="smart",
            max_tokens=max_tokens,
        )
