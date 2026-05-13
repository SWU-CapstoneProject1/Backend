from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import analyze, result, stats, bookmark, report, history, dashboard
from app.core.config import settings

app = FastAPI(
    title="약간동의 API",
    description="AI 기반 불공정 약관 탐지 플랫폼",
    version="0.1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": errors, "status_code": 422},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "서버 내부 오류가 발생했습니다", "status_code": 500},
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
app.include_router(report.router, prefix="/api", tags=["리포트"])
app.include_router(history.router, prefix="/api", tags=["보관함"])
app.include_router(dashboard.router, prefix="/api", tags=["대시보드"])


@app.get("/")
def root():
    return {"message": "약간동의 API 서버 동작 중"}


@app.get("/health")
def health():
    return {"status": "ok"}
