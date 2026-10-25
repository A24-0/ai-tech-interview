# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "docker: needs a running Docker daemon and the sandbox image")
