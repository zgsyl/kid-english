from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.review_list import ReviewList
from app.repositories.base import BaseRepository

class ReviewRepository(BaseRepository[ReviewList]):
    def __init__(self, db: Session):
        super().__init__(db, ReviewList)
    
    def get_review_item(self, user_id: int, sentence_content: str) -> Optional[ReviewList]:
        """根据用户ID和句子内容获取复习项"""
        return self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.sentence_content == sentence_content
        ).first()
    
    def get_pending_review_items(self, user_id: int, limit: int = None) -> List[ReviewList]:
        """获取用户未掌握的复习项"""
        query = self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.mastered == False
        ).order_by(ReviewList.added_date.asc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def get_mastered_review_items(self, user_id: int, limit: int = None) -> List[ReviewList]:
        """获取用户已掌握的复习项"""
        query = self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.mastered == True
        ).order_by(desc(ReviewList.mastered_date))
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def get_recent_review_items(self, user_id: int, days: int = 7) -> List[ReviewList]:
        """获取用户最近N天添加的复习项"""
        since_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.added_date >= since_date
        ).order_by(desc(ReviewList.added_date)).all()
    
    def get_pending_review_count(self, user_id: int) -> int:
        """获取用户未掌握复习项的数量"""
        return self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.mastered == False
        ).count()
    
    def get_review_items_by_type(self, user_id: int, issue_type: str) -> List[ReviewList]:
        """根据问题类型获取复习项"""
        return self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.issue_type == issue_type,
            ReviewList.mastered == False
        ).all()
    
    def mark_as_mastered(self, review_item_id: int) -> Optional[ReviewList]:
        """标记复习项为已掌握"""
        review_item = self.get_by_id(review_item_id)
        if review_item:
            review_item.mastered = True
            #review_item.mastered_date = datetime.utcnow()
            review_item.mastered_date = datetime.now(datetime.timezone.utc)
            self.db.commit()
            self.db.refresh(review_item)
        return review_item
    
    def update_practice_info(self, review_item_id: int) -> Optional[ReviewList]:
        """更新练习信息（练习次数和最后练习时间）"""
        review_item = self.get_by_id(review_item_id)
        if review_item:
            review_item.practice_count += 1
            #review_item.last_practiced = datetime.utcnow()
            review_item.last_practiced = datetime.now(datetime.timezone.utc)
            
            self.db.commit()
            self.db.refresh(review_item)
        return review_item
    
    def get_need_review_items(self, user_id: int, max_items: int = 5) -> List[ReviewList]:
        """获取需要复习的项（基于练习次数和添加时间）"""
        return self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.mastered == False
        ).order_by(
            ReviewList.practice_count.asc(),  # 练习次数少的优先
            ReviewList.added_date.asc()       # 添加时间早的优先
        ).limit(max_items).all()
    
    def delete_old_mastered_items(self, user_id: int, days: int = 30) -> int:
        """删除旧的已掌握复习项"""
        #cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_date = datetime.now(datetime.timezone.utc) - timedelta(days=days)
        result = self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.mastered == True,
            ReviewList.mastered_date < cutoff_date
        ).delete()
        self.db.commit()
        return result
    
    def get_review_statistics(self, user_id: int) -> dict:
        """获取复习统计信息"""
        total_count = self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id
        ).count()
        
        mastered_count = self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id,
            ReviewList.mastered == True
        ).count()
        
        pending_count = total_count - mastered_count
        
        # 按问题类型统计
        type_stats = {}
        items = self.db.query(ReviewList).filter(
            ReviewList.user_id == user_id
        ).all()
        
        for item in items:
            issue_type = item.issue_type or "unknown"
            if issue_type not in type_stats:
                type_stats[issue_type] = {"total": 0, "mastered": 0}
            
            type_stats[issue_type]["total"] += 1
            if item.mastered:
                type_stats[issue_type]["mastered"] += 1
        
        return {
            "total_count": total_count,
            "mastered_count": mastered_count,
            "pending_count": pending_count,
            "mastery_rate": mastered_count / total_count if total_count > 0 else 0,
            "type_statistics": type_stats
        }