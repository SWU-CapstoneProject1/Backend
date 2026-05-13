import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analysis import AnalysisResult
from app.models.models import AnalysisJob, Bookmark
from app.schemas.schemas import BookmarkRequest, BookmarkResponse

router = APIRouter()


@router.post(
    "/bookmark",
    response_model=BookmarkResponse,
    responses={400: {"description": "잘못된 요청"}},
    summary="보관함 저장",
)
def save_bookmark(req: BookmarkRequest, db: Session = Depends(get_db)):
    if not req.job_id or not req.job_id.strip():
        raise HTTPException(status_code=400, detail="job_id를 입력해주세요")
    if not req.session_key or not req.session_key.strip():
        raise HTTPException(status_code=400, detail="session_key를 입력해주세요")

    try:
        uuid.UUID(req.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="job_id 형식이 올바르지 않습니다")

    exists = (
        db.query(AnalysisResult).filter(AnalysisResult.id == req.job_id).first()
        or db.query(AnalysisJob).filter(AnalysisJob.id == req.job_id).first()
    )
    if not exists:
        raise HTTPException(status_code=404, detail="저장할 분석 결과를 찾을 수 없습니다")

    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.job_id == req.job_id, Bookmark.session_key == req.session_key)
        .first()
    )
    if bookmark is None:
        bookmark = Bookmark(job_id=req.job_id, session_key=req.session_key)
        db.add(bookmark)
        db.commit()

    return BookmarkResponse(success=True, message="저장되었습니다")
