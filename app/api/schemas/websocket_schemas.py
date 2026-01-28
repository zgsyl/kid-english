from pydantic import BaseModel
from typing import Optional, Dict, Any

class WebSocketMessageBase(BaseModel):
    type: str
    session_id: int
    timestamp: str

class UserMessage(WebSocketMessageBase):
    type: str = "user_message"
    content: str

class TimeoutMessage(WebSocketMessageBase):
    type: str = "timeout"
    step: str

class TeachingResponse(WebSocketMessageBase):
    type: str = "teaching_response"
    content: str
    step: str
    waiting_for_user: bool
    timeout_seconds: Optional[int] = None
    audio_url: Optional[str] = None

class SessionStartMessage(WebSocketMessageBase):
    type: str = "session_start"
    user_id: int
    message: str

class SessionEndMessage(WebSocketMessageBase):
    type: str = "session_end"
    message: str

class HeartbeatMessage(WebSocketMessageBase):
    type: str = "heartbeat"

class HeartbeatAckMessage(WebSocketMessageBase):
    type: str = "heartbeat_ack"

class ErrorMessage(WebSocketMessageBase):
    type: str = "error"
    message: str