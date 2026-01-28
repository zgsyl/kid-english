import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.conversation_context import ConversationContext
from app.repositories.context_repository import ContextRepository
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ContextService:
    """上下文管理服务，负责维护对话上下文"""
    
    def __init__(self, db: Session):
        self.db = db
        self.context_repo = ContextRepository(db)
        self.max_context_length = settings.MAX_CONTEXT_LENGTH
        logger.info("上下文服务初始化完成")
    
    def get_session_context(self, session_id: int, include_system: bool = True) -> List[Dict[str, str]]:
        """
        获取会话的上下文消息
        
        Args:
            session_id: 会话ID
            include_system: 是否包含系统消息
            
        Returns:
            List[Dict]: 上下文消息列表，格式为 [{"role": "user", "content": "..."}]
        """
        try:
            # 获取所有上下文记录
            all_contexts = self.context_repo.get_by_session(session_id)
            
            if not all_contexts:
                return []
            
            # 转换格式
            messages = []
            for context in all_contexts:
                # 如果不包含系统消息，则跳过系统角色
                if not include_system and context.role == "system":
                    #logger.debug(f"会话 {session_id} 上下文包含系统消息，设置 include_system=True 才能包含")
                    continue
                    
                messages.append({
                    "role": context.role,
                    "content": context.content
                })
            
            # 如果上下文太长，进行截断
            if len(messages) > self.max_context_length:
                # 保留系统消息和最近的对话
                system_messages = [msg for msg in messages if msg["role"] == "system"]
                recent_messages = messages[-self.max_context_length:]
                
                # 如果系统消息不在最近消息中，则添加
                for sys_msg in system_messages:
                    if sys_msg not in recent_messages:
                        recent_messages.insert(0, sys_msg)
                
                messages = recent_messages
                logger.debug(f"会话 {session_id} 上下文已截断，保留 {len(messages)} 条消息")
            
            logger.debug(f"获取会话 {session_id} 的上下文，共 {len(messages)} 条消息")
            return messages
            
        except Exception as e:
            logger.error(f"获取会话 {session_id} 上下文失败: {e}")
            return []
    
    def add_to_context(self, session_id: int, role: str, content: str, 
                           step: str, tokens_used: int = 0) -> ConversationContext:
        """
        添加消息到上下文
        
        Args:
            session_id: 会话ID
            role: 角色（user/assistant/system）
            content: 内容
            step: 教学步骤
            tokens_used: 使用的token数量
            
        Returns:
            ConversationContext: 保存的上下文记录
        """
        try:
            context = self.context_repo.create(
                session_id=session_id,
                role=role,
                content=content,
                step=step,
                tokens_used=tokens_used
            )
            
            # 更新会话的上下文计数
            self._update_session_context_count(session_id)
            
            logger.debug(f"会话 {session_id} 添加上下文: {role} - {step}")
            return context
            
        except Exception as e:
            logger.error(f"添加上下文失败: {e}")
            raise
    
    def add_system_prompt(self, session_id: int, content: str, step: str = "system") -> ConversationContext:
        """
        添加系统提示词到上下文
        
        Args:
            session_id: 会话ID
            content: 系统提示词内容
            step: 步骤标识
            
        Returns:
            ConversationContext: 保存的上下文记录
        """
        return  self.add_to_context(session_id, "system", content, step)
    
    def add_user_message(self, session_id: int, content: str, step: str) -> ConversationContext:
        """
        添加用户消息到上下文
        
        Args:
            session_id: 会话ID
            content: 用户消息内容
            step: 教学步骤
            
        Returns:
            ConversationContext: 保存的上下文记录
        """
        return  self.add_to_context(session_id, "user", content, step)
    
    def add_assistant_message(self, session_id: int, content: str, step: str) -> ConversationContext:
        """
        添加助手消息到上下文
        
        Args:
            session_id: 会话ID
            content: 助手消息内容
            step: 教学步骤
            
        Returns:
            ConversationContext: 保存的上下文记录
        """
        return  self.add_to_context(session_id, "assistant", content, step)
    
    def clear_context(self, session_id: int) -> bool:
        """清空会话的上下文"""
        try:
            deleted_count = self.context_repo.delete_by_session(session_id)
            logger.info(f"会话 {session_id} 上下文已清空，删除 {deleted_count} 条记录")
            return True
        except Exception as e:
            logger.error(f"清空会话 {session_id} 上下文失败: {e}")
            return False
    
    def get_context_count(self, session_id: int) -> int:
        """获取会话的上下文数量"""
        return self.context_repo.get_count_by_session(session_id)
    
    def prune_old_contexts(self, session_id: int, keep_count: int = None) -> bool:
        """
        修剪旧的上下文，只保留指定数量的最新记录
        
        Args:
            session_id: 会话ID
            keep_count: 要保留的记录数量，默认为配置的最大长度
            
        Returns:
            bool: 是否成功
        """
        try:
            if keep_count is None:
                keep_count = self.max_context_length
                
            deleted_count = self.context_repo.delete_old_contexts(session_id, keep_count)
            logger.debug(f"会话 {session_id} 上下文已修剪，删除 {deleted_count} 条旧记录")
            return True
        except Exception as e:
            logger.error(f"修剪会话 {session_id} 上下文失败: {e}")
            return False
    
    def get_context_statistics(self, session_id: int) -> Dict[str, Any]:
        """获取上下文统计信息"""
        try:
            return self.context_repo.get_context_statistics(session_id)
        except Exception as e:
            logger.error(f"获取上下文统计失败: {e}")
            return {}
    
    def get_tokens_usage(self, session_id: int) -> int:
        """获取会话的token使用量"""
        try:
            return self.context_repo.get_tokens_usage_by_session(session_id)
        except Exception as e:
            logger.error(f"获取token使用量失败: {e}")
            return 0
    
    def search_context_content(self, session_id: int, keyword: str, role: str = None) -> List[Dict[str, Any]]:
        """
        搜索上下文内容
        
        Args:
            session_id: 会话ID
            keyword: 搜索关键词
            role: 角色过滤
            
        Returns:
            List[Dict]: 匹配的上下文内容列表
        """
        try:
            contexts = self.context_repo.search_contexts(session_id, keyword, role)
            return [
                {
                    "id": context.id,
                    "role": context.role,
                    "content": context.content,
                    "step": context.step,
                    "created_at": context.created_at.isoformat() if context.created_at else None
                }
                for context in contexts
            ]
        except Exception as e:
            logger.error(f"搜索上下文内容失败: {e}")
            return []
    
    def get_contexts_by_step(self, session_id: int, step: str) -> List[Dict[str, Any]]:
        """
        根据教学步骤获取上下文
        
        Args:
            session_id: 会话ID
            step: 教学步骤
            
        Returns:
            List[Dict]: 上下文记录列表
        """
        try:
            contexts = self.context_repo.get_by_session_and_step(session_id, step)
            return [
                {
                    "id": context.id,
                    "role": context.role,
                    "content": context.content,
                    "created_at": context.created_at.isoformat() if context.created_at else None
                }
                for context in contexts
            ]
        except Exception as e:
            logger.error(f"获取步骤上下文失败: {e}")
            return []
    
    def cleanup_old_contexts(self, days: int = 30) -> int:
        """
        清理旧会话的上下文记录
        
        Args:
            days: 保留天数
            
        Returns:
            int: 删除的记录数量
        """
        try:
            return self.context_repo.cleanup_old_sessions_contexts(days)
        except Exception as e:
            logger.error(f"清理旧上下文失败: {e}")
            return 0
    
    def _update_session_context_count(self, session_id: int):
        """更新会话的上下文计数"""
        try:
            from app.repositories.session_repository import SessionRepository
            session_repo = SessionRepository(self.db)
            
            count =  self.get_context_count(session_id)
            session_repo.update(session_id, context_count=count)
            
        except Exception as e:
            logger.error(f"更新会话上下文计数失败: {e}")