from enum import IntEnum
from dataclasses import dataclass, field
from inspect_ai.solver import TaskState

class BP(IntEnum):
    """
    Четыре breakpoint-а в жизненном цикле одного sample.
    Нумерация важна — используется для сортировки и конфигурирования.
    """
    BEFORE_GENERATE    = 0  # state готов, до первого generate()
    AFTER_TOOL_CALL    = 1  # модель вернула tool_calls, до их исполнения
    AFTER_TOOL_RESULT  = 2  # tool_result добавлен в messages
    AFTER_FINAL_ANSWER = 3  # модель выдала финальный ответ (нет tool_calls)

@dataclass
class BPContext:
    bp: BP
    state: TaskState
    meta: dict = field(default_factory=dict)