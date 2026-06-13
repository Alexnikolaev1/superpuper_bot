from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


config = Config()
