import pytest,sys
import asyncio
from unittest.mock import Mock
from app.agents.teaching_agent import TeachingAgent
from app.agents.state_machine import TeachingStep

from unittest.mock import Mock
from asynctest import CoroutineMock as AsyncMock
from app.utils.logger import setup_logging
import logging


import pytest
import asyncio
from unittest.mock import Mock
from app.agents.teaching_agent import TeachingAgent
from app.agents.state_machine import TeachingStep
from app.utils.database import init_db, get_db_session
from app.services.session_service import SessionService
from app.services.user_service import UserService

@pytest.fixture
def mock_db():
    return Mock()

@pytest.fixture
def sample_lesson():
    return {"id": 1, "day_number": 1, "sentence1": "Hi!", "sentence2": "Hello!", "description": "Hi 是你好的意思，hello是你好的意思"}

@pytest.fixture
def teaching_agent(mock_db, sample_lesson):  # 正确定义为fixture
    
    temp_handler = logging.StreamHandler(sys.stdout)
    temp_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    temp_handler.setFormatter(formatter)
    
    # 获取并配置测试日志记录器
    test_logger = logging.getLogger("tests.test_teaching_agent")
    test_logger.addHandler(temp_handler)
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = True  # 确保日志也传播到父记录器
    
    # 直接输出测试开始信息，不依赖配置好的日志系统
    print("\n=== 测试开始 - 手动输出 ===", flush=True)
    
    # 配置日志系统
    test_logger.info("准备配置日志系统")
    setup_logging()
    test_logger.info("开始测试教学智能体初始化")

    init_db()
    db_session = get_db_session()

    session_service = SessionService(db_session) 
    user_service = UserService(db_session)
    session =  session_service.create_session(user_id=6)
    
    return TeachingAgent(
        user_id=6,
        session_id=session.id,
        lesson_content=sample_lesson,
        db_session=db_session
    )

@pytest.mark.asyncio
async def test_teaching_agent_initialization(teaching_agent):
    """测试教学智能体初始化"""
    assert teaching_agent.user_id == 6
    #assert teaching_agent.session_id == session.id
    assert teaching_agent.lesson["day_number"] == 1
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.INTRODUCTION




# @pytest.mark.asyncio
# async def test_start_teaching(teaching_agent):
#     """测试开始教学"""
#     response = await teaching_agent.start_teaching()
    
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.INTRODUCTION



# @pytest.mark.asyncio
# async def test_process_user_input(teaching_agent):
#     """测试Introduction环节默认跳下一个环节"""
#     # 先开始教学
#     await teaching_agent.start_teaching()
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.INTRODUCTION
#     
#     # 在introduction环节，由小程序前端在播放完介绍环境的语音后，小程序前端用户默认不发送任何消息，后台默认开始拼读环节
#     response = await teaching_agent.process_user_input()
    
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE1



# @pytest.mark.asyncio
# async def test_process_user_input(teaching_agent):
#     """测试处理用户输入"""
#     # 先开始教学
#     await teaching_agent.start_teaching()
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.INTRODUCTION
#     # 测试用户响应
#     # 在introduction环节，由小程序前端在播放完介绍环境的语音后，小程序前端用户默认不发送任何消息，后台默认开始拼读环节
#     response = await teaching_agent.process_user_input()
    
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE1

#     #测试用户正常跟读，当前属于第一轮跟读
#     response = await teaching_agent.process_user_input(user_input="hi")
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE1

#     #测试用户正常跟读，当前属于第二轮跟读，跟读后，开始进入第二句的跟读
#     response = await teaching_agent.process_user_input(user_input="hi")
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE2


#     #测试用户跟读，第二句的正常跟读，属于第一轮的跟读。
#     response = await teaching_agent.process_user_input(user_input="hello")
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE2


#     #测试用户跟读，第二句的跟读，假设此时，学生没有发生跟读，跟读超时，这个超时，是发生在第二轮跟读时的超时
#     response = await teaching_agent.process_user_input(user_input="hello", is_timeout = True)
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE2

