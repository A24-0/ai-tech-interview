# Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
# Proprietary and confidential. See LICENSE in the project root.
"""Imports bank files into DATABASE_URL in one transaction (FR-16).

    python -m app.scripts.import_bank content/seed/python_basics.json content/tasks/python_basics.json

Files are merged in the given order, so tasks of one file may use topics of another.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.domain.bank import Bank, ImportResult, UnknownTopicError
from app.infrastructure.db.bank_import import import_bank
from app.infrastructure.db.session import make_engine, make_session_factory


def load(paths: list[Path]) -> Bank:
    bank = Bank()
    for path in paths:
        bank = bank.merged(Bank.model_validate(json.loads(path.read_text(encoding="utf-8"))))
    return bank


async def run(paths: list[Path], url: str | None = None) -> ImportResult:
    engine = make_engine(url)
    try:
        async with make_session_factory(engine)() as db, db.begin():
            return await import_bank(db, load(paths))
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import topics, questions and tasks into the database.")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # Russian output on a Windows console with a legacy code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        result = asyncio.run(run(args.files))
    except UnknownTopicError as exc:
        print(f"Тема {exc.code!r} не найдена ни в базе, ни в файлах", file=sys.stderr)
        return 1
    for name, counts in (("темы", result.topics), ("вопросы", result.questions), ("задачи", result.tasks)):
        print(f"{name}: создано {counts.created}, обновлено {counts.updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
