from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, index=True)
    service_name = Column(String, default="")
    session_key = Column(String, index=True, default="")

    total_clauses = Column(Integer)
    high_risk = Column(Integer)
    medium_risk = Column(Integer)
    low_risk = Column(Integer)
    overall_risk_ratio = Column(Float)

    result_json = Column(Text)  # 전체 분석 결과 저장

    created_at = Column(DateTime(timezone=True), server_default=func.now())