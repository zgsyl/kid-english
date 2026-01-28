#!/usr/bin/env python3
"""
幼儿英语口语教学智能体 - FastAPI 主应用入口
Author: Teaching Agent Team
Description: 提供WebSocket接口用于教学交互，REST API用于管理功能
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from app.utils.text2voice import TencentCloudTTSClient
from app.utils.sentence_recognition import TencentCloudAPIV3

from app.config.settings import settings
from app.utils.logger import setup_logging
from app.utils.database import init_db, get_db_session
from app.api.routes.websocket import websocket_manager

# 初始化TTS客户端
tts_client = None
try:
    tts_client = TencentCloudTTSClient(
        region="ap-shanghai"
    )
    logging.info("TTS客户端初始化成功")
except Exception as e:
    logging.warning(f"TTS客户端初始化失败: {e}，语音合成功能将不可用")

# 初始化语音识别客户端
asr_client = None
# try:
#     asr_client = TencentCloudAPIV3()
#     logging.info("语音识别客户端初始化成功")
# except Exception as e:
#     logging.warning(f"语音识别客户端初始化失败: {e}，语音识别功能将不可用")
from app.services.teaching_service import TeachingService
from app.services.session_service import SessionService
from app.services.user_service import UserService
from app.services.lesson_service import LessonService
from app.services.record_service import RecordService
from app.services.review_service import ReviewService



from app.api.routes import review

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)

# 全局服务实例
teaching_service = None
session_service = None
user_service = None
lesson_service = None
record_service = None
review_service = None

def process_audio_recognition(message_data, asr_client):
    """
    处理语音识别，将消息中的PCM音频数据转换为文字
    
    Args:
        message_data: 消息字典，包含audio_content字段
        asr_client: TencentCloudAPIV3实例
    
    Returns:
        str: 识别出的文字，如果识别失败返回None
    """
    if not asr_client :
        logging.warning("语音识别客户端未初始化")
        return None

    if not message_data.get('content'):
        logging.warning("消息数据中缺少content字段")
        return None
    
    try:
        #pcm_base64_data = message_data['audio_content']
        pcm_base64_data = message_data['content']
        logging.info(f"开始识别PCM音频数据，base64长度: {len(pcm_base64_data)}")
        
        # 调用语音识别API
        result = asr_client.recognize_pcm_base64(
            pcm_base64_data=pcm_base64_data,
            #engine_model_type="16k_zh"
            engine_model_type="8k_zh"
        )
        
        if result.get('success') and result.get('text'):
            recognized_text = result['text'].strip()
            logging.info(f"语音识别成功，识别结果: {recognized_text}")
            return recognized_text
        else:
            error_msg = result.get('error_message', '语音识别失败')
            logging.warning(f"语音识别失败: {error_msg}")
            return None
            
    except Exception as e:
        logging.error(f"语音识别过程中出错: {e}")
        return None

def process_tts_conversion(response, tts_client):
    """
    处理文本转语音转换并更新响应对象
    
    Args:
        response: 响应字典，将被更新以包含语音相关信息
        tts_client: TencentCloudTTSClient实例
    """
    if 'content' in response and tts_client:
        try:
            content_text = response['content']
            # 调用TTS服务将文本转为语音
            logging.info(f"开始将文本转换为语音，长度: {len(content_text)}字符")
            
            # 使用增强方法获取音频数据
            tts_result = tts_client.text_to_speech_with_audio_data(
                text=content_text,
                voice_type=101008,  # 女声
                codec="mp3",
                wait_for_complete=True,
                timeout=30,
                download_timeout=20
            )
            
            # 在响应中添加语音相关字段
            if tts_result.get('audio_download_success'):
                # 添加语音合成相关信息到response
                response['has_audio'] = True
                response['audio_data'] = tts_result.get('audio_data')
                response['audio_size'] = tts_result.get('file_size', 0)
                response['audio_content_type'] = tts_result.get('content_type', 'audio/mpeg')
                response['tts_task_id'] = tts_result.get('Response', {}).get('Data', {}).get('TaskId')
                response['tts_result_url'] = tts_result.get('Response', {}).get('Data', {}).get('ResultUrl')
                logging.info(f"语音合成成功，音频大小: {response['audio_size']}字节")
            else:
                # 合成失败但不阻止原响应发送
                response['has_audio'] = False
                response['audio_error'] = tts_result.get('error_message', '语音合成失败')
                logging.warning(f"语音合成失败: {response['audio_error']}")
        except Exception as e:
            # 捕获异常但不阻止原响应发送
            response['has_audio'] = False
            response['audio_error'] = str(e)
            logging.error(f"语音合成过程中出错: {e}")
    else:
        # 如果没有content字段或TTS客户端未初始化，标记没有音频
        response['has_audio'] = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - 启动时初始化服务
    - 关闭时清理资源
    """
    global teaching_service, session_service, user_service, lesson_service, record_service, review_service,asr_client,tts_client
    
    # 启动时初始化
    logger.info("初始化教学智能体应用...")
    
    try:
        # 初始化数据库
        init_db()
        logger.info("数据库初始化完成")

        try:
            asr_client = TencentCloudAPIV3()
            logging.info("语音识别客户端初始化成功")
        except Exception as e:
            logging.warning(f"语音识别客户端初始化失败: {e}，语音识别功能将不可用")
        
        # 创建数据库会话用于服务初始化
        db = get_db_session()
    
        # 初始化服务层
        lesson_service = LessonService(db)
        record_service = RecordService(db)
        review_service = ReviewService(db)


   
        teaching_service = TeachingService(db)
        session_service = SessionService(db) 
        user_service = UserService(db)

    
            
        logger.info("服务层初始化完成")
        
        # 检查大模型连接
        await _check_llm_connection()
        
        logger.info("教学智能体应用启动完成")
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise
    
    yield  # 应用运行期间
    
    # 关闭时清理
    logger.info("正在关闭教学智能体应用...")
    
    # 清理所有活跃的WebSocket连接
    for session_id in list(websocket_manager.active_connections.keys()):
        await websocket_manager.disconnect(session_id)
    
    logger.info("教学智能体应用已安全关闭")

