from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_

from app.models.conversation_context import ConversationContext
from app.repositories.base import BaseRepository

class ContextRepository(BaseRepository[ConversationContext]):
    """对话上下文Repository，管理对话历史记录"""
    
    def __init__(self, db: Session):
        super().__init__(db, ConversationContext)
    
    def get_by_session(self, session_id: int, limit: int = None) -> List[ConversationContext]:
        """
        根据会话ID获取上下文记录，按时间正序排列
        
        Args:
            session_id: 会话ID
            limit: 限制返回记录数
            
        Returns:
            List[ConversationContext]: 上下文记录列表
        """
        query = self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id
        ).order_by(asc(ConversationContext.created_at))  # 按创建时间正序排列
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def get_count_by_session(self, session_id: int) -> int:
        """
        获取会话的上下文记录数量
        
        Args:
            session_id: 会话ID
            
        Returns:
            int: 记录数量
        """
        return self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id
        ).count()
    
    def get_by_session_and_step(self, session_id: int, step: str) -> List[ConversationContext]:
        """
        根据会话ID和教学步骤获取上下文记录
        
        Args:
            session_id: 会话ID
            step: 教学步骤
            
        Returns:
            List[ConversationContext]: 上下文记录列表
        """
        return self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id,
            ConversationContext.step == step
        ).order_by(asc(ConversationContext.created_at)).all()
    
    def get_recent_by_session(self, session_id: int, limit: int = 10) -> List[ConversationContext]:
        """
        获取会话最近的上下文记录
        
        Args:
            session_id: 会话ID
            limit: 限制返回记录数
            
        Returns:
            List[ConversationContext]: 最近的上下文记录列表
        """
        return self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id
        ).order_by(desc(ConversationContext.created_at)).limit(limit).all()
    
    def get_by_role(self, session_id: int, role: str) -> List[ConversationContext]:
        """
        根据角色获取上下文记录
        
        Args:
            session_id: 会话ID
            role: 角色 (user, assistant, system)
            
        Returns:
            List[ConversationContext]: 上下文记录列表
        """
        return self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id,
            ConversationContext.role == role
        ).order_by(asc(ConversationContext.created_at)).all()
    
    def get_system_prompts(self, session_id: int) -> List[ConversationContext]:
        """
        获取会话的系统提示词
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[ConversationContext]: 系统提示词记录列表
        """
        return self.get_by_role(session_id, "system")
    
    def get_user_messages(self, session_id: int) -> List[ConversationContext]:
        """
        获取用户消息
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[ConversationContext]: 用户消息记录列表
        """
        return self.get_by_role(session_id, "user")
    
    def get_assistant_messages(self, session_id: int) -> List[ConversationContext]:
        """
        获取助手消息
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[ConversationContext]: 助手消息记录列表
        """
        return self.get_by_role(session_id, "assistant")
    
    def delete_by_session(self, session_id: int) -> int:
        """
        删除会话的所有上下文记录
        
        Args:
            session_id: 会话ID
            
        Returns:
            int: 删除的记录数量
        """
        result = self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id
        ).delete()
        self.db.commit()
        return result
    
    def delete_old_contexts(self, session_id: int, keep_count: int) -> int:
        """
        删除旧的上下文记录，只保留指定数量的最新记录
        
        Args:
            session_id: 会话ID
            keep_count: 要保留的记录数量
            
        Returns:
            int: 删除的记录数量
        """
        # 获取要保留的最新记录的ID
        keep_records = self.db.query(ConversationContext.id).filter(
            ConversationContext.session_id == session_id
        ).order_by(desc(ConversationContext.created_at)).limit(keep_count).all()
        
        keep_ids = [record[0] for record in keep_records]
        
        # 删除不在保留列表中的记录
        if keep_ids:
            result = self.db.query(ConversationContext).filter(
                ConversationContext.session_id == session_id,
                ConversationContext.id.notin_(keep_ids)
            ).delete()
        else:
            result = 0
            
        self.db.commit()
        return result
    
    def get_context_statistics(self, session_id: int) -> Dict[str, Any]:
        """
        获取上下文统计信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 统计信息
        """
        total_count = self.get_count_by_session(session_id)
        contexts = self.get_by_session(session_id)
        
        # 角色分布统计
        role_counts = {}
        # 步骤分布统计
        step_counts = {}
        # token使用统计
        total_tokens = 0
        
        for context in contexts:
            # 统计角色分布
            role = context.role
            role_counts[role] = role_counts.get(role, 0) + 1
            
            # 统计步骤分布
            step = context.step
            step_counts[step] = step_counts.get(step, 0) + 1
            
            # 统计token使用
            total_tokens += context.tokens_used or 0
        
        return {
            "total_messages": total_count,
            "role_distribution": role_counts,
            "step_distribution": step_counts,
            "total_tokens_used": total_tokens,
            "average_tokens_per_message": total_tokens / total_count if total_count > 0 else 0
        }
    
    def get_tokens_usage_by_session(self, session_id: int) -> int:
        """
        获取会话的token使用总量
        
        Args:
            session_id: 会话ID
            
        Returns:
            int: token使用总量
        """
        result = self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id
        ).all()
        
        return sum(context.tokens_used or 0 for context in result)
    
    def get_tokens_usage_by_user(self, user_id: int, start_date: datetime = None, end_date: datetime = None) -> int:
        """
        获取用户的token使用总量
        
        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            int: token使用总量
        """
        # 需要通过会话表关联用户
        from app.models.session import Session
        
        query = self.db.query(ConversationContext).join(
            Session, ConversationContext.session_id == Session.id
        ).filter(
            Session.user_id == user_id
        )
        
        # 添加时间范围过滤
        if start_date:
            query = query.filter(ConversationContext.created_at >= start_date)
        if end_date:
            query = query.filter(ConversationContext.created_at <= end_date)
        
        contexts = query.all()
        return sum(context.tokens_used or 0 for context in contexts)
    
    def cleanup_old_sessions_contexts(self, days: int = 30) -> int:
        """
        清理旧会话的上下文记录
        
        Args:
            days: 保留天数
            
        Returns:
            int: 删除的记录数量
        """
        from app.models.session import Session
        
        # 获取需要清理的会话ID
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_sessions = self.db.query(Session.id).filter(
            Session.created_at < cutoff_date
        ).all()
        
        old_session_ids = [session[0] for session in old_sessions]
        
        if not old_session_ids:
            return 0
        
        # 删除这些会话的上下文记录
        result = self.db.query(ConversationContext).filter(
            ConversationContext.session_id.in_(old_session_ids)
        ).delete()
        
        self.db.commit()
        return result
    
    def search_contexts(self, session_id: int, keyword: str, role: str = None) -> List[ConversationContext]:
        """
        搜索上下文内容
        
        Args:
            session_id: 会话ID
            keyword: 搜索关键词
            role: 角色过滤
            
        Returns:
            List[ConversationContext]: 匹配的上下文记录列表
        """
        query = self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id,
            ConversationContext.content.ilike(f"%{keyword}%")
        )
        
        if role:
            query = query.filter(ConversationContext.role == role)
            
        return query.order_by(asc(ConversationContext.created_at)).all()
    
    def get_contexts_by_date_range(self, session_id: int, start_date: datetime, end_date: datetime) -> List[ConversationContext]:
        """
        根据日期范围获取上下文记录
        
        Args:
            session_id: 会话ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[ConversationContext]: 上下文记录列表
        """
        return self.db.query(ConversationContext).filter(
            ConversationContext.session_id == session_id,
            ConversationContext.created_at >= start_date,
            ConversationContext.created_at <= end_date
        ).order_by(asc(ConversationContext.created_at)).all()