from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.base import BaseRepository




class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_wechat_openid(self, wechat_openid: str) -> Optional[User]:
        """根据微信openid获取用户"""
        return self.db.query(User).filter(User.wechat_openid == wechat_openid).first()
    
    def get_active_users(self) -> List[User]:
        """获取所有活跃用户"""
        return self.db.query(User).filter(User.is_active == True).all()
    
    def update_user_progress(self, user_id: int, **kwargs) -> Optional[User]:
        """更新用户学习进度"""
        user = self.get_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user