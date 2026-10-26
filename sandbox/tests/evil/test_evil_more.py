# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

from test_evil_code import assert_contained, pytestmark, run_evil  # noqa: F401


async def test_infinite_recursion_is_reported_as_error() -> None:
    code = "def solve(a, b):\n    return solve(a, b)\n"

    result, elapsed = await run_evil(code)

    assert result.verdict != "passed"
    assert "recursion" in (result.tests[0].error or "").lower()
    await assert_contained(elapsed)


async def test_spawned_shell_sleep_does_not_outlive_the_run() -> None:
    code = "import os\ndef solve(a, b):\n    os.system('sleep 60')\n    return 3\n"

    result, elapsed = await run_evil(code)

    assert result.verdict in {"timeout", "failed", "error"}
    await assert_contained(elapsed)


async def test_docker_socket_and_dns_are_unreachable() -> None:
    code = (
        "import os, socket\n"
        "def solve(a, b):\n"
        "    if os.path.exists('/var/run/docker.sock'):\n"
        "        return 'docker.sock'\n"
        "    socket.gethostbyname('example.com')\n"
        "    return 3\n"
    )

    result, elapsed = await run_evil(code)

    assert result.verdict != "passed"
    assert "docker.sock" not in (result.tests[0].actual or "")
    await assert_contained(elapsed)
