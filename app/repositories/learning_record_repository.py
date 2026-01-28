from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.learning_record import LearningRecord
from app.repositories.base import BaseRepository
import pytz
from datetime import datetime, timezone, timedelta


class LearningRecordRepository(BaseRepository[LearningRecord]):
    def __init__(self, db: Session):
        super().__init__(db, LearningRecord)
    
    def get_records_since_date(self, user_id: int, since_date: datetime) -> List[LearningRecord]:
        """获取指定日期之后的记录"""
        return self.db.query(LearningRecord).filter(
            LearningRecord.user_id == user_id,
            LearningRecord.record_date >= since_date
        ).order_by(LearningRecord.record_date.desc()).all()
    
    def get_recent_records(self, user_id: int, days: int = 7) -> List[LearningRecord]:
        """获取最近N天的记录"""
        #since_date = datetime.utcnow() - timedelta(days=days)
        since_date = datetime.now(timezone.utc) - timedelta(days=days)



        return self.get_records_since_date(user_id, since_date)
    
    def get_records_by_type(self, user_id: int, record_type: str, days: int = 30) -> List[LearningRecord]:
        """根据类型获取记录"""
        #since_date = datetime.utcnow() - timedelta(days=days)
        since_date = datetime.now(datetime.timezone.utc) - timedelta(days=days)
        return self.db.query(LearningRecord).filter(
            LearningRecord.user_id == user_id,
            LearningRecord.record_type == record_type,
            LearningRecord.record_date >= since_date
        ).all()
    
    def delete_records_before_date(self, user_id: int, cutoff_date: datetime) -> int:
        """删除指定日期之前的记录"""
        result = self.db.query(LearningRecord).filter(
            LearningRecord.user_id == user_id,
            LearningRecord.record_date < cutoff_date
        ).delete()
        self.db.commit()
        return result