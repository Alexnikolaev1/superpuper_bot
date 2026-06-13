import json
import logging
from datetime import datetime
from pathlib import Path

from config import config

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

_conversations: dict[int, list[dict]] = {}
_gen_history: dict[int, list[dict]] = {}
_last_images: dict[int, bytes] = {}


def get_conversation(user_id: int) -> list[dict]:
    return list(_conversations.get(user_id, []))


def add_message(user_id: int, role: str, content: str) -> None:
    if user_id not in _conversations:
        _conversations[user_id] = []
    _conversations[user_id].append({"role": role, "content": content})
    limit = config.MAX_CONVERSATION_MESSAGES
    if len(_conversations[user_id]) > limit:
        _conversations[user_id] = _conversations[user_id][-limit:]


def clear_conversation(user_id: int) -> None:
    _conversations[user_id] = []


def add_generation(user_id: int, gen_type: str, prompt: str, result_info: str = "") -> None:
    if user_id not in _gen_history:
        _gen_history[user_id] = []
    _gen_history[user_id].append({
        "type": gen_type,
        "prompt": prompt[:200],
        "result": result_info,
        "time": datetime.now().strftime("%d.%m %H:%M"),
    })
    limit = config.MAX_HISTORY_ITEMS
    if len(_gen_history[user_id]) > limit:
        _gen_history[user_id] = _gen_history[user_id][-limit:]
    _save_history(user_id)


def get_history(user_id: int) -> list[dict]:
    _load_history(user_id)
    return list(_gen_history.get(user_id, []))


def clear_history(user_id: int) -> None:
    _gen_history[user_id] = []
    path = DATA_DIR / f"{user_id}_history.json"
    if path.exists():
        path.unlink(missing_ok=True)


def get_history_stats(user_id: int) -> dict[str, int]:
    history = get_history(user_id)
    stats: dict[str, int] = {}
    for item in history:
        stats[item["type"]] = stats.get(item["type"], 0) + 1
    return stats


def _save_history(user_id: int) -> None:
    try:
        path = DATA_DIR / f"{user_id}_history.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_gen_history.get(user_id, []), f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.error("Error saving history for %s: %s", user_id, exc)


def _load_history(user_id: int) -> None:
    if user_id in _gen_history:
        return
    try:
        path = DATA_DIR / f"{user_id}_history.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _gen_history[user_id] = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Error loading history for %s: %s", user_id, exc)
        _gen_history[user_id] = []


def get_last_image(user_id: int) -> bytes | None:
    return _last_images.get(user_id)


def save_last_image(user_id: int, image_bytes: bytes) -> None:
    _last_images[user_id] = image_bytes
