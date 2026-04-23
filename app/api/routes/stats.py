from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import StatsResponse
from app.services.stats_service import get_stats

router = APIRouter()


@router.get(
    "/stats",
    response_model=StatsResponse,
    responses={500: {"description": "통계 조회 실패"}},
    summary="서비스 통계 조회",
)
def get_service_stats(db: Session = Depends(get_db)):
    try:
        return get_stats(db)
    except Exception:
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다")
