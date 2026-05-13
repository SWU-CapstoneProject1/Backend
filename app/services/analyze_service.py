from sqlalchemy.orm import Session

from app.models.models import AnalysisJob, Clause, JobStatus, RiskLevel


def _to_db_risk_level(level: str) -> RiskLevel:
    if level == "HIGH":
        return RiskLevel.danger
    if level == "MEDIUM":
        return RiskLevel.caution
    return RiskLevel.safe


def create_analysis_job(
    db:           Session,
    input_type:   str,
    input_value:  str,
    service_name: str = "",
    session_key:  str = "",
) -> AnalysisJob:
    """분석 작업 생성"""
    job = AnalysisJob(
        input_type=input_type,
        input_value=input_value,
        service_name=service_name,
        session_key=session_key,
        status=JobStatus.pending,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def start_text_analysis(db: Session, job_id: str, text: str):
    """텍스트 분석 실행 후 DB에 결과 저장"""
    from app.services.analyze_pipeline import analyze_terms_text
    from app.services.history_service import save_analysis_result

    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise ValueError(f"job_id {job_id}에 해당하는 분석 작업이 없습니다")

    job.status = JobStatus.running
    db.commit()

    try:
        result = analyze_terms_text(text)
    except Exception:
        job.status = JobStatus.failed
        db.commit()
        raise

    summary = result["summary"]

    db.query(Clause).filter(Clause.job_id == job_id).delete()
    for i, clause in enumerate(result.get("clauses", [])):
        db.add(Clause(
            job_id=job_id,
            index=i,
            original=clause.get("content", ""),
            risk_level=_to_db_risk_level(clause.get("risk_level", "LOW")),
            summary=clause.get("llm_summary") or clause.get("plain_explanation", ""),
        ))

    job.status = JobStatus.done
    job.risk_score = summary.get("risk_score", 0.0)
    job.danger_count = summary.get("high_risk", 0)
    job.caution_count = summary.get("medium_risk", 0)
    job.safe_count = summary.get("low_risk", 0)
    db.commit()

    save_analysis_result(
        db,
        result,
        service_name=job.service_name or "",
        session_key=job.session_key or "",
        job_id=job_id,
    )


def start_url_analysis(db: Session, job_id: str, url: str):
    """URL 크롤링 후 약관 텍스트 추출 → 분석"""
    from app.services.url_extractor import extract_text_from_url

    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise ValueError(f"job_id {job_id}에 해당하는 분석 작업이 없습니다")

    try:
        text = extract_text_from_url(url)
    except ValueError as e:
        job.status = JobStatus.failed
        db.commit()
        raise e

    start_text_analysis(db, job_id, text)


def start_file_analysis(db: Session, job_id: str, content: bytes, content_type: str):
    """파일에서 약관 텍스트 추출 → 분석 (PDF 지원, 이미지 미지원)"""
    from app.services.file_extractor import extract_text_from_file

    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise ValueError(f"job_id {job_id}에 해당하는 분석 작업이 없습니다")

    try:
        text = extract_text_from_file(content, content_type)
    except Exception as e:
        job.status = JobStatus.failed
        db.commit()
        raise e

    start_text_analysis(db, job_id, text)


def _mock_classify(text: str) -> list[dict]:
    """
    KoELECTRA 연동 전 임시 분류기
    문단 단위로 분리 후 랜덤 라벨 부여
    실제 모델 연동 시 이 함수 교체
    """
    import re
    paragraphs = [p.strip() for p in re.split(r"\n{2,}|(?=제\s*\d+\s*조)", text) if len(p.strip()) > 20]

    result = []
    for i, para in enumerate(paragraphs[:20]):  # 최대 20조항
        # Mock 분류: 순서에 따라 분류 (실제 모델 교체 필요)
        if i % 5 == 0:
            level = RiskLevel.danger
        elif i % 3 == 0:
            level = RiskLevel.caution
        else:
            level = RiskLevel.safe

        result.append({"text": para, "risk_level": level})

    return result
