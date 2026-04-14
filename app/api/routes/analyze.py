from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import (
    AnalyzeTextRequest, AnalyzeUrlRequest, AnalyzeResponse
)
from app.services.analyze_service import (
    create_analysis_job, start_text_analysis, start_url_analysis, start_file_analysis
)

router = APIRouter()


@router.post("/analyze/text", response_model=AnalyzeResponse, summary="텍스트 직접 붙여넣기 분석")
def analyze_text(req: AnalyzeTextRequest, db: Session = Depends(get_db)):
    """
    텍스트를 직접 붙여넣어 분석 시작
    - 최소 100자 이상 필요
    - job_id 반환 후 GET /api/result/{job_id} 로 결과 조회
    """
    from app.core.config import settings
    if len(req.text) < settings.MIN_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"최소 {settings.MIN_TEXT_LENGTH}자 이상 입력해주세요"
        )

    job = create_analysis_job(db, input_type="text", input_value=req.text,
                              service_name=req.service_name, session_key=req.session_key)

    # TODO: Celery 비동기 작업 등록 (현재는 Mock)
    # analyze_task.delay(job.id)
    start_text_analysis(db, job.id, req.text)

    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post("/analyze/url", response_model=AnalyzeResponse, summary="URL 입력 분석")
def analyze_url(req: AnalyzeUrlRequest, db: Session = Depends(get_db)):
    """
    약관 페이지 URL을 입력하면 자동 크롤링 후 분석
    - 유효하지 않은 URL은 400 에러
    - robots.txt 차단 사이트는 에러 안내
    """
    job = create_analysis_job(db, input_type="url", input_value=req.url,
                              session_key=req.session_key)

    # TODO: Celery 비동기 작업 등록
    # crawl_and_analyze_task.delay(job.id, req.url)
    start_url_analysis(db, job.id, req.url)

    return AnalyzeResponse(job_id=job.id, status=job.status)


@router.post("/analyze/file", response_model=AnalyzeResponse, summary="PDF/이미지 파일 업로드 분석")
def analyze_file(
    file:        UploadFile = File(...),
    session_key: str = "",
    db:          Session = Depends(get_db),
):
    """
    PDF 또는 이미지 파일 업로드 후 분석
    - 허용 형식: PDF, JPG, PNG
    - 최대 크기: 10MB
    """
    from app.core.config import settings

    # 파일 크기 체크
    content = file.file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"파일 크기는 {settings.MAX_FILE_SIZE_MB}MB 이하여야 합니다")

    # 파일 형식 체크
    allowed = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="PDF, JPG, PNG 파일만 허용됩니다")

    job = create_analysis_job(db, input_type="file", input_value=file.filename,
                              session_key=session_key)

    # TODO: Celery 비동기 작업 등록
    # file_analyze_task.delay(job.id, content, file.content_type)
    start_file_analysis(db, job.id, content, file.content_type)

    return AnalyzeResponse(job_id=job.id, status=job.status)
