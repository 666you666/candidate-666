from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from enum import Enum
import copy

from .models import Event, Effect


class PersonStatus(Enum):
    ABSENT = "absent"
    PRESENT_GREETED = "present_greeted"
    PRESENT_UNGREETED = "present_ungreeted"
    LEFT_WAITING = "left_waiting"


@dataclass
class PersonState:
    status: PersonStatus
    left_timestamp: Optional[float] = None


class RobotApplication:
    def __init__(self, absence_timeout_s: float = 10.0):
        self._absence_timeout_s = absence_timeout_s
        self._persons: Dict[str, PersonState] = {}
        self._interaction_count: int = 0   # >0 表示对话或会议进行中

    def _is_interaction_active(self) -> bool:
        return self._interaction_count > 0

    def handle_event(self, event: Event) -> List[Effect]:
        effects: List[Effect] = []
        event_type = event.event_type
        ts = event.timestamp
        pid = event.person_id

        if event_type == "PERSON_ENTERED":
            if pid is None:
                return effects

            state = self._persons.get(pid)

            # 情况1：新访客或已送客后重新进入
            if state is None or state.status == PersonStatus.ABSENT:
                if self._is_interaction_active():
                    # 交互进行中，不迎宾，仅记录在场未迎宾
                    self._persons[pid] = PersonState(status=PersonStatus.PRESENT_UNGREETED)
                else:
                    # 空闲时进入，迎宾
                    effects.append(Effect("wave_hand", "", "greeting"))
                    effects.append(Effect("say", "欢迎光临", "greeting"))
                    self._persons[pid] = PersonState(status=PersonStatus.PRESENT_GREETED)

            # 情况2：已经在场（已迎宾或未迎宾）不重复迎宾
            elif state.status in (PersonStatus.PRESENT_GREETED, PersonStatus.PRESENT_UNGREETED):
                pass

            # 情况3：处于离开等待（不足10秒返回），取消计时，恢复在场且视为已迎宾（不重复迎宾）
            elif state.status == PersonStatus.LEFT_WAITING:
                self._persons[pid] = PersonState(status=PersonStatus.PRESENT_GREETED)

        elif event_type == "PERSON_LEFT":
            if pid is None:
                return effects
            state = self._persons.get(pid)
            if state is None:
                return effects

            if state.status == PersonStatus.PRESENT_GREETED:
                # 已迎宾，开始计时
                self._persons[pid] = PersonState(status=PersonStatus.LEFT_WAITING, left_timestamp=ts)
            elif state.status == PersonStatus.PRESENT_UNGREETED:
                # 未迎宾，直接缺席（不送客）
                self._persons[pid] = PersonState(status=PersonStatus.ABSENT)
            # 其他状态（已经等待、已缺席）忽略

        elif event_type == "CONVERSATION_STARTED":
            self._interaction_count += 1
        elif event_type == "CONVERSATION_ENDED":
            if self._interaction_count > 0:
                self._interaction_count -= 1
        elif event_type == "MEETING_STARTED":
            self._interaction_count += 1
        elif event_type == "MEETING_ENDED":
            if self._interaction_count > 0:
                self._interaction_count -= 1

        elif event_type == "TICK":
            if self._is_interaction_active():
                # 交互进行中：超时的等待者直接消失，不补发送客
                for pid, state in list(self._persons.items()):
                    if state.status == PersonStatus.LEFT_WAITING:
                        if ts - state.left_timestamp >= self._absence_timeout_s:
                            self._persons[pid] = PersonState(status=PersonStatus.ABSENT)
            else:
                # 空闲：超时则送客
                for pid, state in list(self._persons.items()):
                    if state.status == PersonStatus.LEFT_WAITING:
                        if ts - state.left_timestamp >= self._absence_timeout_s:
                            effects.append(Effect("say", "再见", "farewell"))
                            self._persons[pid] = PersonState(status=PersonStatus.ABSENT)

        # 未知事件类型忽略

        return effects

    def snapshot(self) -> Dict[str, Any]:
        """返回内部状态的不可变快照"""
        persons_snapshot = {}
        for pid, state in self._persons.items():
            persons_snapshot[pid] = {
                "status": state.status.value,
                "left_timestamp": state.left_timestamp
            }
        return {
            "persons": persons_snapshot,
            "interaction_count": self._interaction_count,
            "absence_timeout_s": self._absence_timeout_s
        }
