from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.analysis import AnalysisResult
from app.schemas.schemas import StatsResponse


def get_stats(db: Session) -> StatsResponse:
    total_analyses = db.query(func.count(AnalysisResult.id)).scalar() or 0
    total_danger = db.query(func.sum(AnalysisResult.high_risk)).scalar() or 0
    total_services = (
        db.query(func.count(func.distinct(AnalysisResult.service_name)))
        .filter(AnalysisResult.service_name.isnot(None), AnalysisResult.service_name != "")
        .scalar()
        or 0
    )

    return StatsResponse(
        total_analyses=int(total_analyses),
        total_danger=int(total_danger),
        total_services=int(total_services),
    )
