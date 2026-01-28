import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

from app.config.settings import settings

def setup_logging():
    """配置日志系统，确保在pytest环境中也能输出日志"""
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    
    # 清除已有的处理器，避免重复配置
    root_logger.handlers.clear()
    
    # 设置根日志级别
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    console_formatter = logging.Formatter(settings.LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 创建文件处理器
    file_handler = RotatingFileHandler(
        log_dir / "teaching_agent.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    file_formatter = logging.Formatter(settings.LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 设置特定库的日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("websockets").setLevel(logging.WARNING)
    
    # 确保测试日志记录器也能输出日志
    test_logger = logging.getLogger("tests")
    test_logger.setLevel(logging.INFO)
    
    # 直接使用根日志记录器记录初始化信息
    root_logger.info("日志系统初始化完成")
    
    # 添加一个确保日志被刷新的处理
    def flush_handlers(record):
        for handler in root_logger.handlers:
            handler.flush()
    
    # 添加一个日志过滤器来确保日志被刷新
    class FlushFilter(logging.Filter):
        def filter(self, record):
            flush_handlers(record)
            return True
    
    for handler in root_logger.handlers:
        handler.addFilter(FlushFilter())