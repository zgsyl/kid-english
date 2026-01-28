from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class TeachingStep(Enum):
    """教学步骤枚举"""
    INTRODUCTION = "introduction"          # 介绍环节
    READING_SENTENCE1 = "reading_1"       # 第一句拼读
    READING_SENTENCE2 = "reading_2"       # 第二句拼读  
    EXAMINATION_SENTENCE1 = "exam_1"      # 第一句考核
    EXAMINATION_SENTENCE2 = "exam_2"      # 第二句考核
    SUMMARY = "summary"                    # 总结环节
    COMPLETED = "completed"               # 教学完成


@dataclass
class TeachingState:
    """教学状态数据类"""
    current_step: TeachingStep
    sentence1_reading_count: int = 0      # 第一句跟读次数
    sentence1_timeout_count: int = 0      # 第一句跟读超时次数
    sentence2_reading_count: int = 0      # 第二句跟读次数
    sentence2_timeout_count: int = 0      # 第二句跟读超时次数

    sentence1_exam_attempts: int = 0      # 第一句考核尝试次数
    sentence1_timeout_attempts: int = 0   # 第一句跟读超时尝试次数

    sentence2_exam_attempts: int = 0      # 第二句考核尝试次数
    sentence2_timeout_attempts: int = 0   # 第二句跟读超时尝试次数

    sentence1_mastered: bool = False      # 第一句是否掌握
    sentence2_mastered: bool = False      # 第二句是否掌握
    learning_issues: list = None          # 学习问题记录
    
    def __post_init__(self):
        if self.learning_issues is None:
            self.learning_issues = []


