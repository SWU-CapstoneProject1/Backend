from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.analysis import AnalysisResult

router = APIRouter(prefix="/dashboard")


@router.get("")
def get_dashboard(db: Session = Depends(get_db)):
    total_analyses = db.query(func.count(AnalysisResult.id)).scalar()

    total_high = db.query(func.sum(AnalysisResult.high_risk)).scalar() or 0
    total_medium = db.query(func.sum(AnalysisResult.medium_risk)).scalar() or 0
    total_low = db.query(func.sum(AnalysisResult.low_risk)).scalar() or 0

    total_services = db.query(
        func.count(func.distinct(AnalysisResult.service_name))
    ).scalar()

    recent = db.query(AnalysisResult).order_by(
        AnalysisResult.created_at.desc()
    ).limit(5).all()

    recent_list = [
        {
            "job_id": r.id,
            "service_name": r.service_name,
            "date": r.created_at.strftime("%Y-%m-%d"),
            "risk_score": int(r.overall_risk_ratio * 100),
        }
        for r in recent
    ]

    return {
        "total_analyses": total_analyses,
        "total_high": total_high,
        "total_medium": total_medium,
        "total_low": total_low,
        "total_services": total_services,
        "recent": recent_list,
    }