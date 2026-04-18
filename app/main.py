from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze, result, stats, bookmark
from app.core.config import settings

app = FastAPI(
    title="약간동의 API",
    description="AI 기반 불공정 약관 탐지 플랫폼",
    version="0.1.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 (여기서만 tags 설정)
app.include_router(analyze.router, prefix="/api", tags=["분석"])
app.include_router(result.router, prefix="/api", tags=["결과"])
app.include_router(stats.router, prefix="/api", tags=["통계"])
app.include_router(bookmark.router, prefix="/api", tags=["보관함"])


@app.get("/")
def root():
    return {"message": "약간동의 API 서버 동작 중"}


@app.get("/health")
def health():
    return {"status": "ok"}