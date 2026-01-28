from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.session import Session as SessionModel
from app.repositories.base import BaseRepository

class SessionRepository(BaseRepository[SessionModel]):
    def __init__(self, db: Session):
        super().__init__(db, SessionModel)
    
    def get_active_session(self, user_id: int) -> Optional[SessionModel]:
        """获取用户的活跃会话"""
        return self.db.query(SessionModel).filter(
            SessionModel.user_id == user_id,
            SessionModel.status == "active"
        ).first()
    
    def get_user_sessions(self, user_id: int, limit: int = 10) -> List[SessionModel]:
        """获取用户的会话历史"""
        return self.db.query(SessionModel).filter(
            SessionModel.user_id == user_id
        ).order_by(SessionModel.created_at.desc()).limit(limit).all()
    
    def get_recent_sessions(self, user_id: int, days: int = 7) -> List[SessionModel]:
        """获取用户最近N天的会话"""
        since_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(SessionModel).filter(
            SessionModel.user_id == user_id,
            SessionModel.created_at >= since_date
        ).order_by(SessionModel.created_at.desc()).all()
    
    def get_last_session(self, user_id: int) -> Optional[SessionModel]:
        """获取用户最后一次会话"""
        return self.db.query(SessionModel).filter(
            SessionModel.user_id == user_id
        ).order_by(SessionModel.created_at.desc()).first()

