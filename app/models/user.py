from sqlalchemy import Column, String, Integer, Boolean, Text
from .base import BaseModel
from datetime import datetime

"""
用户模型  
记录用户信息,包括微信OpenID、昵称、年龄、头像URL、当前学习天数、总学习天数、总会话次数等。
"""
class User(BaseModel):
    __tablename__ = "users"

    wechat_openid = Column(String(100), unique=True, index=True, nullable=False)
    nickname = Column(String(100))
    age = Column(Integer)
    avatar_url = Column(String(200))
    current_lesson_day = Column(Integer, default=1)
    total_learning_days = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "wechat_openid": self.wechat_openid,
            "nickname": self.nickname,
            "age": self.age,
            "avatar_url": self.avatar_url,
            "current_lesson_day": self.current_lesson_day,
            "total_learning_days": self.total_learning_days,
            "total_sessions": self.total_sessions,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }