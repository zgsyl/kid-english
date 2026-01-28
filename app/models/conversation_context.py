from sqlalchemy import Column, String, Integer, ForeignKey, Text
from .base import BaseModel
from sqlalchemy.orm import relationship



"""
对话上下文模型  
存储一次会话中的对话记录,包括会话ID、角色(用户/助手/系统)、内容、教学步骤、使用的token数等。
"""

class ConversationContext(BaseModel):
    __tablename__ = "conversation_context"

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    step = Column(String(50), nullable=False)  # 教学步骤
    tokens_used = Column(Integer, default=0)

    # 关系定义
    session = relationship("Session", backref="conversation_contexts")

  
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "step": self.step,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }