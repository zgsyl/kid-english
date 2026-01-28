import logging
import json
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from app.api.websocket_manager import WebSocketManager
from app.services.teaching_service import TeachingService
from app.services.session_service import SessionService
from app.services.user_service import UserService
from app.utils.database import get_db

logger = logging.getLogger(__name__)

# 创建WebSocket管理器实例
websocket_manager = WebSocketManager()


class WebSocketRouteHandler:
    """WebSocket路由处理器"""
    
    def __init__(self):
        self.teaching_service = None
        self.session_service = None
        self.user_service = None
        
    async def initialize_services(self, db):
        """初始化服务实例"""
        self.teaching_service = TeachingService(db)
        self.session_service = SessionService(db)
        self.user_service = UserService(db)
    
    async def handle_websocket_connection(self, websocket: WebSocket, user_id: int):
        """
        处理WebSocket连接
        
        Args:
            websocket: WebSocket连接
            user_id: 用户ID
        """
        logger.info(f"用户 {user_id} 尝试连接WebSocket")
        
        # 获取数据库会话
        db = next(get_db())
        await self.initialize_services(db)
        
        try:
            # 验证用户
            user = await self.user_service.get_user_by_id(user_id)
            if not user:
                await websocket.close(code=1008, reason="用户不存在")
                return
            
            # 接受连接
            await websocket.accept()
            logger.info(f"用户 {user_id} WebSocket连接已建立")
            
            # 创建教学会话
            session = await self.session_service.create_session(user_id)
            session_id = session.id
            
            # 管理连接
            await websocket_manager.connect(websocket, session_id)
            
            # 发送欢迎消息
            welcome_msg = {
                "type": "session_start",
                "session_id": session_id,
                "user_id": user_id,
                "message": "教学会话已开始，准备获取今日课程...",
                "timestamp": self._get_current_timestamp()
            }
            await websocket_manager.send_message(session_id, welcome_msg)
            
            # 获取今日课程并开始教学
            lesson = await self.user_service.get_today_lesson_for_user(user_id)
            if not lesson:
                await self._send_error(websocket, session_id, "无法获取今日课程")
                return
            
            # 开始教学
            teaching_response = await self.teaching_service.start_teaching_session(
                user_id, session_id, lesson.id
            )
            await websocket_manager.send_message(session_id, teaching_response)
            
            # 处理消息循环
            await self._handle_message_loop(websocket, session_id, user_id)
            
        except WebSocketDisconnect:
            logger.info(f"用户 {user_id} WebSocket连接正常断开")
        except Exception as e:
            logger.error(f"用户 {user_id} WebSocket连接异常: {e}")
            await self._cleanup_connection(user_id, session_id)
        finally:
            await self._cleanup_connection(user_id, session_id)
    
    async def _handle_message_loop(self, websocket: WebSocket, session_id: int, user_id: int):
        """
        处理消息循环
        
        Args:
            websocket: WebSocket连接
            session_id: 会话ID
            user_id: 用户ID
        """
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                logger.debug(f"收到用户 {user_id} 的消息: {data}")
                
                # 解析消息
                message = await self._parse_message(data, session_id)
                if not message:
                    continue
                
                # 处理消息
                response = await self._process_message(message, session_id, user_id)
                if response:
                    await websocket_manager.send_message(session_id, response)
                    
                # 检查是否应该结束循环
                if message.get("type") == "session_end":
                    break
                    
            except WebSocketDisconnect:
                logger.info(f"用户 {user_id} 连接断开")
                break
            except Exception as e:
                logger.error(f"处理用户 {user_id} 消息时出错: {e}")
                error_response = self._build_error_response(session_id, "处理消息时发生错误")
                try:
                    await websocket_manager.send_message(session_id, error_response)
                except:
                    pass
                break
    
    async def _process_message(self, message: Dict[str, Any], session_id: int, user_id: int) -> Dict[str, Any]:
        """
        处理消息
        
        Args:
            message: 消息数据
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            Dict: 响应消息
        """
        message_type = message["type"]
        
        if message_type == "user_message":
            return await self.teaching_service.process_user_message(
                session_id, message.get("content", "")
            )
            
        elif message_type == "timeout":
            return await self.teaching_service.process_timeout(
                session_id, message.get("step", "")
            )
            
        elif message_type == "heartbeat":
            return {
                "type": "heartbeat_ack",
                "session_id": session_id,
                "timestamp": self._get_current_timestamp()
            }
            
        elif message_type == "session_status":
            status = await self.teaching_service.get_session_status(session_id)
            return {
                "type": "session_status",
                "session_id": session_id,
                "status": status,
                "timestamp": self._get_current_timestamp()
            }
            
        elif message_type == "session_end":
            await self.teaching_service.end_teaching_session(session_id)
            await self.session_service.end_session(session_id)
            return {
                "type": "session_end_ack",
                "session_id": session_id,
                "message": "会话已结束",
                "timestamp": self._get_current_timestamp()
            }
            
        else:
            return self._build_error_response(session_id, f"未知的消息类型: {message_type}")
    
    async def _parse_message(self, data: str, session_id: int) -> Dict[str, Any]:
        """
        解析消息
        
        Args:
            data: 原始消息数据
            session_id: 会话ID
            
        Returns:
            Dict: 解析后的消息
        """
        try:
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
    
    async def _send_error(self, websocket: WebSocket, session_id: int, error_msg: str):
        """发送错误消息"""
        error_response = self._build_error_response(session_id, error_msg)
        try:
            await websocket.send_text(json.dumps(error_response))
        except:
            pass
    
    def _build_error_response(self, session_id: int, error_msg: str) -> Dict[str, Any]:
        """构建错误响应"""
        return {
            "type": "error",
            "session_id": session_id,
            "message": error_msg,
            "timestamp": self._get_current_timestamp()
        }
    
    async def _cleanup_connection(self, user_id: int, session_id: int):
        """清理连接资源"""
        try:
            if session_id:
                await self.teaching_service.end_teaching_session(session_id)
                websocket_manager.disconnect(session_id)
                logger.info(f"用户 {user_id} 会话 {session_id} 资源清理完成")
        except Exception as e:
            logger.error(f"清理连接资源失败: {e}")
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# 创建路由处理器实例
websocket_handler = WebSocketRouteHandler()


# WebSocket端点
async def teaching_websocket(websocket: WebSocket, user_id: int):
    """
    教学WebSocket端点
    
    Args:
        websocket: WebSocket连接
        user_id: 用户ID
    """
    await websocket_handler.handle_websocket_connection(websocket, user_id)