def create_application() -> FastAPI:
    """创建并配置FastAPI应用实例"""
    
    app = FastAPI(
        title="幼儿英语口语教学智能体",
        description="基于大模型的互动式幼儿英语教学系统",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # 配置CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://www.weixin.qq.com",  # 微信小程序
            "http://localhost:3000",      # 开发环境
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 全局异常处理
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "内部服务器错误"}
        )
    
    return app

# 创建应用实例
app = create_application()

# 导入并包含路由
#from app.api.routes import users, lessons, records, websocket
from app.api.routes import users, records, websocket, sessions,lessons

# 注册API路由
app.include_router(users.router, prefix="/api/v1/users", tags=["用户管理"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["教学会话"])
app.include_router(lessons.router, prefix="/api/v1/lessons", tags=["课程管理"])
app.include_router(records.router, prefix="/api/v1/records", tags=["学习记录"])
app.include_router(review.router, prefix="/api/v1/review", tags=["复习管理"])
# WebSocket路由
@app.websocket("/ws/teaching/{user_id}")
async def teaching_websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    教学WebSocket端点
    - 用户连接到教学会话的主要入口
    - 处理实时教学交互
    """
    logger.info(f"用户 {user_id} 尝试连接WebSocket")
    
    try:
        # 验证用户是否存在
        user =  user_service.get_user_by_id(user_id)
        if not user:
            await websocket.close(code=1008, reason="用户不存在")
            return
        
        # 接受WebSocket连接
        await websocket.accept()
        logger.info(f"用户 {user_id} WebSocket连接已建立")
        
        # 创建新的教学会话
        session =  session_service.create_session(user_id)
        session_id = session.id
        
        # 将连接加入管理器
        await websocket_manager.connect(websocket, session_id)
        
        # 发送欢迎消息
        welcome_msg = {
            "type": "session_start",
            "session_id": session_id,
            "message": "教学会话已开始，准备获取今日课程...",
            "timestamp": _get_current_timestamp()
        }
        await websocket_manager.send_message(session_id, welcome_msg)
        
        # 获取今日课程并开始教学
        logger.info(f"用户 {user_id} 开始获取今日课程")
        lesson =  _get_today_lesson(user_id)
        teaching_response =  await teaching_service.start_teaching_session(
            user_id, session_id, lesson.id
        )
        process_tts_conversion(teaching_response, tts_client)
        # 发送初始教学响应
        await websocket_manager.send_message(session_id, teaching_response)

        
        
        # 处理消息循环
        await _handle_websocket_messages(websocket, session_id, user_id)
        
    except WebSocketDisconnect:
        logger.info(f"用户 {user_id} WebSocket连接正常断开")
    except Exception as e:
        logger.error(f"用户 {user_id} WebSocket连接异常: {e}")
        try:
            await websocket.close(code=1011, reason="服务器内部错误")
        except:
            pass
    finally:
        # 清理资源
        if 'session_id' in locals():
            await _cleanup_session(session_id, user_id)

async def _handle_websocket_messages(websocket: WebSocket, session_id: int, user_id: int):
    """
    处理WebSocket消息循环
    """
    while True:
        try:
            # 接收消息
            data = await websocket.receive_text()
            logger.debug(f"收到用户 {user_id} 的消息:")
            
            # 解析消息
            message = await _parse_websocket_message(data, session_id)
            if not message:
                continue
            
            # 处理不同类型的消息
            if message["type"] == "user_message":
                user_message = message.get("content", "")
                recognized_text = process_audio_recognition(message, asr_client)
                if recognized_text:
                    user_message = recognized_text
                    logging.info(f"用户 {user_id} 发送的消息 recognized_text: {recognized_text}")
                else:
                    user_message = ""
                    logging.info(f"用户 {user_id} 发送的消息 content: {user_message}")
                
                # 处理语音识别：如果消息中有音频数据，先进行语音识别
                # recognized_text = process_audio_recognition(message, asr_client)
                # if recognized_text:
                #     # 如果识别成功，将识别的文字与原始文字合并或替换
                #     if user_message:
                #         # 如果既有文字又有音频，合并两者
                #         user_message = f"{user_message} {recognized_text}"
                #         logging.info(f"合并原始文字和语音识别结果: {user_message}")
                #     else:
                #         # 如果只有音频，使用识别结果
                #         user_message = recognized_text
                #         logging.info(f"使用语音识别结果作为用户消息: {user_message}")

                
                
                response = await teaching_service.process_user_message(
                    session_id, user_message
                )
                
            elif message["type"] == "timeout":
                response = await teaching_service.process_timeout(
                    session_id, message.get("step", "")
                )
                
            elif message["type"] == "heartbeat":
                response = {
                    "type": "heartbeat_ack",
                    "session_id": session_id,
                    "timestamp": _get_current_timestamp()
                }
                
            elif message["type"] == "session_end":
                logger.info(f"用户 {user_id} 主动结束会话")
                await _cleanup_session(session_id, user_id)
                break
                
            else:
                response = {
                    "type": "error",
                    "message": f"未知的消息类型: {message['type']}",
                    "timestamp": _get_current_timestamp()
                }
            
            # 发送响应
            if response:
                # 如果存在content字段且TTS客户端已初始化，则将内容转换为语音
                # 调用封装的函数处理文本转语音
                logging.info(f"发送给用户 {user_id} 的消息: {response}")
                process_tts_conversion(response, tts_client)

                await websocket_manager.send_message(session_id, response)
                
        except WebSocketDisconnect:
            logger.info(f"用户 {user_id} 连接断开")
            break
        except Exception as e:
            logger.error(f"处理用户 {user_id} 消息时出错: {e}")
            error_response = {
                "type": "error",
                "message": "处理消息时发生错误",
                "timestamp": _get_current_timestamp()
            }
            try:
                await websocket_manager.send_message(session_id, error_response)
            except:
                pass
            break

async def _parse_websocket_message(data: str, session_id: int) -> Dict[str, Any]:
    """
    解析WebSocket消息
    """
    try:
        import json
        message = json.loads(data)
        
        # 验证必需字段
        if "type" not in message:
            raise ValueError("消息缺少type字段")
        
        # 添加会话ID（如果不存在）
        if "session_id" not in message:
            message["session_id"] = session_id
            
        return message
        
    except json.JSONDecodeError:
        logger.error(f"消息JSON解析失败: {data}")
        return None
    except Exception as e:
        logger.error(f"消息解析失败: {e}")
        return None

def _get_today_lesson(user_id: int):
    """
    获取用户今日课程
    """
    from app.services.lesson_service import LessonService

    lesson =  lesson_service.get_today_lesson(user_id)
    
    if not lesson:
        # 如果没有今日课程，获取第一天的课程
        lesson =  lesson_service.get_lesson_by_day(1)
        
    return lesson

async def _cleanup_session(session_id: int, user_id: int):
    """
    清理会话资源
    """
    try:
        # 结束教学会话
        await teaching_service.end_teaching_session(session_id)
        
        # 从连接管理器移除
        websocket_manager.disconnect(session_id)
        
        # 更新会话状态
        session_service.update_session_status(session_id, "completed")
        
        logger.info(f"用户 {user_id} 会话 {session_id} 资源清理完成")
        
    except Exception as e:
        logger.error(f"清理会话 {session_id} 资源时出错: {e}")

async def _check_llm_connection():
    """
    检查大模型连接是否正常
    """
    try:
        from app.utils.llm_client import LLMClient
        
        llm_client = LLMClient()
        test_messages = [{"role": "user", "content": "测试连接"}]
        response = await llm_client.generate_response(test_messages, max_tokens=10)
        
        if response:
            logger.info("大模型连接测试成功")
            return True
        else:
            logger.warning("大模型连接测试返回空响应")
            return False
            
    except Exception as e:
        logger.error(f"大模型连接测试失败: {e}")
        return False

def _get_current_timestamp() -> str:
    """获取当前时间戳"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

# 健康检查端点
@app.get("/")
async def root():
    """根端点 - 服务状态检查"""
    return {
        "status": "running",
        "service": "幼儿英语口语教学智能体",
        "version": "1.0.0",
        "timestamp": _get_current_timestamp()
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    from app.utils.database import check_db_connection
    
    # 检查数据库连接
    db_status = await check_db_connection()
    
    # 检查大模型连接
    llm_status = await _check_llm_connection()
    
    status = "healthy" if db_status and llm_status else "unhealthy"
    
    return {
        "status": status,
        "database": "connected" if db_status else "disconnected",
        "llm_service": "connected" if llm_status else "disconnected",
        "timestamp": _get_current_timestamp()
    }

@app.get("/api/v1/system/info")
async def system_info():
    """系统信息端点"""
    import psutil
    import platform
    
    # 获取系统信息
    system_info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "active_sessions": len(websocket_manager.active_connections),
        "max_context_length": settings.MAX_CONTEXT_LENGTH,
        "reading_timeout": settings.READING_TIMEOUT,
        "exam_timeout": settings.EXAM_TIMEOUT,
        "llm_model": settings.TONGYI_MODEL
    }
    
    return system_info

if __name__ == "__main__":
    """开发环境直接运行"""
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式热重载
        log_level="info",
        ws_ping_interval=20,      # WebSocket心跳间隔
        ws_ping_timeout=20,       # WebSocket心跳超时
        timeout_keep_alive=5,     # 保持连接超时
    )