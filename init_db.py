"""
DB 테이블 생성 스크립트
최초 1회 실행:
    python init_db.py
"""

from app.core.database import engine, Base

# 기존 모델
from app.models.models import AnalysisJob, Clause, Precedent, ServiceStats

# 새로 추가한 모델
from app.models.analysis import AnalysisResult
from app.models.settings import UserSettings

Base.metadata.create_all(bind=engine)

print("DB 테이블 생성 완료")