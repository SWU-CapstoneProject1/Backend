from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 기본 앱 설정
    APP_NAME: str = "약간동의 API"
    DEBUG: bool = True

    # DB
    DATABASE_URL: str = "sqlite:///./yakgandongui.db"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # 분석 관련
    MIN_TEXT_LENGTH: int = 20
    MAX_FILE_SIZE_MB: int = 10

    # 외부 API 키
    LAW_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",   # .env에 추가 값 있어도 무시
    )


settings = Settings()