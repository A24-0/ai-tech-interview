# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Interview session lifecycle (State pattern): what each status allows.

active -> finished (POST /finish or the interviewer's finish step);
active -> abandoned (no activity for too long, S5-Y1).
A finished or abandoned session takes no messages and no task.
"""

from typing import Literal

SessionStatus = Literal["active", "finished", "abandoned"]


class DomainError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _not_active() -> DomainError:
    return DomainError("session_not_active", "Интервью уже завершено")


class SessionState:
    status: SessionStatus

    def add_message(self) -> None:
        raise _not_active()

    def assign_task(self, has_task: bool) -> None:
        raise _not_active()

    def finish(self) -> SessionStatus:
        raise _not_active()

    def abandon(self) -> SessionStatus:
        raise _not_active()


class Active(SessionState):
    status = "active"

    def add_message(self) -> None:
        pass

    def assign_task(self, has_task: bool) -> None:
        if has_task:
            raise DomainError("task_already_assigned", "Задача уже выдана")

    def finish(self) -> SessionStatus:
        return "finished"

    def abandon(self) -> SessionStatus:
        return "abandoned"


class Finished(SessionState):
    status = "finished"

    def finish(self) -> SessionStatus:
        return "finished"  # a repeated finish (client retry) is harmless


class Abandoned(SessionState):
    status = "abandoned"


_STATES: dict[str, SessionState] = {state.status: state for state in (Active(), Finished(), Abandoned())}


def state_of(status: str) -> SessionState:
    return _STATES[status]
