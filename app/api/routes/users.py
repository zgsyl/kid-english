import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.services.user_service import UserService
from app.api.schemas.user_schemas import (
    UserCreate, UserResponse, UserUpdate, 
    UserStatsResponse, ReviewProgressResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

#@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册接口
    """
    try:
        user_service = UserService(db)
        user = await user_service.register_or_login_user(
            wechat_openid=user_data.wechat_openid,
            user_info=user_data.dict()
        )
        return user
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户注册失败: {str(e)}"
        )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    获取用户信息
    """
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )

@router.get("/openid/{wechat_openid}", response_model=UserResponse)
async def get_user_by_openid(wechat_openid: str, db: Session = Depends(get_db)):
    """
    根据微信openid获取用户信息
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_openid(wechat_openid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    """
    更新用户信息
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        updated_user = await user_service._update_user_info(
            user_id, user_data.dict(exclude_unset=True)
        )
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息失败"
        )

@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    """
    获取用户学习统计
    """
    try:
        user_service = UserService(db)
        user =  user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        stats = await user_service.get_user_learning_stats(user_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户统计失败"
        )

@router.get("/{user_id}/review-progress", response_model=ReviewProgressResponse)
async def get_user_review_progress(user_id: int, db: Session = Depends(get_db)):
    """
    获取用户复习进度
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        progress = await user_service.get_user_review_progress(user_id)
        return progress
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取复习进度失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取复习进度失败"
        )

@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    删除用户数据（软删除）
    """
    try:
        user_service = UserService(db)
        user =  user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        success = user_service.cleanup_user_data(user_id)
        if success:
            return {"message": "用户数据已删除"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除用户数据失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户数据失败"
        )