# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Request dependencies. Auth is a placeholder until the real JWT module lands."""

import uuid
from typing import Annotated

from fastapi import Depends, Header

from app.api.errors import ApiError

_NAMESPACE = uuid.UUID("5d3f1c0e-8a1b-4c55-9b0a-2f6f0c1d7a11")


async def get_current_user_id(authorization: Annotated[str | None, Header()] = None) -> uuid.UUID:
    """Stub: any Bearer token identifies a user; the same token is the same user."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Требуется авторизация")
    token = authorization[7:].strip()
    if not token:
        raise ApiError(401, "unauthorized", "Требуется авторизация")
    return uuid.uuid5(_NAMESPACE, token)


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
