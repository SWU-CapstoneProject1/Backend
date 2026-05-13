from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import AnalysisResult

router = APIRouter(prefix="/history")


@router.get("")
def get_history(
    db: Session = Depends(get_db),
    session_key: str = "",
    risk_level: str = ""
):
    query = db.query(AnalysisResult)

    if session_key:
        query = query.filter(AnalysisResult.session_key == session_key)

    results = query.order_by(AnalysisResult.created_at.desc()).all()

    response = []

    for r in results:
        if risk_level:
            if risk_level == "HIGH" and r.high_risk == 0:
                continue
            if risk_level == "MEDIUM" and r.medium_risk == 0:
                continue
            if risk_level == "LOW" and r.low_risk == 0:
                continue

        response.append({
            "job_id": r.id,
            "service_name": r.service_name,
            "date": r.created_at.strftime("%Y-%m-%d"),
            "risk_score": int(r.overall_risk_ratio * 100),
            "high": r.high_risk,
            "medium": r.medium_risk,
            "low": r.low_risk,
        })

    return response


@router.delete("/{job_id}")
def delete_history(job_id: str, db: Session = Depends(get_db)):
    db.query(AnalysisResult).filter(AnalysisResult.id == job_id).delete()
    db.commit()
    return {"success": True}