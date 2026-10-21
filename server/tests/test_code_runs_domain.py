# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.

from app.domain.code_runs import code_hash, normalize_code


def test_line_endings_and_trailing_spaces_do_not_change_hash() -> None:
    unix = "def solve(nums, k):\n    return False\n"
    windows = "def solve(nums, k):   \r\n    return False\r\n\r\n"
    assert normalize_code(windows) == normalize_code(unix)
    assert code_hash(windows) == code_hash(unix)


def test_meaningful_change_changes_hash() -> None:
    assert code_hash("return 1") != code_hash("return 2")
    assert code_hash("  x = 1") != code_hash("x = 1")  # leading indentation is significant


def test_hash_is_sha256_hex() -> None:
    digest = code_hash("print(1)")
    assert len(digest) == 64
    int(digest, 16)
