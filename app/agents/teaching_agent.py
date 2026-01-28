import logging
from math import log
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.agents.state_machine import TeachingStateMachine, TeachingStep
from app.services.context_service import ContextService
from app.utils.llm_client import LLMClient
from app.agents.prompt_templates import get_prompt_for_step

logger = logging.getLogger(__name__)


class TeachingAgent:
    """教学智能体，负责执行具体的教学流程"""

    def __init__(self, user_id: int, session_id: int, lesson_content: Dict[str, Any], 
                 db_session, use_mock_llm: bool = False):
        self.user_id = user_id
        self.session_id = session_id
        self.lesson = lesson_content
        self.db_session = db_session

        # 初始化依赖服务
        self.state_machine = TeachingStateMachine()
        self.context_service = ContextService(db_session)
        self.llm_client = LLMClient()

        # 当前教学句子
        self.sentences = [lesson_content['sentence1'], lesson_content['sentence2']]
        self.description = lesson_content['description']
        self.current_sentence_index = 0  # 0 for sentence1, 1 for sentence2

        # 学习问题记录
        self.learning_issues = []

        logger.info(f"教学智能体初始化: 用户{user_id}, 会话{session_id}, 课程{lesson_content['day_number']}")

    async def start_teaching(self) -> Dict[str, Any]:
        """开始教学，返回初始消息"""
        # 初始化系统提示词
        system_prompt = get_prompt_for_step("introduction", self.sentences)
        self.context_service.add_system_prompt(self.session_id, system_prompt, "introduction")

        # 生成介绍环节的响应
        #logger.info(f"生成介绍环节的响应: {system_prompt}")
        response = await self._generate_llm_response(system_prompt)
        self.context_service.add_assistant_message(self.session_id, response, "introduction")
        logger.info(f"介绍环节响应: {response}")

        # 构建返回前端的消息
        return self._build_websocket_message(response, self.state_machine.get_current_step())

    async def process_user_input(self, user_input: str = None, is_timeout: bool = False) -> Dict[str, Any]:
        """
        处理用户输入或超时事件

        Args:
            user_input: 用户输入文本（语音转文字）
            is_timeout: 是否为超时事件

        Returns:
            Dict[str, Any]: 发送给前端的消息
        """
        current_step = self.state_machine.get_current_step()

        # 保存用户输入（如果不是超时）
        if not is_timeout and user_input:
            self.context_service.add_user_message(self.session_id, user_input, current_step.value)

        # 根据当前步骤处理
        if current_step == TeachingStep.INTRODUCTION:
            return await self._handle_introduction(user_input, is_timeout)
        elif current_step in [TeachingStep.READING_SENTENCE1, TeachingStep.READING_SENTENCE2]:
            return await self._handle_reading_step(user_input, is_timeout)
        elif current_step in [TeachingStep.EXAMINATION_SENTENCE1, TeachingStep.EXAMINATION_SENTENCE2]:
            return await self._handle_examination_step(user_input, is_timeout)
        elif current_step == TeachingStep.SUMMARY:
            return await self._handle_summary(user_input, is_timeout)
        else:
            logger.error(f"未知的教学步骤: {current_step}")
            return self._build_error_message("未知的教学步骤")

    async def _handle_introduction(self, user_input: str, is_timeout: bool) -> Dict[str, Any]:
        """处理介绍环节"""
        # 介绍环节不需要用户输入，直接进入拼读环节
        self.state_machine.move_to_next_step()
        return await self._start_reading_sentence(1)

    async def _handle_reading_step(self, user_input: str, is_timeout: bool) -> Dict[str, Any]:
        """处理拼读环节"""
        sentence_num = 1 if self.state_machine.get_current_step() == TeachingStep.READING_SENTENCE1 else 2
        sentence = self.sentences[sentence_num - 1]
        

        # 获取当前句子的跟读次数
        #reading_count = self.state_machine.state.sentence1_reading_count if sentence_num == 1 else self.state_machine.state.sentence2_reading_count
        reading_count = self.state_machine.state.sentence1_reading_count if sentence_num == 1 else self.state_machine.state.sentence2_reading_count


        if is_timeout:
            # 超时处理
            reading_count = self.state_machine.record_reading_attempt(sentence_num, success=False)

            timeout_count = self.state_machine.state.sentence1_timeout_count if sentence_num == 1 else self.state_machine.state.sentence2_timeout_count
            logger.info(f"跟读超时，句子{sentence_num}，当前第{reading_count}次跟读")


            if timeout_count <= 2:
                # 第一次超时，再次慢读，等待10秒
                prompt = self._build_reading_prompt(sentence, sentence_num, None, True, timeout_count)
                response = await self._generate_llm_response(prompt)
                self.context_service.add_assistant_message(self.session_id, response, f"reading_{sentence_num}")
                return self._build_websocket_message(response, self.state_machine.get_current_step(), waiting=True, timeout_seconds=10)
            else:
                # 第三次超时，记录未跟读，并进入下一句
                self._record_learning_issue(sentence, sentence_num, "no_repeat")
                return await self._proceed_to_next_reading_step(sentence_num)

    

        else:
            # 用户有跟读
            #  这里想加一个逻辑，如果用户有收入，跟读的语句是正确的，才能进行跟读次数的递增。
            #  否则，记录学习问题，并进入下一句。
            if user_input:
                reading_count = self.state_machine.record_reading_attempt(sentence_num, success=True)
                logger.info(f"用户正确跟读，句子{sentence_num}，当前跟读次数{reading_count}")
            
            # 检查是否完成5轮跟读
            if reading_count > 2:
                # 完成2轮跟读，进入下一句
                logger.info(f"用户完成2轮跟读，句子{sentence_num}")
                return await self._proceed_to_next_reading_step(sentence_num)
            else:
                # 继续跟读
                logger.info(f"用户有跟读，句子{sentence_num}，当前跟读次数{reading_count}")
                prompt = self._build_reading_prompt(sentence, sentence_num, user_input, False, reading_count)
                response = await self._generate_llm_response(prompt)
                logger.info(f"Generated reading response for sentence {sentence_num}: {response}")
                self.context_service.add_assistant_message(self.session_id, response, f"reading_{sentence_num}")
                return self._build_websocket_message(response, self.state_machine.get_current_step(), waiting=True, timeout_seconds=30)

    async def _handle_examination_step(self, user_input: str, is_timeout: bool) -> Dict[str, Any]:
        """处理考核环节"""
        sentence_num = 1 if self.state_machine.get_current_step() == TeachingStep.EXAMINATION_SENTENCE1 else 2
        sentence = self.sentences[sentence_num - 1]
        description = self.description
        exam_attempts = self.state_machine.state.sentence1_exam_attempts if sentence_num == 1 else self.state_machine.state.sentence2_exam_attempts


        if is_timeout:
            # 超时处理
            exam_attempts = self.state_machine.record_exam_attempt(sentence_num, success=False)
            # exam_attempts = self.state_machine.state.sentence1_exam_attempts if sentence_num == 1 else self.state_machine.state.sentence2_exam_attempts
            exam_timeout_attempts = self.state_machine.state.sentence1_timeout_attempts if sentence_num == 1 else self.state_machine.state.sentence2_timeout_attempts

            if exam_timeout_attempts <= 2:
                # 第一次超时，再次提问，等待10秒
                prompt = self._build_examination_prompt(sentence, sentence_num, None, True, exam_timeout_attempts)
                response = await self._generate_llm_response(prompt)
                self.context_service.add_assistant_message(self.session_id, response, f"exam_{sentence_num}")
                return self._build_websocket_message(response, self.state_machine.get_current_step(), waiting=True, timeout_seconds=10)
            else:
                # 第三次超时，告知答案，并进入下一句
                self._record_learning_issue(sentence, sentence_num, "exam_failed")
                return await self._proceed_to_next_exam_step(sentence_num)



        else:
            # 用户有回答，判断是否正确（简单通过关键词判断，实际应该用更复杂的方法）
            #is_correct = self._check_answer_correctness(user_input, description)
            if user_input:
                exam_attempts = self.state_machine.record_exam_attempt(sentence_num, success=True)

            if exam_attempts > 1:

                logger.info(f"用户回答考核问题超过1次，句子{sentence_num}")
                return await self._proceed_to_next_exam_step(sentence_num)
            else:                     # 第一次超时，再次提问，等待10秒
                logger.info(f"用户没有超过一次，句子{sentence_num}，当前考核次数{exam_attempts}")
                prompt = self._build_examination_prompt(sentence, sentence_num, None, True, exam_attempts)
                response = await self._generate_llm_response(prompt)
                self.context_service.add_assistant_message(self.session_id, response, f"exam_{sentence_num}")
                return self._build_websocket_message(response, self.state_machine.get_current_step(), waiting=True, timeout_seconds=10)
                
                



            # if is_correct:
            #     # 回答正确，进入下一句
            #     logger.info(f"用户回答正确，句子{sentence_num}")
            #     return await self._proceed_to_next_exam_step(sentence_num)
            # else:
            #     # 回答错误
            #     exam_attempts = self.state_machine.state.sentence1_exam
            #     attempts if sentence_num == 1 else self.state_machine.state.sentence2_exam_attempts
            #     prompt = self._build_examination_prompt(sentence, sentence_num, user_input, False, exam_attempts)
            #     response = await self._generate_llm_response(prompt)
            #     self.context_service.add_assistant_message(self.session_id, response, f"exam_{sentence_num}")

            #     # 如果已经达到最大尝试次数，则记录问题并进入下一句
            #     if exam_attempts >= 2:
            #         self._record_learning_issue(sentence, sentence_num, "exam_failed")
            #         return await self._proceed_to_next_exam_step(sentence_num)
            #     else:
            #         return self._build_websocket_message(response, self.state_machine.get_current_step(), waiting=True, timeout_seconds=10)

    async def _handle_summary(self, user_input: str, is_timeout: bool) -> Dict[str, Any]:
        """处理总结环节"""
        # 生成总结提示词



        # prompt = get_prompt_for_step("summary", self.sentences)
        # self.context_service.add_system_prompt(self.session_id, prompt, "summary")
        # context = self.context_service.get_session_context(self.session_id)
        # response = await self.llm_client.generate_teaching_response(prompt, user_input, context)
        prompt = self._build_summary_prompt(self.sentences)
        response = await self._generate_llm_response(prompt)
        self.context_service.add_assistant_message(self.session_id, response, "summary")

        # 教学完成
        self.state_machine.move_to_next_step()

        # 返回总结消息，不需要等待用户响应
        return self._build_websocket_message(response, self.state_machine.get_current_step(), waiting=False)

    async def _start_reading_sentence(self, sentence_num: int) -> Dict[str, Any]:
        """开始拼读指定句子"""
        sentence = self.sentences[sentence_num - 1]
        prompt = self._build_reading_prompt(sentence, sentence_num, None, False, 0)
        response = await self._generate_llm_response(prompt)
        logging.info(f"Generated reading response for sentence {sentence_num}: {response}")

        self.context_service.add_assistant_message(self.session_id, response, f"reading_{sentence_num}")

        return self._build_websocket_message(response, self.state_machine.get_current_step(), waiting=True, timeout_seconds=30)

    async def _proceed_to_next_reading_step(self, current_sentence_num: int) -> Dict[str, Any]:
        """推进到下一拼读步骤"""
        if current_sentence_num == 1:
            # 从第一句拼读进入第二句拼读
            self.state_machine.move_to_next_step()
            return await self._start_reading_sentence(2)
        else:
            # 从第二句拼读进入考核环节
            self.state_machine.move_to_next_step()
            return await self._start_examination_sentence(1)

    async def _start_examination_sentence(self, sentence_num: int) -> Dict[str, Any]:
        """开始考核指定句子"""
        sentence = self.sentences[sentence_num - 1]
        prompt = self._build_examination_prompt(sentence, sentence_num, None, False, 0)
        response = await self._generate_llm_response(prompt)
        self.context_service.add_assistant_message(self.session_id, response, f"exam_{sentence_num}")

        return self._build_websocket_message(response, self.state_machine.get_current_step(), waiting=True, timeout_seconds=10)

    async def _proceed_to_next_exam_step(self, current_sentence_num: int) -> Dict[str, Any]:
        """推进到下一考核步骤"""
        if current_sentence_num == 1:
            # 从第一句考核进入第二句考核
            self.state_machine.move_to_next_step()
            return await self._start_examination_sentence(2)
        else:
            # 从第二句考核进入总结环节
            self.state_machine.move_to_next_step()
            return await self._handle_summary(None, False)

    def _build_reading_prompt(self, sentence: str, sentence_num: int, user_input: str, is_timeout: bool, timeout_count: int) -> str:
        """构建拼读环节的提示词"""
        base_prompt = get_prompt_for_step("reading", [sentence])

        # 构建当前状态描述
        state_desc = f"当前句子：{sentence}（第{sentence_num}句）\n"
        #state_desc += f"当前句子超时次数：第{timeout_count}次\n"

        if is_timeout:
            state_desc += f"跟读状态：当前句子第{timeout_count}次跟读超时"
        else:
            if user_input:
                state_desc += f"跟读状态: 学生已经跟读了，学生跟读内容为：{user_input}\n"
            else:
                state_desc += "跟读状态：开始拼读"

        # if is_timeout:
        #     if timeout_count == 1:
        #         state_desc += "状态：第一次超时，需要再次慢读并等待10秒"
        #     elif timeout_count == 2:
        #         state_desc += "状态：第二次超时，需要再次慢读并等待10秒"
        #     else:
        #         state_desc += "状态：第三次超时，需要记录问题并进入下一句"
        # else:
        #     if user_input:
        #         state_desc += f"学生跟读：{user_input}\n状态：跟读成功，需要鼓励并继续下一轮"
        #     else:
        #         state_desc += "状态：开始拼读，需要慢速朗读并等待30秒"

        prompt = base_prompt + "\n\n" + state_desc

        #在下面的代码中，将prompt也保存到context中，方便后续的分析。
        self.context_service.add_system_prompt(self.session_id, prompt, f"reading_{sentence_num}")

        return prompt

    def _build_examination_prompt(self, sentence: str, sentence_num: int, user_input: str, is_timeout: bool, timeout_count: int) -> str:
        """构建考核环节的提示词"""
        base_prompt = get_prompt_for_step("exam", [sentence])

        # 构建当前状态描述
        state_desc = f"考核句子：{sentence}（第{sentence_num}句）\n"

        if is_timeout:
            state_desc += f"考核状态：当前句子第{timeout_count}次考核超时"
        else:
            if user_input:
                state_desc += f"考核状态: 学生已经跟读了，学生跟读内容为：{user_input}， 当前为第{timeout_count}次考核\n"
            else:
                state_desc += "考核状态：开始进行考核"
        
        prompt = base_prompt + "\n\n" + state_desc
        self.context_service.add_system_prompt(self.session_id, prompt, f"exam_{sentence_num}")
        return prompt

    def _build_summary_prompt(self, sentences: List[str]) -> str:
        """构建总结环节的提示词"""
        base_prompt = get_prompt_for_step("summary", sentences)

        #读取context中的所有句子
        state_desc = ""
        for sentence_num, sentence in enumerate(sentences, 1):
            state_desc += f"要总结的句子：{sentence}（第{sentence_num}句）\n"
            
        prompt = base_prompt + "\n\n" + state_desc
        
        self.context_service.add_system_prompt(self.session_id, prompt, "summary")
        return prompt
    

    def _check_answer_correctness(self, user_answer: str, correct_sentence: str) -> bool:
        """检查用户回答是否正确（简单实现）"""
        # 转换为小写并去除标点
        import string
        logger.debug(f"检查回答是否正确，用户回答：{user_answer}，正确句子：{correct_sentence}")
        user_clean = user_answer.lower().translate(str.maketrans('', '', string.punctuation)).strip()
        correct_clean = correct_sentence.lower().translate(str.maketrans('', '', string.punctuation)).strip()

        # 简单包含检查，实际应该用更复杂的方法
        return user_clean in correct_clean or correct_clean in user_clean

    def _record_learning_issue(self, sentence: str, sentence_num: int, issue_type: str):
        """记录学习问题"""
        issue = {
            "sentence_content": sentence,
            "sentence_order": sentence_num,
            "record_type": issue_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.learning_issues.append(issue)
        logger.info(f"记录学习问题: 句子{sentence_num} - {issue_type}")

    async def _generate_llm_response(self, prompt: str, user_input: str = None) -> str:
        """生成LLM响应"""
        # 获取上下文
        context = self.context_service.get_session_context(self.session_id, include_system=True)

        logger.debug(f"获取会话 {self.session_id} 的上下文，共 {len(context)} 条消息")

        # 调用LLM
        response = await self.llm_client.generate_teaching_response(prompt, user_input, context)
        return response

    def _build_websocket_message(self, content: str, step: TeachingStep, 
                               waiting: bool = False, timeout_seconds: int = None) -> Dict[str, Any]:
        """构建WebSocket消息"""
        message = {
            "type": "teaching_response",
            "session_id": self.session_id,
            "content": content,
            "step": step.value,
            "waiting_for_user": waiting,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if waiting and timeout_seconds is not None:
            message["timeout_seconds"] = timeout_seconds

        return message

    def _build_error_message(self, error_msg: str) -> Dict[str, Any]:
        """构建错误消息"""
        return {
            "type": "error",
            "session_id": self.session_id,
            "content": f"教学过程中出现错误：{error_msg}",
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_learning_issues(self) -> List[Dict[str, Any]]:
        """获取学习问题列表"""
        return self.learning_issues

    def is_teaching_complete(self) -> bool:
        """检查教学是否完成"""
        return self.state_machine.is_teaching_complete()