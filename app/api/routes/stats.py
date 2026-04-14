from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import StatsResponse
from app.services.stats_service import get_stats

router = APIRouter()


@router.get("/stats", response_model=StatsResponse, summary="서비스 통계 조회")
def get_service_stats(db: Session = Depends(get_db)):
    """
    홈화면 누적 통계 조회
    - 전체 분석 건수
    - 누적 위험 조항 수
    - 분석된 서비스 수
    """
    return get_stats(db)
