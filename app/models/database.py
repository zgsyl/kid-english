from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # 在DEBUG模式下输出SQL语句
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 创建SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"数据库会话错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def init_db():
    """初始化数据库表"""
    try:
        from app.models.base import Base
        from app.models.user import User
        from app.models.lesson import Lesson
        from app.models.session import Session
        from app.models.conversation_context import ConversationContext
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化完成")
        
        # 初始化基础课程数据
        await _init_base_lessons()
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

async def _init_base_lessons():
    """初始化基础课程数据"""
    from app.repositories.lesson_repository import LessonRepository
    from app.utils.database import get_db
    
    # 基础课程数据
    base_lessons = [
        {"day_number": 1, "sentence1": "Hi!", "sentence2": "Hello!", "description": "基础问候语"},
        {"day_number": 2, "sentence1": "Good morning!", "sentence2": "Goodbye!", "description": "早晚问候语"},
        {"day_number": 3, "sentence1": "Bye!", "sentence2": "Thank you!", "description": "告别和感谢"},
        {"day_number": 4, "sentence1": "You're welcome!", "sentence2": "Excuse me!", "description": "礼貌用语"},
        {"day_number": 5, "sentence1": "I'm sorry!", "sentence2": "That's OK!", "description": "道歉和回应"},
    ]
    
    db = next(get_db())
    lesson_repo = LessonRepository(db)
    
    for lesson_data in base_lessons:
        existing_lesson = lesson_repo.get_lesson_by_day(lesson_data["day_number"])
        if not existing_lesson:
            lesson_repo.create(**lesson_data)
            logger.info(f"初始化课程 Day {lesson_data['day_number']}")