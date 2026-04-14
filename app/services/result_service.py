from sqlalchemy.orm import Session
from app.models.models import AnalysisJob, Clause
from app.schemas.schemas import ResultResponse, ClauseOut, JobStatus, RiskLevel


def get_result(db: Session, job_id: str) -> ResultResponse | None:
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        return None

    clauses = (
        db.query(Clause)
        .filter(Clause.job_id == job_id)
        .order_by(Clause.index)
        .all()
    )

    return ResultResponse(
        job_id=job.id,
        status=JobStatus(job.status),
        service_name=job.service_name or "",
        risk_score=job.risk_score or 0.0,
        danger_count=job.danger_count or 0,
        caution_count=job.caution_count or 0,
        safe_count=job.safe_count or 0,
        clauses=[
            ClauseOut(
                id=c.id,
                index=c.index,
                original=c.original,
                risk_level=RiskLevel(c.risk_level),
                summary=c.summary or "",
            )
            for c in clauses
        ],
        precedents=[],  # TODO: RAG 심결례 추천 연동 후 채우기
    )
