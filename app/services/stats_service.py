from sqlalchemy.orm import Session
from app.models.models import ServiceStats
from app.schemas.schemas import StatsResponse


def get_stats(db: Session) -> StatsResponse:
    stats = db.query(ServiceStats).first()
    if not stats:
        return StatsResponse(total_analyses=0, total_danger=0, total_services=0)

    return StatsResponse(
        total_analyses=stats.total_analyses,
        total_danger=stats.total_danger,
        total_services=stats.total_services,
    )
