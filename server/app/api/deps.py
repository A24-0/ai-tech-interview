# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Shared FastAPI dependencies: database session and the authenticated user."""

import os
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_session

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> uuid.UUID:
    """User id from the access token: JWT HS256 signed with JWT_SECRET, user id in `sub`."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Нужен токен доступа", {"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, os.environ["JWT_SECRET"], algorithms=["HS256"])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Недействительный токен доступа", {"WWW-Authenticate": "Bearer"}
        ) from exc


DbSession = Annotated[AsyncSession, Depends(get_session)]
CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
