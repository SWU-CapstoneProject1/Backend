"""
분석 서비스 레이어
현재: Mock 데이터 반환 (AI 모델 연동 전 뼈대)
추후: KoELECTRA 분류 + Claude API 요약 + RAG 심결례 추천 연동
"""
from sqlalchemy.orm import Session

from app.models.models import AnalysisJob, Clause, JobStatus, RiskLevel


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
    """
    텍스트 분석 실행
    TODO: 실제 AI 파이프라인 연동
      1. 조항 단위 분리 (Regex + SBD)
      2. KoELECTRA 위험도 분류
      3. Claude API 쉬운 요약 생성 (lazy)
      4. RAG 심결례 추천
    """
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        return

    job.status = JobStatus.running
    db.commit()

    # ── Mock 분석 결과 ──────────────────────────────
    # 실제 KoELECTRA 모델 연동 전 임시 데이터
    mock_clauses = _mock_classify(text)

    danger_count  = sum(1 for c in mock_clauses if c["risk_level"] == RiskLevel.danger)
    caution_count = sum(1 for c in mock_clauses if c["risk_level"] == RiskLevel.caution)
    safe_count    = sum(1 for c in mock_clauses if c["risk_level"] == RiskLevel.safe)
    total         = len(mock_clauses) or 1

    # 위험도 점수: 단순 비율 방식 (기능명세서 확정값)
    risk_score = (danger_count / total) * 100

    for i, clause in enumerate(mock_clauses):
        db.add(Clause(
            job_id=job_id,
            index=i,
            original=clause["text"],
            risk_level=clause["risk_level"],
            summary="",  # lazy 생성 — 리포트 화면 진입 시 Claude API 호출
        ))

    job.status        = JobStatus.done
    job.risk_score    = round(risk_score, 1)
    job.danger_count  = danger_count
    job.caution_count = caution_count
    job.safe_count    = safe_count
    db.commit()
    # ── Mock 끝 ────────────────────────────────────


def start_url_analysis(db: Session, job_id: str, url: str):
    """
    URL 크롤링 후 분석
    TODO:
      1. Playwright로 페이지 렌더링
      2. Trafilatura로 본문 추출
      3. start_text_analysis() 호출
    """
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        return

    # Mock: URL 분석은 추후 구현
    job.status = JobStatus.failed
    db.commit()


def start_file_analysis(db: Session, job_id: str, content: bytes, content_type: str):
    """
    PDF/이미지 파일 분석
    TODO:
      - PDF: PyMuPDF 텍스트 추출
      - 이미지: PaddleOCR 텍스트 추출
      - 추출 후 start_text_analysis() 호출
    """
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        return

    # Mock: 파일 분석은 추후 구현
    job.status = JobStatus.failed
    db.commit()


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
