"""
DB 테이블 생성 스크립트
최초 1회 실행: python init_db.py
"""
from app.core.database import engine, Base
from app.models.models import AnalysisJob, Clause, Precedent, ServiceStats

Base.metadata.create_all(bind=engine)
print("✅ DB 테이블 생성 완료")
