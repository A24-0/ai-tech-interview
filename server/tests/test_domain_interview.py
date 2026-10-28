# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Session lifecycle rules: what each status allows."""

import pytest

from app.domain.interview import DomainError, state_of


def test_active_session_takes_messages_task_and_closes():
    active = state_of("active")
    active.add_message()
    active.assign_task(has_task=False)
    assert active.finish() == "finished"
    assert active.abandon() == "abandoned"


def test_task_is_assigned_once():
    with pytest.raises(DomainError) as exc:
        state_of("active").assign_task(has_task=True)
    assert exc.value.code == "task_already_assigned"


@pytest.mark.parametrize("status", ["finished", "abandoned"])
def test_closed_session_takes_nothing(status):
    state = state_of(status)
    for action in (state.add_message, lambda: state.assign_task(False), state.abandon):
        with pytest.raises(DomainError) as exc:
            action()
        assert exc.value.code == "session_not_active"


def test_finish_is_repeatable_but_not_after_abandon():
    assert state_of("finished").finish() == "finished"
    with pytest.raises(DomainError):
        state_of("abandoned").finish()
