from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.models import AnalysisJob, AnalysisProgress
from app.schemas.schemas import AnalysisProgressResponse, JobStatus as SchemaJobStatus


def _clamp_percent(value: int | None) -> int:
    if value is None:
        return 0
    return max(0, min(100, int(value)))


def _schema_status(status) -> SchemaJobStatus:
    raw_status = status.value if hasattr(status, "value") else str(status)
    # DB에 "running"으로 저장된 값을 "processing"으로 매핑
    if raw_status == "running":
        raw_status = "processing"
    return SchemaJobStatus(raw_status)


def _build_response(
    job_id: str,
    status: SchemaJobStatus,
    progress_percent: int,
    stage: str,
    message: str = "",
    current_clause: int = 0,
    total_clauses: int = 0,
    current_clause_title: str = "",
    current_clause_preview: str = "",
) -> AnalysisProgressResponse:
    return AnalysisProgressResponse(
        job_id=job_id,
        status=status,
        progress_percent=_clamp_percent(progress_percent),
        stage=stage,
        message=message,
        current_clause=current_clause or 0,
        total_clauses=total_clauses or 0,
        current_clause_title=current_clause_title or "",
        current_clause_preview=current_clause_preview or "",
    )


def update_analysis_progress(
    db: Session,
    job_id: str,
    *,
    progress_percent: int | None = None,
    stage: str | None = None,
    message: str | None = None,
    current_clause: int | None = None,
    total_clauses: int | None = None,
    current_clause_title: str | None = None,
    current_clause_preview: str | None = None,
) -> AnalysisProgress:
    progress = db.query(AnalysisProgress).filter(AnalysisProgress.job_id == job_id).first()
    if progress is None:
        progress = AnalysisProgress(job_id=job_id)
        db.add(progress)

    if progress_percent is not None:
        progress.progress_percent = _clamp_percent(progress_percent)
    if stage is not None:
        progress.stage = stage
    if message is not None:
        progress.message = message
    if current_clause is not None:
        progress.current_clause = max(0, int(current_clause))
    if total_clauses is not None:
        progress.total_clauses = max(0, int(total_clauses))
    if current_clause_title is not None:
        progress.current_clause_title = current_clause_title
    if current_clause_preview is not None:
        progress.current_clause_preview = current_clause_preview

    db.commit()
    db.refresh(progress)
    return progress


def mark_analysis_failed(
    db: Session,
    job_id: str,
    message: str = "분석 중 오류가 발생했습니다.",
) -> AnalysisProgress:
    progress = db.query(AnalysisProgress).filter(AnalysisProgress.job_id == job_id).first()
    progress_percent = progress.progress_percent if progress is not None else 0
    return update_analysis_progress(
        db,
        job_id,
        progress_percent=progress_percent,
        stage="failed",
        message=message,
    )


def get_analysis_progress(db: Session, job_id: str) -> AnalysisProgressResponse | None:
    progress = db.query(AnalysisProgress).filter(AnalysisProgress.job_id == job_id).first()
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    saved_result = db.query(AnalysisResult).filter(AnalysisResult.id == job_id).first()

    if job is None and saved_result is None and progress is None:
        return None

    if job is not None:
        status = _schema_status(job.status)
    elif saved_result is not None:
        status = SchemaJobStatus.done
    else:
        status = SchemaJobStatus.pending

    if progress is None:
        if status == SchemaJobStatus.done:
            return _build_response(job_id, status, 100, "completed", "분석이 완료되었습니다.")
        if status == SchemaJobStatus.failed:
            return _build_response(job_id, status, 0, "failed", "분석 중 오류가 발생했습니다.")
        if status == SchemaJobStatus.running:
            return _build_response(job_id, status, 5, "running", "분석을 진행하고 있습니다.")
        return _build_response(job_id, status, 0, "queued", "분석 대기 중입니다.")

    progress_percent = progress.progress_percent or 0
    stage = progress.stage or "queued"
    message = progress.message or ""

    if status == SchemaJobStatus.done:
        progress_percent = 100
        stage = "completed"
        message = message or "분석이 완료되었습니다."
    elif status == SchemaJobStatus.failed:
        stage = "failed"
        message = message or "분석 중 오류가 발생했습니다."

    return _build_response(
        job_id=job_id,
        status=status,
        progress_percent=progress_percent,
        stage=stage,
        message=message,
        current_clause=progress.current_clause or 0,
        total_clauses=progress.total_clauses or 0,
        current_clause_title=progress.current_clause_title or "",
        current_clause_preview=progress.current_clause_preview or "",
    )
