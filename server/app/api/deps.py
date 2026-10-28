# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Request dependencies. Auth is a placeholder until the real JWT module lands."""

import os
import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.errors import ApiError
from app.infrastructure.db.session import get_session, get_session_factory

_NAMESPACE = uuid.UUID("5d3f1c0e-8a1b-4c55-9b0a-2f6f0c1d7a11")


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Требуется авторизация")
    token = authorization[7:].strip()
    if not token:
        raise ApiError(401, "unauthorized", "Требуется авторизация")
    return token


async def get_current_user_id(authorization: Annotated[str | None, Header()] = None) -> uuid.UUID:
    """Stub: any Bearer token identifies a user; the same token is the same user.
    A token that is itself a UUID is taken as the user id."""
    token = _bearer_token(authorization)
    try:
        return uuid.UUID(token)
    except ValueError:
        return uuid.uuid5(_NAMESPACE, token)


async def require_admin(authorization: Annotated[str | None, Header()] = None) -> uuid.UUID:
    """Stub of role=admin: the token must be listed in ADMIN_TOKENS (comma-separated)."""
    token = _bearer_token(authorization)
    admins = {t.strip() for t in os.environ.get("ADMIN_TOKENS", "").split(",") if t.strip()}
    if token not in admins:
        raise ApiError(403, "forbidden", "Нужна роль администратора")
    return uuid.uuid5(_NAMESPACE, token)


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
AdminUserId = Annotated[uuid.UUID, Depends(require_admin)]
SessionFactory = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]
DbSession = Annotated[AsyncSession, Depends(get_session)]
