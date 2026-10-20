# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api import interviews, runs
from app.api.errors import install_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="AI Tech Interview API")
    install_error_handlers(app)
    app.include_router(interviews.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    return app


app = create_app()
