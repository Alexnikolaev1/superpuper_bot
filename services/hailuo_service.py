import asyncio
import base64
import logging
from typing import Callable, Awaitable

from config import config
from services.http_client import get_client, request_with_retry

logger = logging.getLogger(__name__)

HAILUO_BASE = "https://api.minimax.io/v1"
VIDEO_MODEL = "MiniMax-Hailuo-2.3-Fast"
VIDEO_MODEL_I2V = "MiniMax-Hailuo-2.3-Fast"
DEFAULT_RESOLUTION = "768P"
MAX_WAIT_SECONDS = 600
POLL_INTERVAL = 8

HEADERS = {
    "Authorization": f"Bearer {config.HAILUO_API_KEY}",
    "Content-Type": "application/json",
}

ProgressCallback = Callable[[int, str], Awaitable[None]]

_SUCCESS_STATUSES = {"success", "Success", "SUCCESS"}
_FAIL_STATUSES = {"fail", "Fail", "Failed", "failed", "FAIL"}


def _check_base_resp(data: dict) -> None:
    base = data.get("base_resp", {})
    code = base.get("status_code", 0)
    if code != 0:
        msg = base.get("status_msg", "unknown error")
        raise RuntimeError(f"MiniMax API error {code}: {msg}")


async def text_to_video(
    prompt: str,
    duration: int = 6,
    on_progress: ProgressCallback | None = None,
) -> str:
    payload = {
        "model": VIDEO_MODEL,
        "prompt": prompt,
        "duration": duration,
        "resolution": DEFAULT_RESOLUTION,
    }
    task_id = await _create_task(payload)
    return await _poll_video_task(task_id, on_progress=on_progress)


async def image_to_video(
    image_bytes: bytes,
    prompt: str = "",
    duration: int = 6,
    on_progress: ProgressCallback | None = None,
) -> str:
    b64_image = base64.b64encode(image_bytes).decode()
    payload = {
        "model": VIDEO_MODEL_I2V,
        "first_frame_image": f"data:image/jpeg;base64,{b64_image}",
        "prompt": prompt or "Smooth cinematic motion, high quality",
        "duration": duration,
        "resolution": DEFAULT_RESOLUTION,
    }
    task_id = await _create_task(payload)
    return await _poll_video_task(task_id, on_progress=on_progress)


async def _create_task(payload: dict) -> str:
    resp = await request_with_retry(
        "POST",
        f"{HAILUO_BASE}/video_generation",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    data = resp.json()
    _check_base_resp(data)
    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError(f"MiniMax: task_id not returned: {data}")
    return task_id


async def _poll_video_task(
    task_id: str,
    max_wait: int = MAX_WAIT_SECONDS,
    on_progress: ProgressCallback | None = None,
) -> str:
    elapsed = 0
    client = get_client()

    while elapsed < max_wait:
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

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
        _check_base_resp(data)

        status = str(data.get("status", "")).strip()
        logger.info("MiniMax video task %s status: %s", task_id, status)

        if status in _SUCCESS_STATUSES:
            file_id = data.get("file_id")
            if not file_id:
                raise RuntimeError(f"MiniMax: no file_id in response: {data}")
            return await _get_video_url(file_id)

        if status in _FAIL_STATUSES:
            raise RuntimeError(f"Video generation failed: {data}")

    raise TimeoutError(f"Video generation timed out after {max_wait // 60} minutes")


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
    data = resp.json()
    _check_base_resp(data)

    file_info = data.get("file", data)
    url = file_info.get("download_url") or file_info.get("url")
    if not url:
        raise RuntimeError(f"MiniMax: download URL not found: {data}")
    return url


async def download_video(url: str) -> bytes:
    resp = await request_with_retry("GET", url, timeout=180)
    return resp.content
