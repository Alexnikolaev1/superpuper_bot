import asyncio
import base64
import logging
from typing import Callable, Awaitable

from config import config
from services.http_client import get_client, request_with_retry

logger = logging.getLogger(__name__)

HAILUO_BASE = "https://api.minimaxi.chat/v1"

HEADERS = {
    "Authorization": f"Bearer {config.HAILUO_API_KEY}",
    "Content-Type": "application/json",
}

ProgressCallback = Callable[[int, str], Awaitable[None]]


async def text_to_video(
    prompt: str,
    duration: int = 6,
    on_progress: ProgressCallback | None = None,
) -> str:
    payload = {
        "model": "video-01",
        "prompt": prompt,
        "duration": duration,
        "resolution": "1080p",
    }
    resp = await request_with_retry(
        "POST",
        f"{HAILUO_BASE}/video_generation",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    task_id = resp.json()["task_id"]
    return await _poll_video_task(task_id, on_progress=on_progress)


async def image_to_video(
    image_bytes: bytes,
    prompt: str = "",
    duration: int = 6,
    on_progress: ProgressCallback | None = None,
) -> str:
    b64_image = base64.b64encode(image_bytes).decode()
    payload = {
        "model": "video-01",
        "first_frame_image": f"data:image/jpeg;base64,{b64_image}",
        "prompt": prompt or "Smooth cinematic motion, high quality",
        "duration": duration,
    }
    resp = await request_with_retry(
        "POST",
        f"{HAILUO_BASE}/video_generation",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    task_id = resp.json()["task_id"]
    return await _poll_video_task(task_id, on_progress=on_progress)


async def _poll_video_task(
    task_id: str,
    max_wait: int = 300,
    on_progress: ProgressCallback | None = None,
) -> str:
    elapsed = 0
    client = get_client()

    while elapsed < max_wait:
        await asyncio.sleep(5)
        elapsed += 5

        if on_progress:
            await on_progress(elapsed, _progress_message(elapsed))

        resp = await client.get(
            f"{HAILUO_BASE}/query/video_generation",
            headers=HEADERS,
            params={"task_id": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")

        if status == "Success":
            return await _get_video_url(data["file_id"])
        if status in ("Fail", "Failed"):
            raise RuntimeError(f"Video generation failed: {data}")

    raise TimeoutError("Video generation timed out after 5 minutes")


def _progress_message(elapsed: int) -> str:
    if elapsed < 30:
        return "🎬 Запускаю генерацию..."
    if elapsed < 90:
        return "⏳ Рендеринг сцены..."
    if elapsed < 180:
        return "🎞 Финальная обработка..."
    return "⌛ Почти готово, подожди ещё немного..."


async def _get_video_url(file_id: str) -> str:
    resp = await request_with_retry(
        "GET",
        f"{HAILUO_BASE}/files/retrieve",
        headers=HEADERS,
        params={"file_id": file_id},
        timeout=30,
    )
    return resp.json()["file"]["download_url"]


async def download_video(url: str) -> bytes:
    resp = await request_with_retry("GET", url, timeout=120)
    return resp.content
