# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Admin endpoints: bank import (FR-16)."""

from fastapi import APIRouter
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUserId, SessionFactory
from app.api.errors import ApiError
from app.domain.bank import Bank, ImportResult, UnknownTopicError
from app.infrastructure.db.bank_import import import_bank

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/import", response_model=ImportResult)
async def import_bank_endpoint(bank: Bank, _: AdminUserId, factory: SessionFactory) -> ImportResult:
    """Topics, questions and tasks in one transaction; a repeated import creates no duplicates."""
    try:
        async with factory() as db, db.begin():
            return await import_bank(db, bank)
    except UnknownTopicError as exc:
        raise ApiError(422, "unknown_topic", "Тема не найдена", detail=f"topicCode {exc.code!r}") from None
    except IntegrityError:  # the bank changed under us (another import without the PostgreSQL lock)
        raise ApiError(409, "import_conflict", "Банк изменился во время импорта, повторите") from None
