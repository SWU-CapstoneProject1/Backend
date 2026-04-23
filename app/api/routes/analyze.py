from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import (
    AnalyzeTextRequest,
    AnalyzeUrlRequest,
    AnalyzeResponse,
    TermsAnalyzeRequest,
    TermsAnalyzeResponse,
)
from app.services.analyze_service import (
    create_analysis_job,
    start_text_analysis,
    start_url_analysis,
    start_file_analysis,
)
from app.services.analyze_pipeline import analyze_terms_text

# ✅ tags 제거 (핵심 수정)
router = APIRouter(prefix="/analyze")


@router.post(
    "",
    response_model=TermsAnalyzeResponse,
    responses={400: {"description": "입력값 오류"}, 500: {"description": "분석 실패"}},
    summary="약관 텍스트 즉시 분석",
)
def analyze_terms(request: TermsAnalyzeRequest):
    from app.core.config import settings

    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="분석할 텍스트를 입력해주세요")
    if len(text) < settings.MIN_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"최소 {settings.MIN_TEXT_LENGTH}자 이상 입력해주세요")

    try:
        return analyze_terms_text(text)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="분석에 필요한 데이터 파일이 없습니다. 서버 설정을 확인해주세요")
    except Exception:
        raise HTTPException(status_code=500, detail="분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요")


@router.post(
    "/text",
    response_model=AnalyzeResponse,
    responses={400: {"description": "입력값 오류"}, 500: {"description": "분석 작업 생성 실패"}},
    summary="텍스트 직접 붙여넣기 분석 작업 시작",
)
def analyze_text(req: AnalyzeTextRequest, db: Session = Depends(get_db)):
    from app.core.config import settings

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="분석할 텍스트를 입력해주세요")
    if len(text) < settings.MIN_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"최소 {settings.MIN_TEXT_LENGTH}자 이상 입력해주세요")

    try:
        job = create_analysis_job(
            db,
            input_type="text",
            input_value=text,
            service_name=req.service_name or "",
            session_key=req.session_key or "",
        )
        start_text_analysis(db, job.id, text)
    except Exception:
        raise HTTPException(status_code=500, detail="분석 작업 생성 중 오류가 발생했습니다")

    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post(
    "/url",
    response_model=AnalyzeResponse,
    responses={500: {"description": "분석 작업 생성 실패"}},
    summary="URL 입력 분석 작업 시작",
)
def analyze_url(req: AnalyzeUrlRequest, db: Session = Depends(get_db)):
    try:
        job = create_analysis_job(
            db,
            input_type="url",
            input_value=str(req.url),
            session_key=req.session_key or "",
        )
        start_url_analysis(db, job.id, str(req.url))
    except Exception:
        raise HTTPException(status_code=500, detail="분석 작업 생성 중 오류가 발생했습니다")

    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post(
    "/file",
    response_model=AnalyzeResponse,
    responses={400: {"description": "파일 형식/크기 오류"}, 500: {"description": "분석 작업 생성 실패"}},
    summary="PDF/이미지 파일 업로드 분석 작업 시작",
)
def analyze_file(
    file: UploadFile = File(...),
    session_key: str = "",
    db: Session = Depends(get_db),
):
    from app.core.config import settings

    allowed = {"application/pdf", "image/jpeg", "image/png"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="PDF, JPG, PNG 파일만 허용됩니다")

    content = file.file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"파일 크기는 {settings.MAX_FILE_SIZE_MB}MB 이하여야 합니다")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다")

    try:
        job = create_analysis_job(
            db,
            input_type="file",
            input_value=file.filename or "",
            session_key=session_key,
        )
        start_file_analysis(db, job.id, content, file.content_type)
    except Exception:
        raise HTTPException(status_code=500, detail="분석 작업 생성 중 오류가 발생했습니다")

    return AnalyzeResponse(job_id=job.id, status=job.status)