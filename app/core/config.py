from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 앱
    APP_NAME: str = "약간동의"
    DEBUG: bool = True

    # DB
    DATABASE_URL: str = "sqlite:///./yakgan.db"  # 개발용 SQLite, 배포시 PostgreSQL로 교체

    # Redis (Celery 브로커)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Claude API (LLM 요약 생성)
    ANTHROPIC_API_KEY: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # 분석 설정
    MIN_TEXT_LENGTH: int = 100       # 최소 입력 글자수
    MAX_FILE_SIZE_MB: int = 10       # 최대 파일 크기

    class Config:
        env_file = ".env"


settings = Settings()
