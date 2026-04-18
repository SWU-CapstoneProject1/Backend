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


@router.post("", response_model=TermsAnalyzeResponse, summary="약관 텍스트 즉시 분석")
def analyze_terms(request: TermsAnalyzeRequest):
    try:
        result = analyze_terms_text(request.text)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"필수 파일 없음: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@router.post("/text", response_model=AnalyzeResponse, summary="텍스트 직접 붙여넣기 분석 작업 시작")
def analyze_text(req: AnalyzeTextRequest, db: Session = Depends(get_db)):
    from app.core.config import settings

    if len(req.text) < settings.MIN_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"최소 {settings.MIN_TEXT_LENGTH}자 이상 입력해주세요"
        )

    job = create_analysis_job(
        db,
        input_type="text",
        input_value=req.text,
        service_name=req.service_name,
        session_key=req.session_key,
    )

    start_text_analysis(db, job.id, req.text)

    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post("/url", response_model=AnalyzeResponse, summary="URL 입력 분석 작업 시작")
def analyze_url(req: AnalyzeUrlRequest, db: Session = Depends(get_db)):
    job = create_analysis_job(
        db,
        input_type="url",
        input_value=req.url,
        session_key=req.session_key,
    )

    start_url_analysis(db, job.id, req.url)

    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post("/file", response_model=AnalyzeResponse, summary="PDF/이미지 파일 업로드 분석 작업 시작")
def analyze_file(
    file: UploadFile = File(...),
    session_key: str = "",
    db: Session = Depends(get_db),
):
    from app.core.config import settings

    content = file.file.read()

    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기는 {settings.MAX_FILE_SIZE_MB}MB 이하여야 합니다"
        )

    allowed = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail="PDF, JPG, PNG 파일만 허용됩니다"
        )

    job = create_analysis_job(
        db,
        input_type="file",
        input_value=file.filename,
        session_key=session_key,
    )

    start_file_analysis(db, job.id, content, file.content_type)

    return AnalyzeResponse(job_id=job.id, status=job.status)