from sqlalchemy import Column, String, Integer, Text, Boolean
from .base import BaseModel
from datetime import datetime

"""
课程模型  
记录每天的学习内容，包括课程编号、两个句子、描述和是否激活状态。
"""
class Lesson(BaseModel):
    __tablename__ = "lessons"

    day_number = Column(Integer, nullable=False, unique=True)
    sentence1 = Column(String(200), nullable=False)
    sentence2 = Column(String(200), nullable=False)
    description = Column(Text)

    sentence1_description = Column(Text)
    sentence2_description = Column(Text)

    # user_id = Column(Integer, nullable=False)

    is_active = Column(Boolean, default=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "day_number": self.day_number,
            "sentence1": self.sentence1,
            "sentence2": self.sentence2,
            "description": self.description,
            "sentence1_description": self.sentence1_description,
            "sentence2_description": self.sentence2_description,
            "is_active": self.is_active,
            # "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }