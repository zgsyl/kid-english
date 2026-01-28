import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.utils.database import get_db
from app.services.session_service import SessionService
from app.services.user_service import UserService
from app.api.schemas.session_schemas import SessionResponse, SessionListResponse
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/user/{user_id}", response_model=SessionListResponse)
async def get_user_sessions(
    user_id: int, 
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    获取用户的会话历史
    """
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        session_service = SessionService(db)
        sessions = session_service.get_user_sessions(user_id, limit)
        
        # 将数据库模型转换为可序列化的SessionResponse对象列表
        session_responses = []
        for session in sessions:
            # 使用SessionResponse模型进行转换，利用model_config中的from_attributes=True
            session_response = SessionResponse.model_validate(session)
            session_responses.append(session_response)
        
        return {
            "user_id": user_id,
            "sessions": session_responses,
            "total": len(session_responses)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户会话失败"
        )

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """
    获取会话详情
    """
    try:
        session_service = SessionService(db)
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话详情失败"
        )

@router.delete("/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    """
    删除会话（清理数据）
    """
    try:
        session_service = SessionService(db)
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        success = session_service.end_session(session_id)
        if success:
            return {"message": "会话数据已删除"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除会话数据失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除会话失败"
        )