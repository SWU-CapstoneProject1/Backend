import mimetypes

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.schemas.schemas import (
    AnalyzeResponse,
    AnalyzeTextRequest,
    AnalyzeUrlRequest,
    TermsAnalyzeRequest,
    TermsAnalyzeResponse,
)
from app.services.analyze_pipeline import analyze_terms_text
from app.services.analyze_service import (
    create_analysis_job,
    start_file_analysis,
    start_text_analysis,
    start_url_analysis,
)
from app.services.file_extractor import OcrUnavailableError, SUPPORTED_IMAGE_CONTENT_TYPES

router = APIRouter(prefix="/analyze")

ALLOWED_FILE_CONTENT_TYPES = {"application/pdf", *SUPPORTED_IMAGE_CONTENT_TYPES}


# ────────────────────────────────────────────────
# 백그라운드 태스크 래퍼 (새 DB 세션 생성)
# ────────────────────────────────────────────────

def _bg_text_analysis(job_id: str, text: str) -> None:
    db = SessionLocal()
    try:
        start_text_analysis(db, job_id, text)
    finally:
        db.close()


def _bg_url_analysis(job_id: str, url: str) -> None:
    db = SessionLocal()
    try:
        start_url_analysis(db, job_id, url)
    finally:
        db.close()


def _bg_file_analysis(job_id: str, content: bytes, content_type: str) -> None:
    db = SessionLocal()
    try:
        start_file_analysis(db, job_id, content, content_type)
    finally:
        db.close()


# ────────────────────────────────────────────────
# 엔드포인트
# ────────────────────────────────────────────────

@router.post(
    "/text",
    response_model=AnalyzeResponse,
    responses={400: {"description": "입력값 오류"}, 500: {"description": "분석 작업 생성 실패"}},
    summary="텍스트 직접 입력 분석 작업 시작",
)
def analyze_text(req: AnalyzeTextRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from app.core.config import settings

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="분석할 텍스트를 입력해주세요.")
    if len(text) < settings.MIN_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"최소 {settings.MIN_TEXT_LENGTH}자 이상 입력해주세요.")

    try:
        job = create_analysis_job(
            db,
            input_type="text",
            input_value=text,
            service_name=req.service_name or "",
            session_key=req.session_key or "",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="분석 작업 생성 중 오류가 발생했습니다.") from exc

    background_tasks.add_task(_bg_text_analysis, job.id, text)
    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post(
    "/url",
    response_model=AnalyzeResponse,
    responses={500: {"description": "분석 작업 생성 실패"}},
    summary="URL 입력 분석 작업 시작",
)
def analyze_url(req: AnalyzeUrlRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        job = create_analysis_job(
            db,
            input_type="url",
            input_value=str(req.url),
            service_name=req.service_name or "",
            session_key=req.session_key or "",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="분석 작업 생성 중 오류가 발생했습니다.") from exc

    background_tasks.add_task(_bg_url_analysis, job.id, str(req.url))
    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post(
    "/file",
    response_model=AnalyzeResponse,
    responses={
        400: {"description": "파일 형식/크기 오류"},
        422: {"description": "텍스트 추출 실패"},
        503: {"description": "OCR 엔진 설정 필요"},
        500: {"description": "분석 작업 생성 실패"},
    },
    summary="PDF/이미지 파일 업로드 분석 작업 시작",
)
def analyze_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session_key: str = Form(""),
    service_name: str = Form(""),
    db: Session = Depends(get_db),
):
    from app.core.config import settings

    resolved_session_key = session_key or request.query_params.get("session_key", "")
    resolved_service_name = service_name or request.query_params.get("service_name", "")
    content_type = _resolve_content_type(file)

    if content_type not in ALLOWED_FILE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="PDF, JPG, PNG 이미지 파일만 업로드할 수 있습니다.")

    content = file.file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"파일 크기는 {settings.MAX_FILE_SIZE_MB}MB 이하여야 합니다.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")

    try:
        job = create_analysis_job(
            db,
            input_type="file",
            input_value=file.filename or "",
            service_name=resolved_service_name,
            session_key=resolved_session_key,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="분석 작업 생성 중 오류가 발생했습니다.") from exc

    background_tasks.add_task(_bg_file_analysis, job.id, content, content_type)
    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post(
    "",
    response_model=TermsAnalyzeResponse,
    responses={400: {"description": "입력값 오류"}, 500: {"description": "분석 실패"}},
    summary="약관 텍스트 즉시 분석",
)
def analyze_terms(request: TermsAnalyzeRequest, db: Session = Depends(get_db)):
    from app.core.config import settings
    from app.services.history_service import save_analysis_result

    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="분석할 텍스트를 입력해주세요.")
    if len(text) < settings.MIN_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"최소 {settings.MIN_TEXT_LENGTH}자 이상 입력해주세요.")

    try:
        result = analyze_terms_text(text)
        record = save_analysis_result(
            db,
            result,
            service_name=request.service_name or "직접 입력",
            session_key=request.session_key or "",
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="분석에 필요한 데이터 파일이 없습니다. 서버 설정을 확인해주세요.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") from exc

    result["job_id"] = record.id
    return result


def _resolve_content_type(file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    if content_type == "image/jpg":
        return "image/jpeg"
    if content_type and content_type != "application/octet-stream":
        return content_type

    guessed_type, _ = mimetypes.guess_type(file.filename or "")
    guessed_type = (guessed_type or "").lower()
    if guessed_type == "image/jpg":
        return "image/jpeg"
    return guessed_type
