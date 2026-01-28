import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.user_repo = UserRepository(db)
        logger.info("会话服务初始化完成")

    def create_session(self, user_id: int, lesson_id: Optional[int] = None) -> SessionModel:
        """创建新的教学会话"""
        # 检查用户是否存在
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")

        # 创建会话
        session_data = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "status": "active",
            "current_step": "introduction"
        }

        session = self.session_repo.create(**session_data)
        logger.info(f"创建新会话: {session.id}, 用户{user_id}")

        return session

    def get_session(self, session_id: int) -> Optional[SessionModel]:
        """获取会话信息"""
        return self.session_repo.get_by_id(session_id)

    def update_session_step(self, session_id: int, step: str) -> Optional[SessionModel]:
        """更新会话的当前步骤"""
        session = self.session_repo.get_by_id(session_id)
        if session:
            session.current_step = step
            self.db.commit()
            self.db.refresh(session)
            logger.debug(f"更新会话步骤: {session_id} -> {step}")
        return session

    def end_session(self, session_id: int, status: str = "completed") -> bool:
        """结束会话"""
        session = self.session_repo.get_by_id(session_id)
        if session:
            session.status = status
            session.end_time = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"会话结束: {session_id}, 状态: {status}")
            return True
        return False

    def get_user_sessions(self, user_id: int, limit: int = 10) -> List[SessionModel]:
        """获取用户的会话历史"""
        return self.session_repo.get_user_sessions(user_id, limit)

    
    def update_session_status(self, session_id: int, status: str) -> bool:
        """更新会话状态"""
        session = self.session_repo.get_by_id(session_id)
        if session:
            session.status = status
            self.db.commit()
            self.db.refresh(session)
            logger.debug(f"更新会话状态: {session_id} -> {status}")
        return session
 


    # def cleanup_inactive_sessions(self, hours: int = 24) -> int:
    #     """清理非活跃会话（超过指定小时）"""
    #     from datetime import datetime, timedelta
    #     cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
    #     inactive_sessions = self.session_repo.get_sessions_before_time(cutoff_time, status="active")
    #     count = 0
        
    #     for session in inactive_sessions:
    #         session.status = "timeout"
    #         session.end_time = datetime.utcnow()
    #         count += 1
            
    #     if count > 0:
    #         self.db.commit()
    #         logger.info(f"清理了 {count} 个非活跃会话")
            
    #     return count