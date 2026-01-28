from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel
import pytz




"""
复习列表模型  
存储用户需要复习的句子,包括用户ID、句子内容、添加日期、是否掌握、掌握日期、问题类型(无重复/错误发音/考试失败)等。
"""


class ReviewList(BaseModel):
    __tablename__ = "review_list"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sentence_content = Column(String(200), nullable=False)
    #added_date = Column(DateTime, default=datetime.utcnow)
    added_date = Column(DateTime, default=lambda: datetime.now(pytz.utc))

    mastered = Column(Boolean, default=False)
    mastered_date = Column(DateTime)
    

    issue_type = Column(String(50))  # "no_repeat", "incorrect_pronunciation", "exam_failed"
    last_practiced = Column(DateTime)
    practice_count = Column(Integer, default=0)
    
    # 关系定义
    user = relationship("User", backref="review_items")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sentence_content": self.sentence_content,
            "added_date": self.added_date.isoformat() if self.added_date else None,
            "mastered": self.mastered,
            "mastered_date": self.mastered_date.isoformat() if self.mastered_date else None,
            "issue_type": self.issue_type,
            "last_practiced": self.last_practiced.isoformat() if self.last_practiced else None,
            "practice_count": self.practice_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }