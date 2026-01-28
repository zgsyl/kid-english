from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.lesson import Lesson
from app.repositories.base import BaseRepository

class LessonRepository(BaseRepository[Lesson]):
    def __init__(self, db: Session):
        super().__init__(db, Lesson)
    
        """根据天数获取课程"""
    def get_lesson_by_day(self, day_number: int) -> Optional[Lesson]:
        return self.db.query(Lesson).filter(Lesson.day_number == day_number).first()
    
    def get_active_lessons(self) -> List[Lesson]:
        """获取所有活跃课程"""
        return self.db.query(Lesson).filter(Lesson.is_active == True).order_by(Lesson.day_number).all()
    
    def get_lessons_by_day_range(self, start_day: int, end_day: int) -> List[Lesson]:
        """根据天数范围获取课程"""
        return self.db.query(Lesson).filter(
            Lesson.day_number >= start_day,
            Lesson.day_number <= end_day,
            Lesson.is_active == True
        ).order_by(Lesson.day_number).all()