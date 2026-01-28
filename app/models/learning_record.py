from sqlalchemy import Column, String, Integer, ForeignKey, Date
from .base import BaseModel


"""
学习记录模型  
存储用户在一次会话中的学习记录,包括用户ID、会话ID、句子内容、句子顺序、记录类型(无重复/错误发音)、记录日期等。
"""

class LearningRecord(BaseModel):
    __tablename__ = "learning_records"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    sentence_content = Column(String(200), nullable=False)
    sentence_order = Column(Integer, nullable=False)  # 1 or 2
    record_type = Column(String(20), nullable=False)  # no_repeat, incorrect_pronunciation
    record_date = Column(Date, nullable=False)