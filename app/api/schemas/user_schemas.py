from pydantic import BaseModel,ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    wechat_openid: str
    nickname: Optional[str] = None
    age: Optional[int] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    age: Optional[int] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    id: int
    current_lesson_day: int
    total_learning_days: int
    total_sessions: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # class Config:
    #     from_attributes = True
    
    model_config = ConfigDict(
        from_attributes=True
    )

class UserStatsResponse(BaseModel):
    user_id: int
    current_lesson_day: int
    total_learning_days: int
    total_sessions: int
    pending_review_count: int
    recent_learning_issues: int
    learning_streak: int
    last_active_date: Optional[datetime]

class ReviewItem(BaseModel):
    sentence_content: str
    added_date: str
    mastered_date: Optional[str] = None

class ReviewProgressResponse(BaseModel):
    pending_count: int
    mastered_count: int
    pending_items: List[ReviewItem]
    mastered_items: List[ReviewItem]