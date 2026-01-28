from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
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


def get_db_session() -> Session:
    """
    直接获取数据库会话
    在服务层中使用
    """
    return SessionLocal()





def check_db_connection() -> bool:
    """检查数据库连接是否正常"""
    try:
        db = SessionLocal()
        # 执行简单的查询测试连接
        result = db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return False

def init_db():
    """初始化数据库表"""
    try:
        from app.models.base import Base
        from app.models.user import User
        from app.models.lesson import Lesson
        from app.models.session import Session
        from app.models.conversation_context import ConversationContext
        from app.models.learning_record import LearningRecord
        from app.models.review_list import ReviewList  # 新增
        from app.models.sentence import Sentence  # 新增
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化完成")
        
        # 初始化基础课程数据
        #_init_base_lessons()
        init_sentence()
        init_base_lessons_from_sentences()
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

def _init_base_lessons():
    """初始化基础课程数据"""
    from app.repositories.lesson_repository import LessonRepository
    from app.utils.database import get_db

    logger.info("开始初始化基础课程数据1")
    # 基础课程数据
    base_lessons = [
        {"day_number": 1, "sentence1": "Hi!", "sentence2": "Hello!", "description": "hi是你好的意思，hello是你好的意思"},
        {"day_number": 2, "sentence1": "Good morning!", "sentence2": "Goodbye!", "description": "早晚问候语"},
        {"day_number": 3, "sentence1": "Bye!", "sentence2": "Thank you!", "description": "告别和感谢"},
        {"day_number": 4, "sentence1": "You're welcome!", "sentence2": "Excuse me!", "description": "礼貌用语"},
        {"day_number": 5, "sentence1": "I'm sorry!", "sentence2": "That's OK!", "description": "道歉和回应"},
    ]
    
    #db = next(get_db())
    db = SessionLocal()

    try:
        lesson_repo = LessonRepository(db)
        
        for lesson_data in base_lessons:
            existing_lesson = lesson_repo.get_lesson_by_day(lesson_data["day_number"])
            if not existing_lesson:
                lesson_repo.create(**lesson_data)
                logger.info(f"初始化课程 Day {lesson_data['day_number']}")
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"初始化课程数据失败: {e}")
        raise
    finally:
        db.close()



def init_sentence():
    """
    初始化句子表数据，插入一些基础的英文短句
    """
    from app.repositories.sentence_repository import SentenceRepository
    from app.models.sentence import Sentence
    
    logger.info("开始初始化句子表数据")
    
    # 基础句子数据 - 简单的英文短句及其中文翻译
    base_sentences = [
        {"sentence_english": "what is your name!", "sentence_chinese": "你叫什么？", "description": "简单的问候语"},
        {"sentence_english": "can i help you?", "sentence_chinese": "你可以帮助我吗？", "description": "询问是否可以帮助"},
        {"sentence_english": "Good morning!", "sentence_chinese": "早上好！", "description": "早晨问候"},
        {"sentence_english": "Good afternoon!", "sentence_chinese": "下午好！", "description": "下午问候"},
        {"sentence_english": "Good evening!", "sentence_chinese": "晚上好！", "description": "晚上问候"},
        {"sentence_english": "Goodbye!", "sentence_chinese": "再见！", "description": "告别用语"},
        {"sentence_english": "Bye!", "sentence_chinese": "拜！", "description": "简单告别"},
        {"sentence_english": "Thank you!", "sentence_chinese": "谢谢！", "description": "感谢用语"},
        {"sentence_english": "You're welcome!", "sentence_chinese": "不客气！", "description": "回应感谢"},
        {"sentence_english": "Excuse me!", "sentence_chinese": "打扰一下！", "description": "礼貌用语"},
        {"sentence_english": "I'm sorry!", "sentence_chinese": "对不起！", "description": "道歉用语"},
        {"sentence_english": "That's OK!", "sentence_chinese": "没关系！", "description": "回应道歉"},
        {"sentence_english": "Yes.", "sentence_chinese": "是的。", "description": "肯定回答"},
        {"sentence_english": "No.", "sentence_chinese": "不是。", "description": "否定回答"},
        {"sentence_english": "Please.", "sentence_chinese": "请。", "description": "礼貌用语"},
        {"sentence_english": "I see.", "sentence_chinese": "我明白了。", "description": "表示理解"},
        {"sentence_english": "Me too.", "sentence_chinese": "我也是。", "description": "表达同样观点"},
        {"sentence_english": "Great!", "sentence_chinese": "太棒了！", "description": "表示赞赏"},
        {"sentence_english": "Nice!", "sentence_chinese": "真好！", "description": "表示满意"},
        {"sentence_english": "Good!", "sentence_chinese": "好！", "description": "表示认可"}
    ]
    
    db = SessionLocal()
    
    try:
        sentence_repo = SentenceRepository(db)
        added_count = 0
        
        for sentence_data in base_sentences:
            # 检查句子是否已存在（通过英文句子内容判断）
            existing_sentences = sentence_repo.search_sentences(sentence_data["sentence_english"])
            sentence_exists = any(s.sentence_english == sentence_data["sentence_english"] for s in existing_sentences)
            
            if not sentence_exists:
                sentence_repo.create_sentence(
                    sentence_english=sentence_data["sentence_english"],
                    sentence_chinese=sentence_data["sentence_chinese"],
                    description=sentence_data["description"]
                )
                added_count += 1
                logger.debug(f"添加句子: {sentence_data['sentence_english']} - {sentence_data['sentence_chinese']}")
        
        db.commit()
        logger.info(f"句子表数据初始化完成，新增{added_count}个句子")
        
    except Exception as e:
        db.rollback()
        logger.error(f"初始化句子表数据失败: {e}")
        raise
    finally:
        db.close()
    """从句子表初始化基础课程数据"""
    pass
  
