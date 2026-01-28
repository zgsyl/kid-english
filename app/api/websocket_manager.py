import logging
import json
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接: session_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        logger.info("WebSocket管理器初始化完成")
    
    async def connect(self, websocket: WebSocket, session_id: int):
        """
        保存WebSocket连接到管理器
        
        Args:
            websocket: WebSocket连接
            session_id: 会话ID
        """
        # 注意：连接已经在外部被accept()了，这里只需要保存连接
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket连接已建立: 会话{session_id}")
    
    def disconnect(self, session_id: int):
        """
        断开WebSocket连接
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket连接已断开: 会话{session_id}")
    
    async def send_message(self, session_id: int, message: Dict):
        """
        向指定会话发送消息
        
        Args:
            session_id: 会话ID
            message: 消息数据
        """
        websocket = self.active_connections.get(session_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message))
                logger.debug(f"消息已发送到会话{session_id}: {message.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"发送消息到会话{session_id}失败: {e}")
                self.disconnect(session_id)
        else:
            logger.warning(f"尝试向不存在的连接发送消息: 会话{session_id}")
    
    async def broadcast(self, message: Dict, exclude_sessions: List[int] = None):
        """
        广播消息到所有连接
        
        Args:
            message: 消息数据
            exclude_sessions: 要排除的会话ID列表
        """
        if exclude_sessions is None:
            exclude_sessions = []
        
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            if session_id in exclude_sessions:
                continue
                
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"广播消息到会话{session_id}失败: {e}")
                disconnected.append(session_id)
        
        # 清理断开连接的会话
        for session_id in disconnected:
            self.disconnect(session_id)
    
    def get_connected_sessions(self) -> List[int]:
        """
        获取所有连接的会话ID
        
        Returns:
            List[int]: 会话ID列表
        """
        return list(self.active_connections.keys())
    
    def is_connected(self, session_id: int) -> bool:
        """
        检查指定会话是否连接
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否连接
        """
        return session_id in self.active_connections
    
    def get_connection_count(self) -> int:
        """
        获取连接数量
        
        Returns:
            int: 连接数量
        """
        return len(self.active_connections)


# 创建全局WebSocket管理器实例
websocket_manager = WebSocketManager()