#     #测试用户跟读，第二句的跟读，假设此时继续发生超时，这个超时，是发生在第三轮的超时，此时进入考试环节，考试环节首先考核第一句。
#     response = await teaching_agent.process_user_input(user_input="hello", is_timeout = True)
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.EXAMINATION_SENTENCE1



#     #开始考核第一句,用户回答正确
#     response = await teaching_agent.process_user_input(user_input="你好")
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.get_current_step() == TeachingStep.EXAMINATION_SENTENCE2













@pytest.mark.asyncio
async def test_process_user_input(teaching_agent):
    """测试处理用户输入"""
    # 先开始教学
    await teaching_agent.start_teaching()
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.INTRODUCTION
    # 测试用户响应
    # 在introduction环节，由小程序前端在播放完介绍环境的语音后，小程序前端用户默认不发送任何消息，后台默认开始拼读环节
    response = await teaching_agent.process_user_input()
    
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE1

    #测试用户正常跟读，当前属于第一轮跟读
    response = await teaching_agent.process_user_input(user_input="hi")
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE1

    #测试用户正常跟读，当前属于第二轮跟读，跟读后，开始进入第二句的跟读
    response = await teaching_agent.process_user_input(user_input="hi")
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE2


    #测试用户跟读，第二句的正常跟读，属于第一轮的跟读。
    response = await teaching_agent.process_user_input(user_input="hello")
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE2


    #测试用户跟读，第二句的跟读，假设此时，学生没有发生跟读，跟读超时，这个超时，是发生在第二轮跟读时的超时
    response = await teaching_agent.process_user_input(user_input="hello", is_timeout = True)
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.READING_SENTENCE2

    #测试用户跟读，第二句的跟读，假设此时继续发生超时，这个超时，是发生在第三轮的超时，此时进入考试环节，考试环节首先考核第一句。
    response = await teaching_agent.process_user_input(user_input="hello", is_timeout = True)
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.EXAMINATION_SENTENCE1

    #开始考核第一句,用户回答错误
    response = await teaching_agent.process_user_input(user_input="天气很不错")
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.EXAMINATION_SENTENCE1

    #开始考核第一句,用户回答再次错误，老师开始进行第二句的考核
    response = await teaching_agent.process_user_input(user_input="天气很不错")
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.EXAMINATION_SENTENCE2


    #开始考核第二句,用户回答正确，老师开始进行总结
    response = await teaching_agent.process_user_input(user_input="hello")
    assert response["type"] == "teaching_response"
    assert teaching_agent.state_machine.get_current_step() == TeachingStep.COMPLETED













# @pytest.mark.asyncio
# async def test_process_timeout(teaching_agent):
#     """测试处理超时"""
#     # 先开始教学
#     teaching_agent.llm_client.generate_response = AsyncMock(return_value="欢迎开始学习！")
#     await teaching_agent.start_teaching()
    
#     # 移动到拼读环节
#     teaching_agent.state_machine.state.current_step = TeachingStep.READING_SENTENCE1
    
#     # 测试超时处理
#     teaching_agent.llm_client.generate_response = AsyncMock(return_value="没关系，我们再试一次。")
#     response = await teaching_agent.process_user_input(is_timeout=True)
    
#     assert response["type"] == "teaching_response"
#     assert teaching_agent.state_machine.state.sentence1_reading_count == 1

# def test_learning_issues_recording(teaching_agent):
#     """测试学习问题记录"""
#     # 模拟多次超时
#     teaching_agent.state_machine.record_reading_attempt(1, success=False)
#     teaching_agent.state_machine.record_reading_attempt(1, success=False)
#     teaching_agent.state_machine.record_reading_attempt(1, success=False)
    
#     issues = teaching_agent.get_learning_issues()
#     assert len(issues) > 0
#     assert issues[0]["sentence_number"] == 1