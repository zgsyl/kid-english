import json
import hashlib
from datetime import datetime, date
from typing import Any, Dict

def generate_session_id(user_id: int) -> str:
    """生成会话ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_str = f"{user_id}_{timestamp}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:12]

def format_timestamp(dt: datetime = None) -> str:
    """格式化时间戳"""
    if not dt:
        dt = datetime.utcnow()
    return dt.isoformat() + "Z"

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全的JSON解析"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def calculate_age(birth_date: date) -> int:
    """计算年龄"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def validate_wechat_openid(openid: str) -> bool:
    """验证微信openid格式"""
    if not openid or not isinstance(openid, str):
        return False
    # 简单的格式验证，实际应根据微信openid的格式进行调整
    return len(openid) >= 10 and openid.isalnum()