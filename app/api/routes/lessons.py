from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.services.lesson_service import LessonService
from app.api.schemas.lesson_schemas import LessonResponse
from app.services.user_service import UserService


router = APIRouter()

@router.get("/today/{user_id}", response_model=LessonResponse)
async def get_today_lesson(user_id: int, db: Session = Depends(get_db)):
    """
    获取用户今日课程
    """
    lesson_service = LessonService(db)
    user_service = UserService(db)  # 需要导入UserService
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    lesson = lesson_service.get_lesson_by_day(user.current_lesson_day)
    if not lesson:
        raise HTTPException(status_code=404, detail="今日课程不存在")
    
    return lesson

@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    """
    根据ID获取课程
    """
    lesson_service = LessonService(db)
    lesson = await lesson_service.get_lesson_by_id(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课程不存在")
    return lesson

@router.get("/day/{day_number}", response_model=LessonResponse)
async def get_lesson_by_day(day_number: int, db: Session = Depends(get_db)):
    """
    根据天数获取课程
    """
    lesson_service = LessonService(db)
    lesson = lesson_service.get_lesson_by_day(day_number)
    if not lesson:
        raise HTTPException(status_code=404, detail="课程不存在")
    return lesson