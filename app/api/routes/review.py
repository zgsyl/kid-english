import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.utils.database import get_db
from app.services.review_service import ReviewService
from app.services.user_service import UserService
from app.api.schemas.review_schemas import (
    ReviewProgressResponse, ReviewRecommendationResponse,
    ReviewItemResponse, BatchUpdateRequest, BatchUpdateResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{user_id}/progress", response_model=ReviewProgressResponse)
async def get_review_progress(user_id: int, db: Session = Depends(get_db)):
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
        
        review_service = ReviewService(db)
        progress = await review_service.get_user_review_progress(user_id)
        return progress
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取复习进度失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取复习进度失败"
        )

@router.get("/{user_id}/recommendations", response_model=ReviewRecommendationResponse)
async def get_review_recommendations(user_id: int, db: Session = Depends(get_db)):
    """
    获取复习推荐
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        review_service = ReviewService(db)
        recommendations = await review_service.get_review_recommendations(user_id)
        return recommendations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取复习推荐失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取复习推荐失败"
        )

@router.post("/{user_id}/mark-mastered")
async def mark_review_item_mastered(
    user_id: int, 
    sentence_content: str = Query(..., description="句子内容"),
    db: Session = Depends(get_db)
):
    """
    标记复习项为已掌握
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        review_service = ReviewService(db)
        success = await review_service.mark_review_item_mastered(user_id, sentence_content)
        
        if success:
            return {"message": "复习项已标记为已掌握"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="复习项不存在"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记复习项失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="标记复习项失败"
        )

@router.post("/{user_id}/batch-update", response_model=BatchUpdateResponse)
async def batch_update_review_items(
    user_id: int,
    update_request: BatchUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    批量更新复习项
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        review_service = ReviewService(db)
        result = await review_service.batch_update_review_items(user_id, update_request.updates)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量更新复习项失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量更新复习项失败"
        )