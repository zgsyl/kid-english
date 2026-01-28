import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.review_list import ReviewList
from app.repositories.review_repository import ReviewRepository
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ReviewService:
    """复习服务，管理用户的复习清单和学习进度"""
    
    def __init__(self, db: Session):
        self.db = db
        self.review_repo = ReviewRepository(db)
        logger.info("复习服务初始化完成")
    
    def add_to_review_list(self, user_id: int, sentence_content: str, 
                               issue_type: str = None, sentence_order: int = None) -> ReviewList:
        """
        添加句子到复习清单
        
        Args:
            user_id: 用户ID
            sentence_content: 句子内容
            issue_type: 问题类型 ("no_repeat", "incorrect_pronunciation", "exam_failed")
            sentence_order: 句子顺序
            
        Returns:
            ReviewList: 创建的复习项
        """
        try:
            # 检查是否已经在复习清单中
            existing_item = self.review_repo.get_review_item(user_id, sentence_content)
            
            if existing_item:
                # 如果已存在但未掌握，更新练习信息
                if not existing_item.mastered:
                    self.review_repo.update_practice_info(existing_item.id)
                    logger.info(f"复习项已存在，更新练习信息: {sentence_content}")
                return existing_item
            
            # 创建新的复习项
            review_data = {
                "user_id": user_id,
                "sentence_content": sentence_content,
                "issue_type": issue_type,
                "added_date": datetime.utcnow()
            }
            
            review_item = self.review_repo.create(**review_data)
            logger.info(f"新复习项添加成功: 用户{user_id}, 句子: {sentence_content}")
            return review_item
            
        except Exception as e:
            logger.error(f"添加到复习清单失败: {e}")
            raise
    
    def get_review_lesson_for_user(self, user_id: int, max_sentences: int = 2) -> List[Dict[str, Any]]:
        """
        为用户生成复习课程
        
        Args:
            user_id: 用户ID
            max_sentences: 最大句子数量
            
        Returns:
            List[Dict]: 复习句子列表
        """
        try:
            # 获取需要复习的句子
            review_items = self.review_repo.get_need_review_items(user_id, max_sentences)
            
            if not review_items:
                logger.info(f"用户 {user_id} 没有需要复习的句子")
                return []
            
            # 构建复习课程数据
            review_lesson = []
            for item in review_items:
                review_lesson.append({
                    "sentence_content": item.sentence_content,
                    "review_item_id": item.id,
                    "issue_type": item.issue_type,
                    "is_review": True
                })
                
                # 更新练习信息
                self.review_repo.update_practice_info(item.id)
            
            logger.info(f"为用户 {user_id} 生成复习课程，包含 {len(review_lesson)} 个句子")
            return review_lesson
            
        except Exception as e:
            logger.error(f"生成复习课程失败: {e}")
            return []
    
    def mark_review_item_mastered(self, user_id: int, sentence_content: str) -> bool:
        """
        标记复习项为已掌握
        
        Args:
            user_id: 用户ID
            sentence_content: 句子内容
            
        Returns:
            bool: 是否成功标记
        """
        try:
            review_item = self.review_repo.get_review_item(user_id, sentence_content)
            if review_item:
                self.review_repo.mark_as_mastered(review_item.id)
                logger.info(f"复习项标记为已掌握: 用户{user_id}, 句子: {sentence_content}")
                return True
            else:
                logger.warning(f"未找到复习项: 用户{user_id}, 句子: {sentence_content}")
                return False
                
        except Exception as e:
            logger.error(f"标记复习项为已掌握失败: {e}")
            return False
    
    def get_user_review_progress(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户复习进度
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 复习进度信息
        """
        try:
            pending_items = self.review_repo.get_pending_review_items(user_id)
            mastered_items = self.review_repo.get_mastered_review_items(user_id)
            stats = self.review_repo.get_review_statistics(user_id)
            
            return {
                "pending_count": len(pending_items),
                "mastered_count": len(mastered_items),
                "pending_items": [
                    {
                        "id": item.id,
                        "sentence_content": item.sentence_content,
                        "issue_type": item.issue_type,
                        "added_date": item.added_date.isoformat() if item.added_date else None,
                        "practice_count": item.practice_count,
                        "last_practiced": item.last_practiced.isoformat() if item.last_practiced else None
                    }
                    for item in pending_items
                ],
                "mastered_items": [
                    {
                        "id": item.id,
                        "sentence_content": item.sentence_content,
                        "issue_type": item.issue_type,
                        "added_date": item.added_date.isoformat() if item.added_date else None,
                        "mastered_date": item.mastered_date.isoformat() if item.mastered_date else None,
                        "practice_count": item.practice_count
                    }
                    for item in mastered_items
                ],
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"获取用户复习进度失败: {e}")
            return {
                "pending_count": 0,
                "mastered_count": 0,
                "pending_items": [],
                "mastered_items": [],
                "statistics": {}
            }
    
    def cleanup_old_review_items(self, user_id: int, days: int = 90) -> int:
        """
        清理旧的复习项
        
        Args:
            user_id: 用户ID
            days: 保留天数
            
        Returns:
            int: 删除的项目数量
        """
        try:
            # 删除旧的已掌握项目
            deleted_count = self.review_repo.delete_old_mastered_items(user_id, days)
            logger.info(f"清理用户 {user_id} 的旧复习项: 删除 {deleted_count} 条")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧复习项失败: {e}")
            return 0
    
    def get_review_recommendations(self, user_id: int) -> Dict[str, Any]:
        """
        获取复习推荐
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 复习推荐信息
        """
        try:
            # 获取需要复习的句子
            need_review = self.review_repo.get_need_review_items(user_id, 10)
            
            # 按问题类型分组
            by_type = {}
            for item in need_review:
                issue_type = item.issue_type or "other"
                if issue_type not in by_type:
                    by_type[issue_type] = []
                by_type[issue_type].append(item.sentence_content)
            
            # 计算复习优先级
            priority_items = []
            for item in need_review[:5]:  # 取前5个最高优先级的
                priority = self._calculate_review_priority(item)
                priority_items.append({
                    "sentence": item.sentence_content,
                    "priority": priority,
                    "issue_type": item.issue_type,
                    "practice_count": item.practice_count,
                    "days_since_added": (datetime.utcnow() - item.added_date).days
                })
            
            return {
                "total_need_review": len(need_review),
                "by_issue_type": by_type,
                "priority_items": priority_items,
                "recommended_daily_goal": min(5, len(need_review))  # 建议每日复习目标
            }
            
        except Exception as e:
            logger.error(f"获取复习推荐失败: {e}")
            return {
                "total_need_review": 0,
                "by_issue_type": {},
                "priority_items": [],
                "recommended_daily_goal": 0
            }
    
    def _calculate_review_priority(self, review_item: ReviewList) -> float:
        """
        计算复习优先级
        
        Args:
            review_item: 复习项
            
        Returns:
            float: 优先级分数（越高越优先）
        """
        # 基于以下因素计算优先级：
        # 1. 练习次数越少，优先级越高
        # 2. 添加时间越早，优先级越高
        # 3. 最近练习过的话，优先级降低
        
        practice_factor = 1.0 / (review_item.practice_count + 1)
        
        days_since_added = (datetime.utcnow() - review_item.added_date).days
        time_factor = min(1.0, days_since_added / 30.0)  # 最大30天
        
        if review_item.last_practiced:
            days_since_practice = (datetime.utcnow() - review_item.last_practiced).days
            recent_factor = max(0.1, 1.0 - (days_since_practice / 7.0))  # 7天内练习过会降低优先级
        else:
            recent_factor = 1.0
        
        return practice_factor * time_factor * recent_factor
    
    def batch_update_review_items(self, user_id: int, updates: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        批量更新复习项
        
        Args:
            user_id: 用户ID
            updates: 更新列表，每个元素包含 sentence_content 和 mastered
            
        Returns:
            Dict: 更新统计
        """
        try:
            success_count = 0
            fail_count = 0
            
            for update in updates:
                sentence_content = update.get("sentence_content")
                mastered = update.get("mastered", False)
                
                if mastered:
                    success =  self.mark_review_item_mastered(user_id, sentence_content)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    # 对于未掌握的，更新练习信息
                    review_item = self.review_repo.get_review_item(user_id, sentence_content)
                    if review_item:
                        self.review_repo.update_practice_info(review_item.id)
                        success_count += 1
                    else:
                        fail_count += 1
            
            return {
                "success_count": success_count,
                "fail_count": fail_count,
                "total_processed": success_count + fail_count
            }
            
        except Exception as e:
            logger.error(f"批量更新复习项失败: {e}")
            return {"success_count": 0, "fail_count": 0, "total_processed": 0}