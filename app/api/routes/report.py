import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.result_service import get_result
from app.services.pdf_report_service import generate_pdf_report

router = APIRouter()


@router.get(
    "/report/{job_id}/pdf",
    summary="분석 결과 PDF 다운로드",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF 파일"},
        400: {"description": "잘못된 job_id 형식"},
        404: {"description": "분석 결과 없음"},
        500: {"description": "PDF 생성 실패"},
    },
)
def download_pdf_report(job_id: str, db: Session = Depends(get_db)):
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="job_id 형식이 올바르지 않습니다")

    result = get_result(db, job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")

    try:
        pdf_bytes = generate_pdf_report(result)
    except Exception:
        raise HTTPException(status_code=500, detail="PDF 생성 중 오류가 발생했습니다")

    service_name = result.service_name or "report"
    filename = f"yakgandongui_{service_name}_{job_id[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
