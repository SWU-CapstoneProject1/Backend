from sqlalchemy import Column, String, Integer, Boolean
from app.core.database import Base


class UserSettings(Base):
    """
    사용자 맞춤 설정 저장 테이블

    - session_key 기준으로 설정 관리
    - 로그인 없이도 사용자별 설정 유지 가능
    """

    __tablename__ = "user_settings"

    # 사용자 식별 키 (프론트에서 생성해서 전달)
    session_key = Column(String, primary_key=True, index=True)

    # 위험도 민감도 (0 ~ 100)
    risk_sensitivity = Column(Integer, default=50)

    # 개인정보 관련 조항 제외 여부
    exclude_personal_data = Column(Boolean, default=False)

    # 알림 사용 여부
    notifications = Column(Boolean, default=False)

    # 테마 설정 (light / dark / system)
    theme = Column(String, default="system")