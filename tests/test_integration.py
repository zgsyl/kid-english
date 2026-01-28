import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.utils.database import get_db

# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # 创建表
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
    # 清理表
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_user_registration(client):
    """测试用户注册"""
    user_data = {
        "wechat_openid": "test_openid_123",
        "nickname": "测试用户",
        "age": 5,
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    response = client.post("/api/v1/users/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["wechat_openid"] == "test_openid_123"
    assert data["nickname"] == "测试用户"
    assert data["current_lesson_day"] == 1

def test_get_user(client):
    """测试获取用户信息"""
    # 先创建用户
    user_data = {
        "wechat_openid": "test_openid_456",
        "nickname": "测试用户2"
    }
    create_response = client.post("/api/v1/users/register", json=user_data)
    user_id = create_response.json()["id"]
    
    # 获取用户信息
    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["wechat_openid"] == "test_openid_456"

def test_get_today_lesson(client):
    """测试获取今日课程"""
    # 创建用户
    user_data = {
        "wechat_openid": "test_openid_789",
        "nickname": "测试用户3"
    }
    create_response = client.post("/api/v1/users/register", json=user_data)
    user_id = create_response.json()["id"]
    
    # 获取今日课程
    response = client.get(f"/api/v1/lessons/today/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert "sentence1" in data
    assert "sentence2" in data
    assert data["day_number"] == 1

def test_websocket_connection():
    """测试WebSocket连接"""
    # 这里需要实际的WebSocket测试
    # 可以使用websockets库进行测试
    pass