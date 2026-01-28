import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.models.learning_record import LearningRecord
from app.repositories.learning_record_repository import LearningRecordRepository
from app.config.settings import settings

logger = logging.getLogger(__name__)


class RecordService:
    """学习记录服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.record_repo = LearningRecordRepository(db)
        logger.info("学习记录服务初始化完成")
    
    def record_learning_issues(self, user_id: int, session_id: int, 
                                   learning_issues: List[Dict[str, Any]]) -> bool:
        """
        记录学习问题
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            learning_issues: 学习问题列表
            
        Returns:
            bool: 是否成功记录
        """
        try:
            recorded_count = 0
            
            for issue in learning_issues:
                record_data = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "sentence_content": issue["sentence_content"],
                    "sentence_order": issue["sentence_order"],
                    "record_type": issue["record_type"],  # "no_repeat" or "incorrect_pronunciation"
                    "record_date": date.today()
                }
                
                # 创建记录
                self.record_repo.create(**record_data)
                recorded_count += 1
            
            logger.info(f"记录学习问题成功: 用户{user_id}, 会话{session_id}, 记录数{recorded_count}")
            return True
            
        except Exception as e:
            logger.error(f"记录学习问题失败: {e}")
            return False
    
    def get_user_learning_records(self, user_id: int, days: int = 30) -> List[LearningRecord]:
        """
        获取用户的学习记录
        
        Args:
            user_id: 用户ID
            days: 查询天数
            
        Returns:
            List[LearningRecord]: 学习记录列表
        """
        try:
            #since_date = datetime.utcnow() - timedelta(days=days)
            since_date = datetime.now(datetime.timezone.utc)() - timedelta(days=days)      
            records = self.record_repo.get_records_since_date(user_id, since_date)
            return records
        except Exception as e:
            logger.error(f"获取用户学习记录失败: {e}")
            return []
    
    def get_problematic_sentences(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取用户有问题的句子（需要复习的）
        
        Args:
            user_id: 用户ID
            days: 查询天数
            
        Returns:
            List[Dict]: 问题句子统计
        """
        try:
            #since_date = datetime.utcnow() - timedelta(days=days)
            since_date = datetime.now(datetime.timezone.utc)() - timedelta(days=days)      
            records = self.record_repo.get_records_since_date(user_id, since_date)
            
            # 统计每个句子的问题次数
            sentence_stats = {}
            
            for record in records:
                sentence_key = record.sentence_content
                
                if sentence_key not in sentence_stats:
                    sentence_stats[sentence_key] = {
                        "sentence_content": record.sentence_content,
                        "total_issues": 0,
                        "no_repeat_count": 0,
                        "incorrect_pronunciation_count": 0,
                        "last_issue_date": record.record_date,
                        "sentence_order": record.sentence_order
                    }
                
                stats = sentence_stats[sentence_key]
                stats["total_issues"] += 1
                
                if record.record_type == "no_repeat":
                    stats["no_repeat_count"] += 1
                elif record.record_type == "incorrect_pronunciation":
                    stats["incorrect_pronunciation_count"] += 1
                
                if record.record_date > stats["last_issue_date"]:
                    stats["last_issue_date"] = record.record_date
            
            # 按问题次数排序
            sorted_sentences = sorted(
                sentence_stats.values(),
                key=lambda x: x["total_issues"],
                reverse=True
            )
            
            return sorted_sentences
            
        except Exception as e:
            logger.error(f"获取问题句子失败: {e}")
            return []
    
    def get_learning_statistics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        获取学习统计信息
        
        Args:
            user_id: 用户ID
            days: 查询天数
            
        Returns:
            Dict: 统计信息
        """
        try:
            #since_date = datetime.utcnow() - timedelta(days=days)
            since_date = datetime.now(datetime.timezone.utc)() - timedelta(days=days)      
            records = self.record_repo.get_records_since_date(user_id, since_date)
            
            total_issues = len(records)
            no_repeat_count = sum(1 for r in records if r.record_type == "no_repeat")
            pronunciation_count = sum(1 for r in records if r.record_type == "incorrect_pronunciation")
            
            # 按日期统计
            date_stats = {}
            for record in records:
                date_str = record.record_date.isoformat()
                if date_str not in date_stats:
                    date_stats[date_str] = {
                        "date": date_str,
                        "total_issues": 0,
                        "no_repeat_count": 0,
                        "incorrect_pronunciation_count": 0
                    }
                
                stats = date_stats[date_str]
                stats["total_issues"] += 1
                
                if record.record_type == "no_repeat":
                    stats["no_repeat_count"] += 1
                elif record.record_type == "incorrect_pronunciation":
                    stats["incorrect_pronunciation_count"] += 1
            
            return {
                "total_issues": total_issues,
                "no_repeat_count": no_repeat_count,
                "incorrect_pronunciation_count": pronunciation_count,
                "daily_statistics": list(date_stats.values()),
                "analysis_period_days": days
            }
            
        except Exception as e:
            logger.error(f"获取学习统计失败: {e}")
            return {
                "total_issues": 0,
                "no_repeat_count": 0,
                "incorrect_pronunciation_count": 0,
                "daily_statistics": [],
                "analysis_period_days": days
            }
    
    def clear_old_records(self, user_id: int, days: int = 90) -> int:
        """
        清理旧的记录
        
        Args:
            user_id: 用户ID
            days: 保留天数
            
        Returns:
            int: 删除的记录数量
        """
        try:
            #cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            deleted_count = self.record_repo.delete_records_before_date(user_id, cutoff_date)
            logger.info(f"清理用户{user_id}的旧记录: 删除{deleted_count}条")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")
            return 0