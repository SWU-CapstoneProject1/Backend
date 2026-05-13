import json
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult


def save_analysis_result(
    db: Session,
    result: dict,
    service_name: str = "",
    session_key: str = "",
    job_id: Optional[str] = None,
):
    job_id = job_id or str(uuid.uuid4())

    summary = result["summary"]

    stored_result = dict(result)
    stored_result["job_id"] = job_id

    record = db.query(AnalysisResult).filter(AnalysisResult.id == job_id).first()
    if record is None:
        record = AnalysisResult(id=job_id)
        db.add(record)

    record.service_name = service_name
    record.session_key = session_key
    record.total_clauses = summary["total_clauses"]
    record.high_risk = summary["high_risk"]
    record.medium_risk = summary["medium_risk"]
    record.low_risk = summary["low_risk"]
    record.overall_risk_ratio = summary["overall_risk_ratio"]
    record.result_json = json.dumps(stored_result, ensure_ascii=False)

    db.commit()
    db.refresh(record)

    return record
