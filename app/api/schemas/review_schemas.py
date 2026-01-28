from pydantic import BaseModel,ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime

class ReviewItemBase(BaseModel):
    sentence_content: str
    issue_type: Optional[str] = None

class ReviewItemResponse(ReviewItemBase):
    id: int
    user_id: int
    added_date: str
    mastered: bool
    mastered_date: Optional[str] = None
    last_practiced: Optional[str] = None
    practice_count: int

    # class Config:
    #     from_attributes = True

    model_config = ConfigDict(
        from_attributes=True
    )

class ReviewProgressResponse(BaseModel):
    pending_count: int
    mastered_count: int
    pending_items: List[Dict[str, Any]]
    mastered_items: List[Dict[str, Any]]
    statistics: Dict[str, Any]

class ReviewRecommendationResponse(BaseModel):
    total_need_review: int
    by_issue_type: Dict[str, List[str]]
    priority_items: List[Dict[str, Any]]
    recommended_daily_goal: int

class ReviewUpdate(BaseModel):
    sentence_content: str
    mastered: bool

class BatchUpdateRequest(BaseModel):
    updates: List[ReviewUpdate]

class BatchUpdateResponse(BaseModel):
    success_count: int
    fail_count: int
    total_processed: int