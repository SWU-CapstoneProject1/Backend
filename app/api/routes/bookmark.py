from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import BookmarkRequest, BookmarkResponse

router = APIRouter()


@router.post("/bookmark", response_model=BookmarkResponse, summary="보관함 저장")
def save_bookmark(req: BookmarkRequest, db: Session = Depends(get_db)):
    """
    분석 결과를 보관함에 저장
    - MVP: localStorage 기반 (프론트에서 처리)
    - 이 엔드포인트는 서버 측 저장 확인용
    """
    # MVP에서는 프론트 localStorage 저장이 주 방식
    # 서버 저장은 로그인 기능 구현 후 활성화
    return BookmarkResponse(success=True, message="저장되었습니다")
