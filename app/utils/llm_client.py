import logging
import openai
from typing import List, Dict, Any, Optional
import asyncio
import time
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config.settings import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """大模型客户端，封装通义千问的调用"""
    
    def __init__(self):
        self.api_key = settings.TONGYI_API_KEY
        self.model = settings.TONGYI_MODEL
        self.base_url = settings.TONGYI_API_BASE
        self.max_tokens = settings.TONGYI_MAX_TOKENS
        self.timeout = 30
        
        # 配置OpenAI客户端（通义千问使用兼容OpenAI的接口）
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        logger.info(f"LLM客户端初始化完成，模型: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_response(self, messages: List[Dict[str, str]], 
                              temperature: float = 0.7,
                              max_tokens: Optional[int] = None) -> str:
        """
        调用大模型生成响应
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "你好"}]
            temperature: 生成温度
            max_tokens: 最大token数
            
        Returns:
            str: 模型生成的响应内容
        """

        # 使用异步方式调用（在实际环境中可能需要使用异步客户端）
        logger.debug(f"调用LLM，消息数: {len(messages)}, 温度: {temperature}, 最大token数: {max_tokens or self.max_tokens}")
    
        try:
            start_time = time.time()
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or self.max_tokens,
                    stream=False  # 非流式响应
                )
            )

            content = response.choices[0].message.content
            usage = response.usage
            
            elapsed_time = time.time() - start_time
            logger.debug(f"LLM调用成功: {len(content)}字符, "
                        f"耗时: {elapsed_time:.2f}s, "
            
                        f"Token使用: {usage.total_tokens if usage else 'N/A'}")
            return content

        except openai.APITimeoutError as e:
            logger.error(f"LLM调用超时: {e}")
            raise
        except openai.APIError as e:
            logger.error(f"LLM API错误: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM调用未知错误: {e}")
            raise

    async def generate_teaching_response(self, system_prompt: str, user_input: str = None, 
                                       context: List[Dict] = None) -> str:
        """
        生成教学响应（专门为教学场景优化）
        
        Args:
            system_prompt: 系统提示词，定义AI角色和教学规则
            user_input: 用户输入（可选）
            context: 对话上下文（可选）
            
        Returns:
            str: 教学响应
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加上下文
        if context:
            messages.extend(context)
        
        # 添加当前用户输入
        if user_input:
            messages.append({"role": "user", "content": user_input})
        
        # 为教学场景调整参数
        logger.debug(f"生成教学响应，系统提示词: {system_prompt}, 用户输入: {user_input}, 上下文消息数: {len(context)}")
        
        response = await self.generate_response(
            messages=messages,
            temperature=0.8,  # 稍高的温度使回复更有创造性
            max_tokens=500    # 限制响应长度
        )
        return response

    async def check_connection(self) -> bool:
        """检查与大模型的连接是否正常"""
        try:
            test_messages = [{"role": "user", "content": "Hello, respond with 'OK'"}]
            response = await self.generate_response(test_messages, max_tokens=10)
            return bool(response and "OK" in response)
        except Exception as e:
            logger.error(f"大模型连接检查失败: {e}")
            return False

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量（粗略估算）
        注意：这是一个简单的估算，实际应该使用模型对应的tokenizer
        """
        # 中文大致按字符数估算，英文按单词数估算
        # 这是一个粗略的估算，实际使用中应该根据具体模型调整
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        other_chars = len(text) - chinese_chars
        # 假设中文字符每个1.5token，其他字符每个0.8token
        return int(chinese_chars * 1.5 + other_chars * 0.8)

    async def batch_generate_responses(self, requests: List[Dict]) -> List[str]:
        """
        批量生成响应（用于测试或批量处理）
        
        Args:
            requests: 请求列表，每个元素包含messages和参数
            
        Returns:
            List[str]: 响应列表
        """
        tasks = []
        for req in requests:
            task = self.generate_response(**req)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)


class MockLLMClient(LLMClient):
    """模拟LLM客户端，用于测试和开发"""
    
    def __init__(self):
        self.responses = {
            "introduction": "小朋友你好呀！今天我们要认识2个超有用的英文短句，学会了就能跟妈妈、老师打招呼啦～",
            "reading": "现在我们来慢慢读这个短句，小朋友跟着我一起读哦～ H——i！",
            "exam": "太厉害啦！答对了！",
            "summary": "小朋友，今天我们一共学习了2个英文短句，分别是..."
        }
        logger.info("使用模拟LLM客户端")
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              temperature: float = 0.7,
                              max_tokens: Optional[int] = None) -> str:
        """模拟生成响应"""
        # 简单的逻辑：根据最后一条消息内容返回预设响应
        last_message = messages[-1]["content"] if messages else ""
        
        if "介绍" in last_message or "开场" in last_message:
            return self.responses["introduction"]
        elif "读" in last_message or "跟读" in last_message:
            return self.responses["reading"]
        elif "考核" in last_message or "游戏" in last_message:
            return self.responses["exam"]
        elif "总结" in last_message:
            return self.responses["summary"]
        else:
            return "这是一个模拟响应。在实际系统中，这里会是AI老师的真实回复。"
    
    async def check_connection(self) -> bool:
        return True


# 创建全局LLM客户端实例
def create_llm_client(use_mock: bool = False) -> LLMClient:
    """创建LLM客户端实例"""
    if use_mock or not settings.TONGYI_API_KEY or settings.TONGYI_API_KEY == "your_tongyi_api_key_here":
        logger.info("使用模拟LLM客户端（开发模式）")
        return MockLLMClient()
    else:
        return LLMClient()