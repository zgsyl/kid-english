
import pytest
import logging
import sys
from app.services.user_service import UserService
from app.models.user import User
from app.utils.logger import setup_logging
from app.utils.database import init_db, get_db_session

# 启用pytest捕获日志
@pytest.mark.asyncio
# 设置此测试的日志捕获级别
@pytest.mark.filterwarnings("ignore::Warning")
def test_register_user():
    # 创建一个临时的控制台日志处理器，直接输出到sys.stdout
    temp_handler = logging.StreamHandler(sys.stdout)
    temp_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    temp_handler.setFormatter(formatter)
    
    # 获取并配置测试日志记录器
    test_logger = logging.getLogger("tests.test_user_service")
    test_logger.addHandler(temp_handler)
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = True  # 确保日志也传播到父记录器
    
    # 直接输出测试开始信息，不依赖配置好的日志系统
    print("\n=== 测试开始 - 手动输出 ===", flush=True)
    
    # 配置日志系统
    test_logger.info("准备配置日志系统")
    setup_logging()
    test_logger.info("开始测试用户注册功能")

    # 初始化数据库
    test_logger.info("初始化数据库连接")
    init_db()
    db_session = get_db_session()
    
    # 创建用户服务实例
    test_logger.info("创建UserService实例")
    user_service = UserService(db_session)
    
    # 准备测试数据
    user_data = {
        "wechat_openid": "test_openid",
        "nickname": "测试用户",
        "age": 5
    }
    test_logger.info(f"准备用户数据: {user_data}")
    
    # 执行注册/登录操作
    test_logger.info("执行用户注册或登录")
    user = user_service.register_or_login_user("test_openid", user_data)
    
    # 记录结果
    test_logger.info(f"注册/登录结果: 用户ID={user.id}")

    # 断言验证
    test_logger.info("开始断言验证")
    assert user is not None, "用户对象不应为空"
    assert user.wechat_openid == "test_openid", "微信OpenID应匹配"
    assert user.nickname == "测试用户", "昵称应匹配"
    assert user.age == 5, "年龄应匹配"
    test_logger.info("所有断言验证通过")
    
    # 确保所有日志被刷新
    for handler in test_logger.handlers:
        handler.flush()
    
    # 手动输出测试结束信息
    print("=== 测试结束 - 手动输出 ===\n", flush=True)
