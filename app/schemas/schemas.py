from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, HttpUrl


# ────────────────────────────────────────────────
# 공통 에러 응답
# ────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Any
    status_code: int


class RiskLevel(str, Enum):
    danger = "danger"
    caution = "caution"
    safe = "safe"


class JobStatus(str, Enum):
    pending = "pending"
    running = "processing"   # 프론트 기대값: 'processing'
    done = "done"
    failed = "failed"


# ────────────────────────────────────────────────
# 분석 요청
# ────────────────────────────────────────────────

class AnalyzeTextRequest(BaseModel):
    """텍스트 직접 붙여넣기 분석 요청"""
    text: str
    service_name: Optional[str] = ""
    session_key: Optional[str] = ""

    class Config:
        json_schema_extra = {
            "example": {
                "text": "제1조 (목적) 이 약관은...",
                "service_name": "카카오",
                "session_key": "uuid-xxxx",
            }
        }


class AnalyzeUrlRequest(BaseModel):
    """URL 입력 분석 요청"""
    url: HttpUrl
    session_key: Optional[str] = ""
    service_name: Optional[str] = ""

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/terms",
                "session_key": "uuid-xxxx",
                "service_name": "서비스명",
            }
        }


# ────────────────────────────────────────────────
# 분석 작업 시작 응답
# ────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    """분석 작업 시작 응답 — job_id 반환"""
    job_id: str
    status: JobStatus
    message: str = "분석이 시작되었습니다"


# ────────────────────────────────────────────────
# 기존 결과 조회 응답
# ────────────────────────────────────────────────

class ClauseOut(BaseModel):
    """조항 단위 결과"""
    id: str
    index: int
    original: str
    risk_level: RiskLevel
    summary: str = ""
    precedents: List["PrecedentOut"] = Field(default_factory=list)


class PrecedentOut(BaseModel):
    """추천 심결례"""
    case_no: str
    title: str
    date: str
    summary: str
    source_url: str
    similarity: float


class ResultResponse(BaseModel):
    """분석 결과 전체 응답"""
    job_id: str
    status: JobStatus
    service_name: str
    risk_score: float
    danger_count: int
    caution_count: int
    safe_count: int
    clauses: List[ClauseOut] = Field(default_factory=list)
    precedents: List[PrecedentOut] = Field(default_factory=list)


# ────────────────────────────────────────────────
# 통계
# ────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_analyses: int
    total_danger: int
    total_services: int


# ────────────────────────────────────────────────
# 보관함
# ────────────────────────────────────────────────

class AnalysisProgressResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress_percent: int
    stage: str
    message: str = ""
    current_clause: int = 0
    total_clauses: int = 0
    current_clause_title: str = ""
    current_clause_preview: str = ""


class BookmarkRequest(BaseModel):
    job_id: str
    session_key: str


class BookmarkResponse(BaseModel):
    success: bool
    message: str


# ────────────────────────────────────────────────
# 즉시 분석 API (/analyze)용 스키마
# ────────────────────────────────────────────────

class TermsAnalyzeRequest(BaseModel):
    text: str
    service_name: Optional[str] = ""
    session_key: Optional[str] = ""

    class Config:
        json_schema_extra = {
            "example": {
                "text": (
                    "제1조(면책)\n"
                    "회사는 회원에게 발생한 손해에 대해 책임지지 않습니다.\n\n"
                    "제2조(약관 변경)\n"
                    "회사는 사전 통지 없이 약관을 변경할 수 있습니다."
                ),
                "service_name": "넷플릭스",
                "session_key": "uuid-xxxx",
            }
        }


class PrecedentCase(BaseModel):
    id: str
    title: str
    score: float
    decision_date: Optional[str] = ""
    case_number: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    preview: Optional[str] = ""


class ClauseAnalysisResult(BaseModel):
    clause_id: int
    title: str
    content: str
    risk_level: str
    risk_score: int
    risk_types: List[str] = Field(default_factory=list)
    matched_rules: List[str] = Field(default_factory=list)
    llm_summary: str
    plain_explanation: str
    legal_rationale: str
    consumer_warning: str
    confidence_note: str
    precedent_cases: List[PrecedentCase] = Field(default_factory=list)


class TermsAnalyzeSummary(BaseModel):
    total_clauses: int
    high_risk: int
    medium_risk: int
    low_risk: int
    overall_risk_ratio: float   # 0.0 ~ 1.0 (프론트 게이지용)
    risk_score: float = 0.0     # 0 ~ 100점
    risk_grade: str = "안전"    # 안전 / 주의 / 위험


class TermsAnalyzeResponse(BaseModel):
    job_id: Optional[str] = None
    summary: TermsAnalyzeSummary
    clauses: List[ClauseAnalysisResult] = Field(default_factory=list)
