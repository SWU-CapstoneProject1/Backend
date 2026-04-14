from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import ResultResponse
from app.services.result_service import get_result

router = APIRouter()


@router.get("/result/{job_id}", response_model=ResultResponse, summary="분석 결과 조회")
def get_analysis_result(job_id: str, db: Session = Depends(get_db)):
    """
    job_id로 분석 결과 조회
    - status: pending/running → 분석 중
    - status: done → 결과 포함
    - status: failed → 에러 메시지
    """
    result = get_result(db, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")
    return result
