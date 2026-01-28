import logging
from datetime import date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.repositories.lesson_repository import LessonRepository
import logging

logger = logging.getLogger(__name__)

class LessonService:
    """课程服务，负责课程内容的管理和获取"""

    def __init__(self, db: Session):
        self.db = db
        self.lesson_repo = LessonRepository(db)
        logger.info("课程服务初始化完成")

    def get_lesson_by_day(self, day_number: int) -> Optional[Lesson]:
        """根据天数获取课程"""
        return self.lesson_repo.get_lesson_by_day(day_number)

    def get_today_lesson(self, user_id: int) -> Optional[Lesson]:
        """
        获取用户今日课程
        注意：这里暂时返回固定课程，后续应该根据用户进度和复习需求调整
        """
        # 暂时返回第1天的课程，实际应该根据用户当前进度决定
        # 后续可以结合用户的学习记录和复习清单来动态决定
        return  self.get_lesson_by_day(1)

    def get_all_lessons(self) -> List[Lesson]:
        """获取所有课程"""
        return self.lesson_repo.get_active_lessons()

    def create_lesson(self, day_number: int, sentence1: str, sentence2: str, 
                          description: str = None) -> Lesson:
        """创建新课程"""
        # 检查是否已存在该天数的课程
        existing_lesson =  self.get_lesson_by_day(day_number)
        if existing_lesson:
            raise ValueError(f"第 {day_number} 天的课程已存在")

        lesson_data = {
            "day_number": day_number,
            "sentence1": sentence1,
            "sentence2": sentence2,
            "description": description
        }
        return self.lesson_repo.create(**lesson_data)

    def update_lesson(self, lesson_id: int, **kwargs) -> Optional[Lesson]:
        """更新课程"""
        return self.lesson_repo.update(lesson_id, **kwargs)

    def delete_lesson(self, lesson_id: int) -> bool:
        """删除课程（软删除）"""
        return self.lesson_repo.update(lesson_id, is_active=False) is not None

    def get_lesson_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """根据ID获取课程"""
        return self.lesson_repo.get_by_id(lesson_id)

    def get_lessons_count(self) -> int:
        """获取课程总数"""
        return len(self.lesson_repo.get_active_lessons())

    def get_lesson_range(self, start_day: int, end_day: int) -> List[Lesson]:
        """获取指定天数范围的课程"""
        return self.lesson_repo.get_lessons_by_day_range(start_day, end_day)