from typing import List, Optional, TypeVar, Generic, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """基础Repository类，提供通用的CRUD操作"""
    
    def __init__(self, db: Session, model_class: T):
        self.db = db
        self.model_class = model_class
    
    def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取记录"""
        return self.db.query(self.model_class).filter(self.model_class.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """获取所有记录（分页）"""
        return self.db.query(self.model_class).offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> T:
        """创建新记录"""
        instance = self.model_class(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """更新记录"""
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            self.db.commit()
            self.db.refresh(instance)
        return instance
    
    def delete(self, id: int) -> bool:
        """删除记录"""
        instance = self.get_by_id(id)
        if instance:
            self.db.delete(instance)
            self.db.commit()
            return True
        return False
    
    def filter_by(self, **filters) -> List[T]:
        """根据条件过滤记录"""
        query = self.db.query(self.model_class)
        for attr, value in filters.items():
            if hasattr(self.model_class, attr):
                query = query.filter(getattr(self.model_class, attr) == value)
        return query.all()
    
    def get_first_by(self, **filters) -> Optional[T]:
        """根据条件获取第一条记录"""
        query = self.db.query(self.model_class)
        for attr, value in filters.items():
            if hasattr(self.model_class, attr):
                query = query.filter(getattr(self.model_class, attr) == value)
        return query.first()