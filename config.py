import os
import sys

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

REQUIRED_VARS = ("TELEGRAM_TOKEN", "TOGETHER_API_KEY", "OPENROUTER_API_KEY", "HAILUO_API_KEY")


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    TELEGRAM_TOKEN: str

    TOGETHER_API_KEY: str
    OPENROUTER_API_KEY: str
    HAILUO_API_KEY: str

    ALLOWED_USER_IDS: str | None = None

    MAX_CONVERSATION_MESSAGES: int = Field(default=20, ge=4, le=50)
    MAX_HISTORY_ITEMS: int = Field(default=50, ge=10, le=200)
    THROTTLE_RATE: float = Field(default=0.5, ge=0.1, le=5.0)

    def get_allowed_ids(self) -> set[int] | None:
        if not self.ALLOWED_USER_IDS:
            return None
        return {int(x.strip()) for x in self.ALLOWED_USER_IDS.split(",") if x.strip()}

    def is_allowed(self, user_id: int) -> bool:
        allowed = self.get_allowed_ids()
        return True if allowed is None else user_id in allowed


def _load_config() -> Config:
    try:
        return Config()
    except ValidationError:
        missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
        print(
            "\n❌ Бот не запущен: не заданы переменные окружения.\n"
            f"   Отсутствуют: {', '.join(missing)}\n\n"
            "   Railway → твой сервис → вкладка Variables → Add Variable:\n"
            "   • TELEGRAM_TOKEN\n"
            "   • TOGETHER_API_KEY\n"
            "   • OPENROUTER_API_KEY\n"
            "   • HAILUO_API_KEY\n\n"
            "   После сохранения Railway перезапустит деплой автоматически.\n",
            file=sys.stderr,
        )
        raise


config = _load_config()
