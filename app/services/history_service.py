import json
import uuid
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult


def save_analysis_result(
    db: Session,
    result: dict,
    service_name: str = "",
    session_key: str = "",
):
    job_id = str(uuid.uuid4())

    summary = result["summary"]

    record = AnalysisResult(
        id=job_id,
        service_name=service_name,
        session_key=session_key,
        total_clauses=summary["total_clauses"],
        high_risk=summary["high_risk"],
        medium_risk=summary["medium_risk"],
        low_risk=summary["low_risk"],
        overall_risk_ratio=summary["overall_risk_ratio"],
        result_json=json.dumps(result, ensure_ascii=False),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record