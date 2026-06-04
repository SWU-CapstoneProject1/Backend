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
    OCR_PDF_MAX_PAGES: int = 20
    OCR_PDF_DPI: int = 200
    TESSERACT_CMD: str = ""
    TESSDATA_DIR: str = ""

    PRECEDENT_MIN_SIMILARITY: float = 0.2
    USE_SEMANTIC_RAG: bool = False
    ALLOW_MODEL_DOWNLOAD: bool = False

    USE_KOELECTRA_CLASSIFIER: bool = False
    KOELECTRA_MODEL_NAME_OR_PATH: str = "snunlp/KR-ELECTRA-discriminator"
    KOELECTRA_DEVICE: int = -1
    KOELECTRA_MAX_LENGTH: int = 256
    KOELECTRA_MIN_CONFIDENCE: float = 0.5
    KOELECTRA_LABEL_MAP: str = "LABEL_0:LOW,LABEL_1:MEDIUM,LABEL_2:HIGH"

    LAW_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
