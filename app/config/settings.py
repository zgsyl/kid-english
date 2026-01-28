import os
from pydantic_settings import BaseSettings
from pydantic import  ConfigDict
from typing import Optional

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    APP_NAME: str = "幼儿英语口语教学智能体"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置
    #DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/teaching_agent"
    #DATABASE_URL: str = "postgresql+asyncpg://zch:123456@120.24.120.22/site_backend"
    DATABASE_URL: str = "postgresql://zch:123456@120.24.108.58/site_backend"


    
    # 大模型配置
    TONGYI_API_KEY: str = "sk-59474b60399e4719b9afb3f3ef4bd010"
    TONGYI_MODEL: str = "qwen-plus"
    TONGYI_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    TONGYI_MAX_TOKENS: int = 2000
    
    # WebSocket配置
    WEBSOCKET_HOST: str = "0.0.0.0"
    WEBSOCKET_PORT: int = 8000
    
    # 上下文配置
    MAX_CONTEXT_LENGTH: int = 20
    MAX_TOKENS_PER_MESSAGE: int = 500
    
    # 超时配置
    READING_TIMEOUT: int = 30
    EXAM_TIMEOUT: int = 10
    WEBSOCKET_PING_INTERVAL: int = 20
    WEBSOCKET_PING_TIMEOUT: int = 20
    
    # 日志配置
    LOG_LEVEL: str = "DEBUG"
    #LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    
    # 教学配置
    MAX_READING_ATTEMPTS: int = 3
    MAX_EXAM_ATTEMPTS: int = 2
    REQUIRED_READING_ROUNDS: int = 5
    
    # class Config:
    #     env_file = ".env"
    #     case_sensitive = True
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

# 创建全局配置实例
settings = Settings()