from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.sentence import Sentence
from app.repositories.base import BaseRepository


class SentenceRepository(BaseRepository[Sentence]):
    """
    句子Repository类，管理句子数据的访问操作
    """
    
    def __init__(self, db: Session):
        """
        初始化SentenceRepository
        
        Args:
            db: SQLAlchemy会话对象
        """
        super().__init__(db, Sentence)
    
    def get_all_sentences(self) -> List[Sentence]:
        """
        获取所有句子
        
        Returns:
            List[Sentence]: 所有句子的列表
        """
        return self.db.query(Sentence).all()
    
    def get_sentences_by_ids(self, sentence_ids: List[int]) -> List[Sentence]:
        """
        根据ID列表获取句子
        
        Args:
            sentence_ids: 句子ID列表
            
        Returns:
            List[Sentence]: 句子列表
        """
        return self.db.query(Sentence).filter(Sentence.id.in_(sentence_ids)).all()
    
    def search_sentences(self, keyword: str) -> List[Sentence]:
        """
        根据关键词搜索句子（中英文搜索）
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Sentence]: 匹配的句子列表
        """
        return self.db.query(Sentence).filter(
            or_(
                Sentence.sentence_english.ilike(f"%{keyword}%"),
                Sentence.sentence_chinese.ilike(f"%{keyword}%"),
                Sentence.description.ilike(f"%{keyword}%")
            )
        ).all()
    
    def create_sentence(self, sentence_english: str, sentence_chinese: str, description: str = None) -> Sentence:
        """
        创建新句子
        
        Args:
            sentence_english: 英文句子
            sentence_chinese: 中文句子
            description: 句子描述（可选）
            
        Returns:
            Sentence: 创建的句子对象
        """
        sentence = Sentence(
            sentence_english=sentence_english,
            sentence_chinese=sentence_chinese,
            description=description
        )
        self.db.add(sentence)
        self.db.commit()
        self.db.refresh(sentence)
        return sentence
    
    def update_sentence(self, sentence_id: int, **kwargs) -> Optional[Sentence]:
        """
        更新句子信息
        
        Args:
            sentence_id: 句子ID
            **kwargs: 要更新的字段和值
            
        Returns:
            Optional[Sentence]: 更新后的句子对象，如果不存在则返回None
        """
        return super().update(sentence_id, **kwargs)
    
    def delete_sentence(self, sentence_id: int) -> bool:
        """
        删除句子
        
        Args:
            sentence_id: 句子ID
            
        Returns:
            bool: 是否删除成功
        """
        sentence = self.get_by_id(sentence_id)
        if sentence:
            self.db.delete(sentence)
            self.db.commit()
            return True
        return False
    
    def batch_create_sentences(self, sentences_data: List[dict]) -> List[Sentence]:
        """
        批量创建句子
        
        Args:
            sentences_data: 句子数据列表，每个元素包含sentence_english, sentence_chinese, description
            
        Returns:
            List[Sentence]: 创建的句子对象列表
        """
        sentences = [
            Sentence(
                sentence_english=data.get('sentence_english'),
                sentence_chinese=data.get('sentence_chinese'),
                description=data.get('description')
            )
            for data in sentences_data
        ]
        self.db.add_all(sentences)
        self.db.commit()
        return sentences