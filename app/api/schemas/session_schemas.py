from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic import ConfigDict

class SessionBase(BaseModel):
    user_id: int
    lesson_id: Optional[int] = None

class SessionResponse(SessionBase):
    id: int
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    context_count: int
    current_step: Optional[str] = None
    created_at: datetime

    # class Config:
    #     from_attributes = True
    
    model_config = ConfigDict(
        from_attributes=True
    )

class SessionListResponse(BaseModel):
    user_id: int
    sessions: list
    total: int