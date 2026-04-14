from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Enum
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class JobStatus(str, enum.Enum):
    pending   = "pending"    # 대기 중
    running   = "running"    # 분석 중
    done      = "done"       # 완료
    failed    = "failed"     # 실패


class RiskLevel(str, enum.Enum):
    danger  = "danger"   # 위험 🔴
    caution = "caution"  # 주의 🟡
    safe    = "safe"     # 정상 🟢


class AnalysisJob(Base):
    """분석 작업 테이블"""
    __tablename__ = "analysis_jobs"

    id           = Column(String, primary_key=True, default=generate_uuid)
    session_key  = Column(String, index=True)           # 비로그인 사용자 식별키
    input_type   = Column(String)                        # url / pdf / text
    input_value  = Column(Text)                          # 입력값 (URL or 텍스트)
    service_name = Column(String, default="")            # 서비스명
    status       = Column(Enum(JobStatus), default=JobStatus.pending)
    risk_score   = Column(Float, default=0.0)            # 0~100 종합 위험도
    danger_count = Column(Integer, default=0)
    caution_count= Column(Integer, default=0)
    safe_count   = Column(Integer, default=0)
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, onupdate=func.now())


class Clause(Base):
    """조항 단위 분석 결과 테이블"""
    __tablename__ = "clauses"

    id           = Column(String, primary_key=True, default=generate_uuid)
    job_id       = Column(String, index=True)            # AnalysisJob.id 참조
    index        = Column(Integer)                       # 조항 순서
    original     = Column(Text)                          # 원문
    risk_level   = Column(Enum(RiskLevel))               # 위험/주의/정상
    summary      = Column(Text, default="")              # LLM 쉬운 요약
    created_at   = Column(DateTime, server_default=func.now())


class Precedent(Base):
    """공정위 심결례 RAG 데이터 테이블"""
    __tablename__ = "precedents"

    id           = Column(String, primary_key=True, default=generate_uuid)
    case_no      = Column(String, index=True)            # 사건번호
    title        = Column(String)                        # 사건명
    date         = Column(String)                        # 의결일
    content      = Column(Text)                          # 본문
    source_url   = Column(String, default="")            # 원문 출처
    created_at   = Column(DateTime, server_default=func.now())


class ServiceStats(Base):
    """서비스 통계 테이블"""
    __tablename__ = "service_stats"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    total_analyses  = Column(Integer, default=0)         # 전체 분석 건수
    total_danger    = Column(Integer, default=0)         # 누적 위험 조항 수
    total_services  = Column(Integer, default=0)         # 분석된 서비스 수
    updated_at      = Column(DateTime, server_default=func.now())
