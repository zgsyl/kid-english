import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.utils.database import get_db
from app.services.record_service import RecordService
from app.services.user_service import UserService
from app.api.schemas.record_schemas import (
    LearningRecordResponse, LearningStatsResponse, ProblematicSentencesResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{user_id}", response_model=List[LearningRecordResponse])
async def get_learning_records(
    user_id: int, 
    days: int = Query(30, description="查询天数", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    获取用户学习记录
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        record_service = RecordService(db)
        records = await record_service.get_user_learning_records(user_id, days)
        return records
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取学习记录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取学习记录失败"
        )

@router.get("/{user_id}/statistics", response_model=LearningStatsResponse)
async def get_learning_statistics(
    user_id: int,
    days: int = Query(30, description="统计天数", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    获取用户学习统计
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        record_service = RecordService(db)
        stats = await record_service.get_learning_statistics(user_id, days)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取学习统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取学习统计失败"
        )

@router.get("/{user_id}/problematic-sentences", response_model=ProblematicSentencesResponse)
async def get_problematic_sentences(
    user_id: int,
    days: int = Query(7, description="查询天数", ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    获取用户有问题的句子
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        record_service = RecordService(db)
        sentences = await record_service.get_problematic_sentences(user_id, days)
        return {
            "user_id": user_id,
            "analysis_days": days,
            "problematic_sentences": sentences
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取问题句子失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取问题句子失败"
        )