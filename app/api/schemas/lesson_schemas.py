from pydantic import BaseModel,ConfigDict
from typing import Optional, List
from datetime import datetime

class LessonBase(BaseModel):
    day_number: int
    sentence1: str
    sentence2: str
    description: Optional[str] = None

class LessonResponse(LessonBase):
    id: int
    is_active: bool
    created_at: datetime

    # class Config:
    #     from_attributes = True

    model_config = ConfigDict(
        from_attributes=True
    )

class LessonListResponse(BaseModel):
    lessons: List[LessonResponse]
    total: int
    skip: int
    limit: int