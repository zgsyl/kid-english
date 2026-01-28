from sqlalchemy import Column, String, Integer, Text, Boolean
from .base import BaseModel
from datetime import datetime

"""
句子模型  
句子的中文和英文，以及描述
"""
class Sentence(BaseModel):
    __tablename__ = "sentences"
    sentence_english = Column(String(200), nullable=False)
    sentence_chinese = Column(String(200), nullable=False)
    description = Column(Text)
  
    def to_dict(self):
        return {
            "id": self.id,
            "sentence_english": self.sentence_english,
            "sentence_chinese": self.sentence_chinese,
            "description": self.description
        }