import base64
import logging

import httpx

from config import config
from services.http_client import request_with_retry

logger = logging.getLogger(__name__)

TOGETHER_BASE = "https://api.together.xyz/v1"

MODELS = {
    "deepseek": "deepseek-ai/DeepSeek-V4-Pro",
    "llama": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "qwen": "Qwen/Qwen2.5-72B-Instruct-Turbo",
}

IMAGE_MODELS = {
    "flux_schnell": "black-forest-labs/FLUX.1-schnell",
    "flux_dev": "black-forest-labs/FLUX.2-dev",
    "sdxl": "stabilityai/stable-diffusion-xl-base-1.0",
}

IMAGE_STEPS = {
    "flux_schnell": 4,
    "flux_dev": 28,
    "sdxl": 30,
}

HEADERS = {
    "Authorization": f"Bearer {config.TOGETHER_API_KEY}",
    "Content-Type": "application/json",
}


def _normalize_dimensions(width: int, height: int) -> tuple[int, int]:
    """FLUX требует размеры кратные 64, в пределах 256–1024."""
    def _snap(value: int) -> int:
        value = max(256, min(1024, value))
        return round(value / 64) * 64

    return _snap(width), _snap(height)


def _extract_image_bytes(data: dict) -> bytes:
    items = data.get("data") or []
    if not items:
        raise RuntimeError(f"Together: empty image response: {data}")

    item = items[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])

    if item.get("url"):
        import asyncio
        from services.http_client import get_client

        async def _download():
            client = get_client()
            resp = await client.get(item["url"], timeout=120)
            resp.raise_for_status()
            return resp.content

        return asyncio.get_event_loop().run_until_complete(_download())

    raise RuntimeError(f"Together: unexpected image format: {item}")


async def chat_completion(
    messages: list[dict],
    model_key: str = "deepseek",
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    model = MODELS.get(model_key, MODELS["deepseek"])
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    resp = await request_with_retry(
        "POST",
        f"{TOGETHER_BASE}/chat/completions",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def generate_image(
    prompt: str,
    model_key: str = "flux_schnell",
    width: int = 1024,
    height: int = 1024,
    steps: int | None = None,
) -> bytes:
    model = IMAGE_MODELS.get(model_key, IMAGE_MODELS["flux_schnell"])
    width, height = _normalize_dimensions(width, height)
    steps = steps or IMAGE_STEPS.get(model_key, 4)

    payload = {
        "model": model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "n": 1,
        "response_format": "base64",
    }

    try:
        resp = await request_with_retry(
            "POST",
            f"{TOGETHER_BASE}/images/generations",
            headers=HEADERS,
            json=payload,
            timeout=120,
        )
        data = resp.json()
        items = data.get("data") or []
        if not items:
            raise RuntimeError(f"Together: empty image response: {data}")
        b64 = items[0].get("b64_json")
        if not b64:
            raise RuntimeError(f"Together: no image data: {items[0]}")
        return base64.b64decode(b64)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300]
        logger.error("Together image error %s: %s", exc.response.status_code, detail)
        raise RuntimeError(f"Image API error: {detail}") from exc
