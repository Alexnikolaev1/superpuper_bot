import base64
import logging

from config import config
from services.http_client import request_with_retry

logger = logging.getLogger(__name__)

TOGETHER_BASE = "https://api.together.xyz/v1"

MODELS = {
    "deepseek": "deepseek-ai/DeepSeek-V3",
    "llama": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "qwen": "Qwen/Qwen2.5-72B-Instruct-Turbo",
}

IMAGE_MODELS = {
    "flux_schnell": "black-forest-labs/FLUX.1-schnell-Free",
    "flux_dev": "black-forest-labs/FLUX.1-dev",
    "sdxl": "stabilityai/stable-diffusion-xl-base-1.0",
}

HEADERS = {
    "Authorization": f"Bearer {config.TOGETHER_API_KEY}",
    "Content-Type": "application/json",
}


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
    steps: int = 4,
) -> bytes:
    model = IMAGE_MODELS.get(model_key, IMAGE_MODELS["flux_schnell"])

    if model_key == "flux_dev":
        steps = 28
    elif model_key == "sdxl":
        steps = 30

    payload = {
        "model": model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "n": 1,
        "response_format": "b64_json",
    }
    resp = await request_with_retry(
        "POST",
        f"{TOGETHER_BASE}/images/generations",
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    data = resp.json()
    b64 = data["data"][0]["b64_json"]
    return base64.b64decode(b64)
