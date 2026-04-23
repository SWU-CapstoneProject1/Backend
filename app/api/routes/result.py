import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import ResultResponse
from app.services.result_service import get_result

router = APIRouter()


@router.get(
    "/result/{job_id}",
    response_model=ResultResponse,
    responses={400: {"description": "잘못된 job_id 형식"}, 404: {"description": "분석 결과 없음"}, 500: {"description": "조회 실패"}},
    summary="분석 결과 조회",
)
def get_analysis_result(job_id: str, db: Session = Depends(get_db)):
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="job_id 형식이 올바르지 않습니다")

    try:
        result = get_result(db, job_id)
    except Exception:
        raise HTTPException(status_code=500, detail="결과 조회 중 오류가 발생했습니다")

    if result is None:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")

    return result
