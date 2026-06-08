import json

from sqlalchemy.orm import Session
from app.models.analysis import AnalysisResult
from app.models.models import AnalysisJob, Clause
from app.schemas.schemas import ResultResponse, ClauseOut, PrecedentOut, JobStatus, RiskLevel


def _schema_risk_level(level: str) -> RiskLevel:
    if level == "HIGH":
        return RiskLevel.danger
    if level == "MEDIUM":
        return RiskLevel.caution
    return RiskLevel.safe


def _schema_job_status(status) -> JobStatus:
    raw = status.value if hasattr(status, "value") else str(status)
    if raw == "running":
        raw = "processing"
    return JobStatus(raw)


def _result_from_saved(record: AnalysisResult) -> ResultResponse:
    data = json.loads(record.result_json or "{}")
    summary = data.get("summary", {})
    clauses = data.get("clauses", [])

    precedent_map = {}
    for clause in clauses:
        for case in clause.get("precedent_cases", []):
            case_id = case.get("id") or case.get("case_number") or case.get("title")
            if not case_id or case_id in precedent_map:
                continue
            precedent_map[case_id] = PrecedentOut(
                case_no=case.get("case_number", ""),
                title=case.get("title", ""),
                date=case.get("decision_date", ""),
                summary=case.get("preview", ""),
                source_url="",
                similarity=float(case.get("score", 0.0)),
            )

    return ResultResponse(
        job_id=record.id,
        status=JobStatus.done,
        service_name=record.service_name or "",
        risk_score=summary.get("risk_score", round((record.overall_risk_ratio or 0.0) * 100, 1)),
        danger_count=record.high_risk or 0,
        caution_count=record.medium_risk or 0,
        safe_count=record.low_risk or 0,
        clauses=[
            ClauseOut(
                id=str(clause.get("clause_id", index + 1)),
                index=index,
                original=clause.get("content", ""),
                risk_level=_schema_risk_level(clause.get("risk_level", "LOW")),
                summary=clause.get("llm_summary") or clause.get("plain_explanation", ""),
                precedents=[
                    PrecedentOut(
                        case_no=case.get("case_number", ""),
                        title=case.get("title", ""),
                        date=case.get("decision_date", ""),
                        summary=case.get("preview", ""),
                        source_url="",
                        similarity=float(case.get("score", 0.0)),
                    )
                    for case in clause.get("precedent_cases", [])
                ],
            )
            for index, clause in enumerate(clauses)
        ],
        precedents=list(precedent_map.values()),
    )


def get_result(db: Session, job_id: str) -> ResultResponse | None:
    saved = db.query(AnalysisResult).filter(AnalysisResult.id == job_id).first()
    if saved:
        return _result_from_saved(saved)

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
        status=_schema_job_status(job.status),
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
                risk_level=RiskLevel(c.risk_level.value if hasattr(c.risk_level, "value") else c.risk_level),
                summary=c.summary or "",
            )
            for c in clauses
        ],
        precedents=[],  # TODO: RAG 심결례 추천 연동 후 채우기
    )
