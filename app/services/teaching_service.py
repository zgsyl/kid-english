import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from sqlalchemy.orm import Session

from app.agents.teaching_agent import TeachingAgent
from app.agents.state_machine import TeachingStep
from app.services.context_service import ContextService
from app.services.user_service import UserService
from app.services.lesson_service import LessonService
from app.services.record_service import RecordService
from app.config.settings import settings

logger = logging.getLogger(__name__)


class TeachingService:
    """教学服务，整合所有教学相关功能"""
    
    def __init__(self, db: Session):
        self.db = db
        self.context_service = ContextService(db)
        self.user_service = UserService(db)
        self.lesson_service = LessonService(db)
        self.record_service = RecordService(db)
        
        # 活跃的教学智能体实例 {session_id: TeachingAgent}
        self.active_agents: Dict[int, TeachingAgent] = {}
        
        logger.info("教学服务初始化完成")

    async def start_teaching_session(self, user_id: int, session_id: int, lesson_id: int) -> Dict[str, Any]:
        """
        开始新的教学会话
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            lesson_id: 课程ID
            
        Returns:
            Dict: 教学响应消息
        """
        try:
            # 获取课程内容
            lesson =  self.lesson_service.get_lesson_by_id(lesson_id)
            if not lesson:
                raise ValueError(f"课程不存在: {lesson_id}")
            
            # 创建教学智能体
            agent = TeachingAgent(
                user_id=user_id,
                session_id=session_id,
                lesson_content=lesson.to_dict(),
                db_session=self.db
            )
            
            # 保存智能体实例
            self.active_agents[session_id] = agent
            
            # 开始教学
            response =  await agent.start_teaching()
            
            logger.info(f"教学会话开始: 用户{user_id}, 会话{session_id}, 课程{lesson_id}")
            return response
            
        except Exception as e:
            logger.error(f"开始教学会话失败: {e}")
            return self._build_error_message(f"开始教学失败: {str(e)}")

    def process_user_message(self, session_id: int, user_input: str) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            session_id: 会话ID
            user_input: 用户输入文本
            
        Returns:
            Dict: 教学响应消息
        """
        try:
            agent = self.active_agents.get(session_id)
            if not agent:
                return self._build_error_message("会话不存在或已结束")
            
            # 处理用户输入
            response =  agent.process_user_input(user_input=user_input)
            
            # 检查教学是否完成
            if agent.is_teaching_complete():
                 self._handle_teaching_completion(agent)
            
            logger.debug(f"处理用户消息: 会话{session_id}, 输入: {user_input[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"处理用户消息失败: {e}")
            return self._build_error_message(f"处理消息失败: {str(e)}")

    async def process_timeout(self, session_id: int, step: str) -> Dict[str, Any]:
        """
        处理超时事件
        
        Args:
            session_id: 会话ID
            step: 超时的教学步骤
            
        Returns:
            Dict: 教学响应消息
        """
        try:
            agent = self.active_agents.get(session_id)
            if not agent:
                return self._build_error_message("会话不存在或已结束")
            
            # 处理超时
            response = await agent.process_user_input(is_timeout=True)
            
            # 检查教学是否完成
            if agent.is_teaching_complete():
                await self._handle_teaching_completion(agent)
            
            logger.info(f"处理超时事件: 会话{session_id}, 步骤: {step}")
            return response
            
        except Exception as e:
            logger.error(f"处理超时事件失败: {e}")
            return self._build_error_message(f"处理超时失败: {str(e)}")

    async def _handle_teaching_completion(self, agent: TeachingAgent):
        """
        处理教学完成后的逻辑
        """
        try:
            # 获取学习问题记录
            learning_issues = agent.get_learning_issues()
            
            if learning_issues:
                # 记录学习问题
                self.record_service.record_learning_issues(
                    user_id=agent.user_id,
                    session_id=agent.session_id,
                    learning_issues=learning_issues
                )
                
                # 更新用户复习清单
                for issue in learning_issues:
                    await self.user_service._add_to_review_list(
                        agent.user_id, issue["sentence_content"]
                    )
            
            # 更新用户学习进度
            self.user_service.update_user_learning_progress(
                agent.user_id,
                {"session_id": agent.session_id, "completed": True}
            )
            
            # 检查是否应该推进到下一课程
            if not learning_issues:  # 如果没有学习问题，推进课程
                await self.user_service.advance_user_lesson(agent.user_id)
            
            # 清理教学智能体
            self.active_agents.pop(agent.session_id, None)
            
            logger.info(f"教学完成: 用户{agent.user_id}, 会话{agent.session_id}, "
                       f"学习问题: {len(learning_issues)}个")
            
        except Exception as e:
            logger.error(f"处理教学完成逻辑失败: {e}")

    async def end_teaching_session(self, session_id: int) -> bool:
        """
        结束教学会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功结束
        """
        try:
            agent = self.active_agents.get(session_id)
            if agent:
                # 记录未完成的学习问题
                learning_issues = agent.get_learning_issues()
                if learning_issues:
                    await self.record_service.record_learning_issues(
                        user_id=agent.user_id,
                        session_id=session_id,
                        learning_issues=learning_issues
                    )
                
                # 清理智能体实例
                self.active_agents.pop(session_id, None)
                
                # 更新会话状态
                # 这里需要调用会话服务更新状态
                logger.info(f"教学会话手动结束: {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"结束教学会话失败: {e}")
            return False

    async def get_session_status(self, session_id: int) -> Dict[str, Any]:
        """
        获取会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 会话状态信息
        """
        try:
            agent = self.active_agents.get(session_id)
            if not agent:
                return {"status": "not_found", "message": "会话不存在"}
            
            state_data = agent.state_machine.get_state_data()
            
            return {
                "status": "active",
                "session_id": session_id,
                "user_id": agent.user_id,
                "current_step": state_data["current_step"],
                "teaching_progress": self._calculate_teaching_progress(state_data),
                "learning_issues_count": state_data["learning_issues_count"],
                "is_completed": agent.is_teaching_complete()
            }
            
        except Exception as e:
            logger.error(f"获取会话状态失败: {e}")
            return {"status": "error", "message": str(e)}

    def _calculate_teaching_progress(self, state_data: Dict[str, Any]) -> float:
        """
        计算教学进度
        
        Args:
            state_data: 状态数据
            
        Returns:
            float: 进度百分比 (0-100)
        """
        step_weights = {
            "introduction": 10,
            "reading_1": 25,
            "reading_2": 40,
            "exam_1": 60,
            "exam_2": 80,
            "summary": 100,
            "completed": 100
        }
        
        current_step = state_data["current_step"]
        return step_weights.get(current_step, 0)

    def _build_error_message(self, error_msg: str) -> Dict[str, Any]:
        """构建错误消息"""
        return {
            "type": "error",
            "content": error_msg,
            "timestamp": self._get_current_timestamp()
        }

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.utcnow().isoformat() + "Z"

    async def cleanup_inactive_sessions(self, timeout_minutes: int = 30) -> int:
        """
        清理非活跃会话
        
        Args:
            timeout_minutes: 超时时间（分钟）
            
        Returns:
            int: 清理的会话数量
        """
        try:
            # 这里需要实现会话活跃度检查逻辑
            # 暂时返回0，实际实现需要根据具体需求
            return 0
            
        except Exception as e:
            logger.error(f"清理非活跃会话失败: {e}")
            return 0