class TeachingStateMachine:
    """教学状态机，管理教学流程的状态转换"""
    
    def __init__(self, max_reading_attempts: int = 3, max_exam_attempts: int = 2):
        self.state = TeachingState(current_step=TeachingStep.INTRODUCTION)
        self.max_reading_attempts = max_reading_attempts
        self.max_exam_attempts = max_exam_attempts
        
        logger.info("教学状态机初始化完成")
    
    def get_current_step(self) -> TeachingStep:
        """获取当前步骤"""
        return self.state.current_step
    
    def get_state_data(self) -> Dict[str, Any]:
        """获取状态数据"""
        return {
            "current_step": self.state.current_step.value,
            "sentence1_reading_count": self.state.sentence1_reading_count,
            "sentence2_reading_count": self.state.sentence2_reading_count,
            "sentence1_exam_attempts": self.state.sentence1_exam_attempts,
            "sentence2_exam_attempts": self.state.sentence2_exam_attempts,
            "sentence1_mastered": self.state.sentence1_mastered,
            "sentence2_mastered": self.state.sentence2_mastered,
            "learning_issues_count": len(self.state.learning_issues)
        }
    
    def record_reading_attempt(self, sentence_number: int, success: bool = False) -> int:
        """
        记录跟读尝试
        
        Args:
            sentence_number: 句子编号（1或2）
            success: 是否成功跟读
            
        Returns:
            int: 当前尝试次数
        """
        if sentence_number == 1:
            if success:
                self.state.sentence1_reading_count += 1
            count = self.state.sentence1_reading_count

            if not success:
                self.state.sentence1_timeout_count += 1
            
            # 如果达到2次成功跟读，标记为掌握
            if success and count >= 2:
                self.state.sentence1_mastered = True
                
            return count
            
        elif sentence_number == 2:
            #self.state.sentence2_reading_count += 1
            count = self.state.sentence2_reading_count

            if success:
                self.state.sentence2_reading_count += 1

            if not success:
                self.state.sentence2_timeout_count += 1
            
            # 如果达到2次成功跟读，标记为掌握
            if success and count >= 2:
                self.state.sentence2_mastered = True
                
            return count
        else:
            raise ValueError("句子编号必须是1或2")

    def record_timeout_attempt(self, sentence_number: int, success: bool = False) -> int:
        """
        记录跟读尝试
        
        Args:
            sentence_number: 句子编号（1或2）
            success: 是否成功跟读
            
        Returns:
            int: 当前尝试次数
        """
        if sentence_number == 1:
            self.state.sentence1_timeout_count += 1
            count = self.state.sentence1_timeout_count      
            return count
            
        elif sentence_number == 2:
            self.state.sentence2_timeout_count += 1
            count = self.state.sentence2_timeout_count    
            return count
        else:
            raise ValueError("句子编号必须是1或2")
    
    def record_exam_attempt(self, sentence_number: int, success: bool = False) -> int:
        """
        记录考核尝试
        
        Args:
            sentence_number: 句子编号（1或2）
            success: 是否回答正确
            
        Returns:
            int: 当前尝试次数
        """
        if sentence_number == 1:
            if success:
                self.state.sentence1_exam_attempts += 1

            if not success:
                self.state.sentence1_timeout_attempts += 1
            
            if success:
                self.state.sentence1_mastered = True
            elif self.state.sentence1_exam_attempts >= self.max_exam_attempts:
                # 记录学习问题
                self._record_learning_issue(sentence_number, "exam_failed")
                
            return self.state.sentence1_exam_attempts
            
        elif sentence_number == 2:
            if success:
                self.state.sentence2_exam_attempts += 1

            if not success:
                self.state.sentence2_timeout_attempts += 1
            
            if success:
                self.state.sentence2_mastered = True
            elif self.state.sentence2_exam_attempts >= self.max_exam_attempts:
                # 记录学习问题
                self._record_learning_issue(sentence_number, "exam_failed")
                
            return self.state.sentence2_exam_attempts
        else:
            raise ValueError("句子编号必须是1或2")
    
    def _record_learning_issue(self, sentence_number: int, issue_type: str):
        """记录学习问题"""
        issue = {
            "sentence_number": sentence_number,
            "issue_type": issue_type,  # no_repeat, exam_failed, etc.
            "step": self.state.current_step.value,
            "timestamp": self._get_current_timestamp()
        }
        self.state.learning_issues.append(issue)
        logger.info(f"记录学习问题: 句子{sentence_number}, 类型: {issue_type}")
    
    def should_proceed_to_next_reading(self, sentence_number: int) -> bool:
        """
        判断是否应该进入下一句拼读
        
        Args:
            sentence_number: 当前句子编号
            
        Returns:
            bool: 是否应该进入下一句
        """
        if sentence_number == 1:
            # 第一句拼读完成的条件：掌握或达到最大尝试次数
            return (self.state.sentence1_mastered or 
                   self.state.sentence1_reading_count >= self.max_reading_attempts)
        else:
            # 第二句拼读完成的条件：掌握或达到最大尝试次数
            return (self.state.sentence2_mastered or 
                   self.state.sentence2_reading_count >= self.max_reading_attempts)
    
    def should_proceed_to_next_exam(self, sentence_number: int) -> bool:
        """
        判断是否应该进入下一句考核
        
        Args:
            sentence_number: 当前句子编号
            
        Returns:
            bool: 是否应该进入下一句
        """
        if sentence_number == 1:
            # 第一句考核完成的条件：掌握或达到最大尝试次数
            return (self.state.sentence1_mastered or 
                   self.state.sentence1_exam_attempts >= self.max_exam_attempts)
        else:
            # 第二句考核完成的条件：掌握或达到最大尝试次数
            return (self.state.sentence2_mastered or 
                   self.state.sentence2_exam_attempts >= self.max_exam_attempts)
    
    def move_to_next_step(self) -> TeachingStep:
        """移动到下一个教学步骤"""
        current = self.state.current_step
        
        if current == TeachingStep.INTRODUCTION:
            self.state.current_step = TeachingStep.READING_SENTENCE1
            
        elif current == TeachingStep.READING_SENTENCE1:
            #if self.should_proceed_to_next_reading(1):
            self.state.current_step = TeachingStep.READING_SENTENCE2
            # 否则保持在当前步骤
            
        elif current == TeachingStep.READING_SENTENCE2:
            #if self.should_proceed_to_next_reading(2):
            self.state.current_step = TeachingStep.EXAMINATION_SENTENCE1
            # 否则保持在当前步骤
            
        elif current == TeachingStep.EXAMINATION_SENTENCE1:
            #if self.should_proceed_to_next_exam(1):
            self.state.current_step = TeachingStep.EXAMINATION_SENTENCE2
            # 否则保持在当前步骤
            
        elif current == TeachingStep.EXAMINATION_SENTENCE2:
            #if self.should_proceed_to_next_exam(2):
            self.state.current_step = TeachingStep.SUMMARY
            # 否则保持在当前步骤
            
        elif current == TeachingStep.SUMMARY:
            self.state.current_step = TeachingStep.COMPLETED
            
        logger.debug(f"状态转换: {current.value} -> {self.state.current_step.value}")
        return self.state.current_step
    
    def is_teaching_complete(self) -> bool:
        """检查教学是否完成"""
        return self.state.current_step == TeachingStep.COMPLETED
    
    def get_learning_issues(self) -> list:
        """获取学习问题列表"""
        return self.state.learning_issues.copy()
    
    def reset(self):
        """重置状态机"""
        self.state = TeachingState(current_step=TeachingStep.INTRODUCTION)
        logger.info("教学状态机已重置")
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"