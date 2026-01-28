import pytest
from app.agents.state_machine import TeachingStateMachine, TeachingStep

def test_state_machine_initialization():
    sm = TeachingStateMachine()
    assert sm.get_current_step() == TeachingStep.INTRODUCTION

def test_state_transition():
    sm = TeachingStateMachine()
    sm.move_to_next_step()
    assert sm.get_current_step() == TeachingStep.READING_SENTENCE1

def test_reading_attempts():
    sm = TeachingStateMachine()
    sm.record_reading_attempt(1)
    assert sm.state.sentence1_reading_count == 1

def test_teaching_completion():
    sm = TeachingStateMachine()
    # 模拟完成所有步骤
    sm.state.current_step = TeachingStep.SUMMARY
    sm.move_to_next_step()
    assert sm.is_teaching_complete() == True