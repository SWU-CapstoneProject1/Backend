from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from enum import Enum


class RiskLevel(str, Enum):
    danger  = "danger"
    caution = "caution"
    safe    = "safe"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done    = "done"
    failed  = "failed"


# ────────────────────────────────────────────────
# 분석 요청
# ────────────────────────────────────────────────

class AnalyzeTextRequest(BaseModel):
    """텍스트 직접 붙여넣기 분석 요청"""
    text:         str
    service_name: Optional[str] = ""
    session_key:  Optional[str] = ""

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
    url:         str
    session_key: Optional[str] = ""


# ────────────────────────────────────────────────
# 분석 응답
# ────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    """분석 작업 시작 응답 — job_id 반환"""
    job_id:  str
    status:  JobStatus
    message: str = "분석이 시작되었습니다"


class ClauseOut(BaseModel):
    """조항 단위 결과"""
    id:         str
    index:      int
    original:   str
    risk_level: RiskLevel
    summary:    str = ""


class PrecedentOut(BaseModel):
    """추천 심결례"""
    case_no:    str
    title:      str
    date:       str
    summary:    str
    source_url: str
    similarity: float


class ResultResponse(BaseModel):
    """분석 결과 전체 응답"""
    job_id:       str
    status:       JobStatus
    service_name: str
    risk_score:   float
    danger_count: int
    caution_count:int
    safe_count:   int
    clauses:      List[ClauseOut] = []
    precedents:   List[PrecedentOut] = []


# ────────────────────────────────────────────────
# 통계
# ────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_analyses: int
    total_danger:   int
    total_services: int


# ────────────────────────────────────────────────
# 보관함
# ────────────────────────────────────────────────

class BookmarkRequest(BaseModel):
    job_id:      str
    session_key: str


class BookmarkResponse(BaseModel):
    success: bool
    message: str