def init_base_lessons_from_sentences():
    """
    从句子表初始化基础课程数据
    将sentence表中的句子按每2个一组创建课程
    """
    from app.repositories.sentence_repository import SentenceRepository
    from app.repositories.lesson_repository import LessonRepository
    
    logger.info("开始从句子表初始化基础课程数据")
    
    db = SessionLocal()
    
    try:
        sentence_repo = SentenceRepository(db)
        lesson_repo = LessonRepository(db)
        
        # 获取所有句子
        all_sentences = sentence_repo.get_all_sentences()
        
        if not all_sentences:
            logger.warning("句子表为空，无法初始化课程数据")
            return
        
        # 按照每2个句子一组创建课程
        lesson_count = 0
        
        # 确保句子数量是偶数，如果不是，只使用偶数个
        sentences_to_use = all_sentences[:len(all_sentences) // 2 * 2]
        
        logger.info(f"将使用{len(sentences_to_use)}个句子创建{len(sentences_to_use) // 2}个课程")
        
        # 遍历句子，每两个组成一个课程
        for i in range(0, len(sentences_to_use), 2):
            if i + 1 < len(sentences_to_use):
                sentence1 = sentences_to_use[i].sentence_english
                sentence2 = sentences_to_use[i + 1].sentence_english
                
                # 生成课程描述（结合两个句子的中文和描述）
                description = f""
                if sentences_to_use[i].description:
                    description += f"句子1: {sentences_to_use[i].sentence_english} - {sentences_to_use[i].sentence_chinese} ({sentences_to_use[i].description})\n"
                else:
                    description += f"句子1: {sentences_to_use[i].sentence_english} - {sentences_to_use[i].sentence_chinese}\n"
                
                if sentences_to_use[i + 1].description:
                    description += f"句子2: {sentences_to_use[i + 1].sentence_english} - {sentences_to_use[i + 1].sentence_chinese} ({sentences_to_use[i + 1].description})"
                else:
                    description += f"句子2: {sentences_to_use[i + 1].sentence_english} - {sentences_to_use[i + 1].sentence_chinese}"
                
                # 课程编号从1开始
                day_number = (i // 2) + 1
                
                # 检查课程是否已存在
                existing_lesson = lesson_repo.get_lesson_by_day(day_number)
                if not existing_lesson:
                    lesson_data = {
                    "day_number": day_number,
                    "sentence1": sentence1,
                    "sentence2": sentence2,
                    "description": description,
                    "sentence1_description": sentences_to_use[i].description,
                    "sentence2_description": sentences_to_use[i + 1].description,
                    "is_active": True
                }
                    
                    lesson_repo.create(**lesson_data)
                    lesson_count += 1
                    logger.info(f"创建课程 Day {day_number}: {sentence1}, {sentence2}")
                else:
                    logger.debug(f"课程 Day {day_number} 已存在，跳过")
        
        db.commit()
        logger.info(f"从句子表初始化课程完成，新增{lesson_count}个课程")
        
    except Exception as e:
        db.rollback()
        logger.error(f"从句子表初始化课程数据失败: {e}")
        raise
    finally:
        db.close()
    

    





def get_db_stats() -> dict:
    """
    获取数据库统计信息（同步版本）
    """
    try:
        db = SessionLocal()
        
        # 获取各表记录数
        tables = ["users", "lessons", "sessions", "conversation_context", "learning_records", "review_list"]
        stats = {}
        
        for table in tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                stats[table] = count
            except Exception as e:
                logger.warning(f"获取表 {table} 统计失败: {e}")
                stats[table] = 0
        
        db.close()
        logger.debug(f"数据库统计: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        return {}


def execute_raw_sql(sql: str, params: dict = None):
    """
    执行原始SQL语句（同步版本）
    
    Args:
        sql: SQL语句
        params: 参数
        
    Returns:
        执行结果
    """
    try:
        db = SessionLocal()
        result = db.execute(text(sql), params or {})
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        logger.error(f"执行SQL失败: {e}")
        raise
    finally:
        db.close()



def get_table_info(table_name: str) -> dict:
    """
    获取表结构信息（同步版本）
    """
    try:
        db = SessionLocal()
        
        # 获取表信息
        result = db.execute(text(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """))
        
        columns = []
        for row in result:
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == 'YES',
                "default": row[3]
            })
        
        db.close()
        return {
            "table_name": table_name,
            "columns": columns
        }
        
    except Exception as e:
        logger.error(f"获取表信息失败: {e}")
        return {"table_name": table_name, "columns": []}
