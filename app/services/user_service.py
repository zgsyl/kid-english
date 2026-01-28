#!/usr/bin/env python3
"""
用户服务模块
处理用户注册、登录、学习进度跟踪、课程分配等核心业务逻辑
"""

import logging
from datetime import datetime, date
from math import log
from re import L
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.user import User
from app.models.lesson import Lesson
from app.models.session import Session as SessionModel
from app.models.learning_record import LearningRecord
from app.models.review_list import ReviewList
from app.repositories.user_repository import UserRepository
from app.repositories.lesson_repository import LessonRepository
from app.repositories.learning_record_repository import LearningRecordRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.session_repository import SessionRepository
from app.services.review_service import ReviewService

"""
UserService
处理用户数据的CRUD操作,包括用户注册、登录、获取今日课程、更新学习进度、管理复习清单等。
"""


logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.lesson_repo = LessonRepository(db)
        self.record_repo = LearningRecordRepository(db)
        self.review_repo = ReviewRepository(db)
        self.session_repo = SessionRepository(db)
        self.review_service = ReviewService(db)
        logger.info("用户服务初始化完成")

    async def register_or_login_user(self, wechat_openid: str, user_info: Dict[str, Any]) -> User:
        """
        用户注册或登录
        - 如果用户不存在，则创建新用户
        - 如果用户已存在，则更新用户信息
        """
        try:
            # 查找现有用户
            existing_user = self.user_repo.get_by_wechat_openid(wechat_openid)
            
            if existing_user:
                # 更新用户信息
                logger.info(f"用户已存在，更新用户信息: {wechat_openid}")
                return  self._update_user_info(existing_user.id, user_info)
            else:
                # 创建新用户
                logger.info(f"创建新用户: {wechat_openid}")
                return  self._create_new_user(wechat_openid, user_info)
                
        except Exception as e:
            logger.error(f"用户注册/登录失败: {e}")
            raise

    def _create_new_user(self, wechat_openid: str, user_info: Dict[str, Any]) -> User:
        """创建新用户"""
        user_data = {
            "wechat_openid": wechat_openid,
            "nickname": user_info.get("nickname", ""),
            "age": user_info.get("age", 0),
            "avatar_url": user_info.get("avatar_url", ""),
            "current_lesson_day": 1,  # 从第一天开始
            "total_learning_days": 0,
            "total_sessions": 0,
            "is_active": True
        }
        
        user = self.user_repo.create(**user_data)
        
        # 初始化用户的学习记录
        self._initialize_user_learning_data(user.id)
        
        logger.info(f"新用户创建成功: {user.id} - {user.nickname}")
        return user

    async def _update_user_info(self, user_id: int, user_info: Dict[str, Any]) -> User:
        """更新用户信息"""
        update_data = {}
        
        if "nickname" in user_info:
            update_data["nickname"] = user_info["nickname"]
        if "age" in user_info:
            update_data["age"] = user_info["age"]
        if "avatar_url" in user_info:
            update_data["avatar_url"] = user_info["avatar_url"]
            
        if update_data:
            user = self.user_repo.update(user_id, **update_data)
            logger.info(f"用户信息更新成功: {user_id}")
            return user
        else:
            return self.user_repo.get_by_id(user_id)

    def _initialize_user_learning_data(self, user_id: int):
        """初始化用户学习数据"""
        # 这里可以添加初始化逻辑，比如创建默认的学习计划等
        logger.info(f"初始化用户学习数据: {user_id}")

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户信息"""
        return self.user_repo.get_by_id(user_id)

    async def get_user_by_openid(self, wechat_openid: str) -> Optional[User]:
        """根据微信openid获取用户信息"""
        return self.user_repo.get_by_wechat_openid(wechat_openid)

    def update_user_learning_progress(self, user_id: int, session_data: Dict[str, Any]):
        """
        更新用户学习进度
        在每次教学会话结束后调用
        """
        try:
            user =  self.get_user_by_id(user_id)
            if not user:
                logger.error(f"用户不存在: {user_id}")
                return

            # 更新学习统计
            update_data = {
                "total_sessions": user.total_sessions + 1
            }

            # 检查是否是新的学习日
            today = date.today()
            last_session = self.session_repo.get_last_session(user_id)
            
            if last_session:
                last_session_date = last_session.start_time.date()
                if last_session_date != today:
                    update_data["total_learning_days"] = user.total_learning_days + 1
            else:
                # 第一次学习
                update_data["total_learning_days"] = 1

            # 更新用户数据
            self.user_repo.update(user_id, **update_data)
            
            logger.info(f"用户学习进度更新: {user_id}, 总会话: {update_data['total_sessions']}")
            
        except Exception as e:
            logger.error(f"更新用户学习进度失败: {e}")

    def get_today_lesson_for_user(self, user_id: int) -> Optional[Lesson]:
        """
        获取用户今日应该学习的课程
        基于用户当前进度和学习记录决定
        """
        try:
            user =  self.get_user_by_id(user_id)
            if not user:
                return None

            # 检查用户是否有需要复习的内容,复习接口先不使用，要根据
            # review_lessons =  self.review_service.get_review_lesson_for_user(user_id)
            # if review_lessons:
            #     logger.info(f"用户 {user_id} 有复习课程，返回复习内容")
            #     return  self._create_review_lesson(review_lessons)

            # 获取用户当前应该学习的正常课程
            current_lesson_day = user.current_lesson_day
            lesson = self.lesson_repo.get_lesson_by_day(current_lesson_day)
            
            if not lesson:
                logger.warning(f"用户 {user_id} 的课程 {current_lesson_day} 不存在")
                # 如果课程不存在，返回第一天的课程
                lesson = self.lesson_repo.get_lesson_by_day(1)

            logger.info(f"用户 {user_id} 今日课程: 第 {current_lesson_day} 天")
            return lesson

        except Exception as e:
            logger.error(f"获取用户今日课程失败: {e}")
            # 出错时返回第一天的课程作为fallback
            return self.lesson_repo.get_lesson_by_day(1)

    def _get_review_lessons(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户需要复习的句子列表
        返回需要复习的句子，最多2句
        """
        try:
            # 获取用户未掌握的复习项
            review_items = self.review_repo.get_pending_review_items(user_id, limit=2)
            
            if not review_items:
                return []

            review_lessons = []
            for item in review_items:
                review_lessons.append({
                    "sentence": item.sentence_content,
                    "review_item_id": item.id,
                    "is_review": True
                })

            logger.info(f"用户 {user_id} 有 {len(review_lessons)} 个复习句子")
            return review_lessons

        except Exception as e:
            logger.error(f"获取复习课程失败: {e}")
            return []

    def _create_review_lesson(self, review_sentences: List[Dict[str, Any]]) -> Lesson:
        """
        创建复习课程
        基于需要复习的句子构建一个临时的课程对象
        """
        # 这里我们创建一个动态的课程对象
        # 在实际实现中，你可能需要修改数据模型来支持动态课程
        from app.models.lesson import Lesson
        
        # 创建临时课程对象
        review_lesson = Lesson(
            id=-1,  # 使用特殊ID表示复习课程
            day_number=0,  # 复习课程的天数为0
            sentence1=review_sentences[0]["sentence"],
            sentence2=review_sentences[1]["sentence"] if len(review_sentences) > 1 else review_sentences[0]["sentence"],
            is_review=True,
            review_sentences=review_sentences  # 存储复习句子的详细信息
        )
        
        return review_lesson

    def advance_user_lesson(self, user_id: int) -> bool:
        """
        推进用户到下一课程
        在当前课程学习完成后调用
        """
        try:
            user =  self.get_user_by_id(user_id)
            if not user:
                return False

            # 检查是否有复习内容
            review_items = self.review_repo.get_pending_review_items(user_id)
            if review_items:
                logger.info(f"用户 {user_id} 还有复习内容，不推进课程")
                return False

            # 获取下一课程
            next_lesson_day = user.current_lesson_day + 1
            next_lesson = self.lesson_repo.get_lesson_by_day(next_lesson_day)
            
            if next_lesson:
                # 更新用户当前课程
                self.user_repo.update(user_id, current_lesson_day=next_lesson_day)
                logger.info(f"用户 {user_id} 课程推进到第 {next_lesson_day} 天")
                return True
            else:
                # 已经是最后一课，保持当前状态
                logger.info(f"用户 {user_id} 已完成所有课程")
                return False

        except Exception as e:
            logger.error(f"推进用户课程失败: {e}")
            return False

    async def record_learning_issues(self, user_id: int, session_id: int, 
                                   learning_issues: List[Dict[str, Any]]):
        """
        记录学习问题（未跟读、发音不准）
        learning_issues: [
            {
                "sentence_content": "Hi!",
                "sentence_order": 1,
                "record_type": "no_repeat"  # or "incorrect_pronunciation"
            }
        ]
        """
        try:
            for issue in learning_issues:
                # 保存学习记录
                record_data = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "sentence_content": issue["sentence_content"],
                    "sentence_order": issue["sentence_order"],
                    "record_type": issue["record_type"],
                    "record_date": date.today()
                }
                
                self.record_repo.create(**record_data)
                
                # 添加到复习清单（如果不存在）
                await self._add_to_review_list(user_id, issue["sentence_content"])
                
            logger.info(f"用户 {user_id} 会话 {session_id} 记录学习问题: {len(learning_issues)} 个")
            
        except Exception as e:
            logger.error(f"记录学习问题失败: {e}")

    def _add_to_review_list(self, user_id: int, sentence_content: str):
        """添加句子到复习清单"""
        # try:
        #     # 检查是否已经在复习清单中
        #     existing_item = self.review_repo.get_review_item(user_id, sentence_content)
            
        #     if not existing_item:
        #         # 创建新的复习项
        #         review_data = {
        #             "user_id": user_id,
        #             "sentence_content": sentence_content,
        #             "added_date": date.today(),
        #             "mastered": False
        #         }
        #         self.review_repo.create(**review_data)
        #         logger.info(f"句子添加到复习清单: {sentence_content}")
        #     else:
        #         logger.info(f"句子已在复习清单中: {sentence_content}")
                
        # except Exception as e:
        #     logger.error(f"添加到复习清单失败: {e}")

        return  self.review_service.add_to_review_list(user_id, sentence_content, issue_type)

    def mark_review_item_mastered(self, user_id: int, sentence_content: str) -> bool:
        """标记复习项为已掌握"""
        try:
            review_item = self.review_repo.get_review_item(user_id, sentence_content)
            if review_item:
                self.review_repo.update(review_item.id, mastered=True, mastered_date=datetime.now())
                logger.info(f"复习项标记为已掌握: {sentence_content}")
                return True
            return False
        except Exception as e:
            logger.error(f"标记复习项为已掌握失败: {e}")
            return False

    async def get_user_learning_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户学习统计信息"""
        try:
            user =  self.get_user_by_id(user_id)
            if not user:
                return {}

            # 获取复习项数量

            pending_review_count = self.review_repo.get_pending_review_count(user_id)
            logger.info(f"用户 {user_id} 待复习项数量: {pending_review_count}")
            
            # 获取学习记录统计
            recent_records = self.record_repo.get_recent_records(user_id, days=7)
            logger.info(f"用户 {user_id} 最近7天学习记录数量: {len(recent_records)}")
            
            stats = {
                "user_id": user_id,
                "current_lesson_day": user.current_lesson_day,
                "total_learning_days": user.total_learning_days,
                "total_sessions": user.total_sessions,
                "pending_review_count": pending_review_count,
                "recent_learning_issues": len(recent_records),
                "learning_streak":  self._calculate_learning_streak(user_id),
                "last_active_date":  self._get_last_active_date(user_id)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取用户学习统计失败: {e}")
            return {}

    def _calculate_learning_streak(self, user_id: int) -> int:
        """计算用户连续学习天数"""
        try:
            # 获取最近的学习会话日期
            recent_sessions = self.session_repo.get_recent_sessions(user_id, days=30)
            
            if not recent_sessions:
                logger.info(f"用户 {user_id} 最近30天没有学习会话")
                return 0
                
            # 按日期排序并计算连续天数
            dates = sorted([s.start_time.date() for s in recent_sessions], reverse=True)
            
            streak = 0
            current_date = date.today()
            
            for session_date in dates:
                if session_date == current_date:
                    streak += 1
                    current_date = current_date - timedelta(days=1)
                else:
                    break
            logger.info(f"用户 {user_id} 最近30天学习连续天数: {streak}")
                    
            return streak
            
        except Exception as e:
            logger.error(f"计算学习连续天数失败: {e}")
            return 0

    def _get_last_active_date(self, user_id: int) -> Optional[date]:
        """获取用户最后活跃日期"""
        try:
            last_session = self.session_repo.get_last_session(user_id)
            if last_session:
                logger.info(f"用户 {user_id} 最近活跃日期: {last_session.start_time.date()}")
            else:
                logger.info(f"用户 {user_id} 没有最近学习会话")
                
            return last_session.start_time.date() if last_session else None
        except Exception as e:
            logger.error(f"获取最后活跃日期失败: {e}")
            return None

    async def get_user_review_progress(self, user_id: int) -> Dict[str, Any]:
        """获取用户复习进度"""
        try:
            pending_items = self.review_repo.get_pending_review_items(user_id)
            mastered_items = self.review_repo.get_mastered_review_items(user_id)
            
            return {
                "pending_count": len(pending_items),
                "mastered_count": len(mastered_items),
                "pending_items": [
                    {
                        "sentence_content": item.sentence_content,
                        "added_date": item.added_date.isoformat()
                    }
                    for item in pending_items
                ],
                "mastered_items": [
                    {
                        "sentence_content": item.sentence_content,
                        "mastered_date": item.mastered_date.isoformat() if item.mastered_date else None
                    }
                    for item in mastered_items
                ]
            }
            
        except Exception as e:
            logger.error(f"获取用户复习进度失败: {e}")
            return {"pending_count": 0, "mastered_count": 0, "pending_items": [], "mastered_items": []}

    def cleanup_user_data(self, user_id: int) -> bool:
        """清理用户数据（用于账户删除等场景）"""
        try:
            # 在实际应用中，你可能需要根据数据保留策略来决定是软删除还是硬删除
            # 这里实现软删除
            user =  self.get_user_by_id(user_id)
            if user:
                self.user_repo.update(user_id, is_active=False)
                logger.info(f"用户数据已标记为删除: {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"清理用户数据失败: {e}")
            return False