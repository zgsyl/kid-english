from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from .base import BaseModel
from datetime import datetime
import pytz

"""
会话模型  
记录一次教学会话,包括用户ID、课程ID、会话状态、开始时间、结束时间、上下文数量、当前步骤等。
"""
class Session(BaseModel):
    __tablename__ = "sessions"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    status = Column(String(20), default="active")  # active, completed, timeout, error
    #start_time = Column(DateTime, default=datetime.utcnow)
    start_time = Column(DateTime, default=lambda: datetime.now(pytz.utc))

    #end_time = Column(DateTime)
    end_time = Column(DateTime, default=lambda: datetime.now(pytz.utc))

    context_count = Column(Integer, default=0)
    current_step = Column(String(50))  # 当前教学步骤
    
    # 关系定义
    user = relationship("User", backref="sessions")
    lesson = relationship("Lesson", backref="sessions")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "lesson_id": self.lesson_id,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "context_count": self.context_count,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }