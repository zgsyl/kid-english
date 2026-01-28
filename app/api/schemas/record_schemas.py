from pydantic import BaseModel,ConfigDict
from typing import List, Dict, Any
from datetime import datetime

class LearningRecordBase(BaseModel):
    user_id: int
    session_id: int
    sentence_content: str
    sentence_order: int
    record_type: str

class LearningRecordResponse(LearningRecordBase):
    id: int
    record_date: datetime
    created_at: datetime

    # class Config:
    #     from_attributes = True

    model_config = ConfigDict(
        from_attributes=True
    )

class DailyStatistics(BaseModel):
    date: str
    total_issues: int
    no_repeat_count: int
    incorrect_pronunciation_count: int

class LearningStatsResponse(BaseModel):
    total_issues: int
    no_repeat_count: int
    incorrect_pronunciation_count: int
    daily_statistics: List[DailyStatistics]
    analysis_period_days: int

class ProblematicSentence(BaseModel):
    sentence_content: str
    total_issues: int
    no_repeat_count: int
    incorrect_pronunciation_count: int
    last_issue_date: datetime
    sentence_order: int

class ProblematicSentencesResponse(BaseModel):
    user_id: int
    analysis_days: int
    problematic_sentences: List[ProblematicSentence]