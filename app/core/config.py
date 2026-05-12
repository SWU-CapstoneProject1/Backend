from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "YakganDongui API"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./yakgandongui.db"

    ALLOWED_ORIGINS: List[str] = ["*"]

    MIN_TEXT_LENGTH: int = 20
    MAX_FILE_SIZE_MB: int = 10

    OCR_LANGUAGE: str = "kor+eng"
    OCR_PSM: int = 6
    OCR_MIN_TEXT_LENGTH: int = 20
    TESSERACT_CMD: str = ""
    TESSDATA_DIR: str = ""

    LAW_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
