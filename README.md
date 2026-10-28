# AI Tech Interview

AI-тренажёр технических собеседований с автоматическим разбором кода. Диалог ведёт языковая модель, код кандидата выполняется в изолированном контейнере Docker, каждое замечание отчёта привязано к ответу или строке кода.

Проект закрытый, условия использования в файле `LICENSE`.

## Структура

| Каталог | Что внутри |
|---|---|
| `client/` | клиент Flutter для Web и Windows (Riverpod, go_router) |
| `server/` | серверный пакет на Python 3.12: AI-слой (`app/infrastructure/ai`), песочница (`app/infrastructure/sandbox`), доменные модели |
| `sandbox/` | `runner.py`, `Dockerfile.runner`, тесты, злой код и нагрузка |
| `docs/` | безопасность песочницы, тест-кейсы, план тестирования, эталонный набор, деплой |
| `.github/workflows/` | проверки сервера и песочницы, проверки клиента, деплой по тегу |

## Запуск сервера и песочницы

```bash
cd server
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

Тесты песочницы нужны Docker и образ:

```bash
docker build -f sandbox/Dockerfile.runner -t interview-sandbox:latest sandbox
server/.venv/bin/python -m pytest sandbox/tests -q
```

Переменные окружения AI-слоя и песочницы перечислены в `server/.env.example`. Без них работают заглушки: `LLM_PROVIDER=fake`, `SANDBOX_BACKEND=fake`.

## Запуск клиента

```bash
cd client
flutter pub get
flutter run -d chrome
flutter test
```

Данные клиента пока берутся из встроенных заглушек. Демо-аккаунты: `demo@interview.dev` / `demo123` и `admin@interview.dev` / `admin123`.

## Ветки

Работа идёт в ветках `feature/*`, слияние через pull request в `develop`. В `main` изменения попадают в конце проекта.
