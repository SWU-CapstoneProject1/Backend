from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.settings import UserSettings

router = APIRouter()


class SettingsResponse(BaseModel):
    session_key: str
    risk_sensitivity: int = 50
    notifications: bool = False
    theme: str = "system"
    exclude_personal_data: bool = False

    class Config:
        from_attributes = True


class SettingsUpdateRequest(BaseModel):
    risk_sensitivity: Optional[int] = None   # 0 ~ 100
    notifications: Optional[bool] = None
    theme: Optional[str] = None              # light / dark / system
    exclude_personal_data: Optional[bool] = None


@router.get(
    "/settings/{session_key}",
    response_model=SettingsResponse,
    summary="사용자 설정 조회",
)
def get_settings(session_key: str, db: Session = Depends(get_db)):
    row = db.query(UserSettings).filter(UserSettings.session_key == session_key).first()
    if row is None:
        # 없으면 기본값 반환
        return SettingsResponse(session_key=session_key)
    return SettingsResponse(
        session_key=row.session_key,
        risk_sensitivity=row.risk_sensitivity if row.risk_sensitivity is not None else 50,
        notifications=row.notifications if row.notifications is not None else False,
        theme=row.theme or "system",
        exclude_personal_data=row.exclude_personal_data if row.exclude_personal_data is not None else False,
    )


@router.put(
    "/settings/{session_key}",
    response_model=SettingsResponse,
    summary="사용자 설정 저장/수정",
)
def update_settings(session_key: str, body: SettingsUpdateRequest, db: Session = Depends(get_db)):
    if body.risk_sensitivity is not None and not (0 <= body.risk_sensitivity <= 100):
        raise HTTPException(status_code=400, detail="risk_sensitivity는 0~100 사이여야 합니다.")

    row = db.query(UserSettings).filter(UserSettings.session_key == session_key).first()
    if row is None:
        row = UserSettings(session_key=session_key)
        db.add(row)

    if body.risk_sensitivity is not None:
        row.risk_sensitivity = body.risk_sensitivity
    if body.notifications is not None:
        row.notifications = body.notifications
    if body.theme is not None:
        row.theme = body.theme
    if body.exclude_personal_data is not None:
        row.exclude_personal_data = body.exclude_personal_data

    db.commit()
    db.refresh(row)

    return SettingsResponse(
        session_key=row.session_key,
        risk_sensitivity=row.risk_sensitivity,
        notifications=row.notifications,
        theme=row.theme,
        exclude_personal_data=row.exclude_personal_data,
    )
