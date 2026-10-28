# Даня: бэкенд запусков кода и фоновый обработчик

> Сначала прочитай `00_ОБЩЕЕ_контекст_и_контракт.md`, особенно разделы 6.2 (эндпоинты `/runs`), 6.3 (RunResult), 7 (протоколы `Sandbox` и `review_code`: их реализует Ангелина, ты только вызываешь) и 8 (переменные окружения).
> Положить в репозиторий как `docs/sprint-s3/02_danila.md`.
> Твоя зона: таблица `code_runs` и её миграция, `server/app/api/runs.py`, `server/app/infrastructure/db/run_queue.py`, `server/app/worker/`, сервисы `worker` и `docker-socket-proxy` в `deploy/docker-compose.yml`, контент задач, `docs/tests/`, ТЗ.

## Что сделать за ночь

| # | Notion | Задача | Готово, когда |
|---|---|---|---|
| 1 | S3-Y1 | Таблица `code_runs` (миграция поверх миграции Юры), `POST /interviews/{id}/runs`, `GET /runs/{id}` | 202 + queued; повтор `clientRunId` без дубля; лимит → 429 |
| 2 | S3-D2 (очередь) | `PgCodeRunQueue` на `SKIP LOCKED` + цикл фонового обработчика: статусы, `attempts`, вызов `Sandbox.run` и `review_code` | Запуск доходит до `done` (сначала с `FakeSandbox`, после 03:00 с `DockerSandbox` Ангелины) |
| 3 | S3-Y3 | `cancel_runs_for_session`, `requeue_stale` (зависшие `running` → `queued`) | Тест: запуск, взятый больше 60 с назад, возвращается в очередь |
| 4 | S3-Y4 | `worker` и `docker-socket-proxy` в compose, лимиты в `.env` | `docker compose up` поднимает фоновый обработчик, запуски проходят на стенде |
| 5 | S3-D4 (½) | 5 задач с тестами (2 junior, 2 middle, 1 senior) + эталонные решения в JSON | Эталонное решение проходит все тесты через `runner.py` Ангелины |
| 6 | S2-A1 | Тест-кейсы интервью и запусков в `docs/tests/interview.md` | По ним утром делаем сквозной прогон |
| 7 | S2-D5 | Техническое задание (выжимка из раздела 1.3 отчёта) | `docs/artifacts/ТЗ.md` в репозитории |

**Не твоё этой ночью:** `runner.py`, образ песочницы, `DockerSandbox`, «злой код» и всё, что связано с LLM (промпты, провайдер, разбор кода), — это Ангелина. Ты пишешь против протоколов `Sandbox` и `review_code` из контракта. Эндпоинты интервью делает Юра.

## Порядок работы

1. 22:45–00:30: эндпоинты `/runs` (задача 1). Модели и запросы пиши сразу. Миграцию генерируй, **когда Юра смержит свою** (обещал до 00:30): `down_revision` = его ревизия, чтобы не было двух голов Alembic.
2. 00:30–03:00: очередь и цикл обработчика с `FakeSandbox` и `FakeChatProvider` (задача 2), затем задача 3.
3. В 03:00 Ангелина мержит `DockerSandbox` и `review_code`: переключаешься на них через `get_sandbox()` / `get_chat_provider()` и делаешь compose (задача 4).
4. В паузах: задачи с тестами (5), тест-кейсы (6), ТЗ (7). Задачи проверяй её `runner.py`: он появится раньше всего остального, примерно к 00:00.

## Таблица code_runs

```
code_runs: id uuid pk, session_id uuid fk interview_sessions on delete cascade, code_task_id int fk code_tasks,
  client_run_id uuid, code text, code_hash text,
  status text check in (queued,running,done,failed,cancelled) default queued,
  attempts int default 0, result jsonb null, ai_review jsonb null, error text null, locked_by text null,
  created_at timestamptz default now(), started_at timestamptz null, finished_at timestamptz null
  UNIQUE (session_id, client_run_id)
  INDEX (created_at) WHERE status = 'queued'          -- ix_runs_queue
  INDEX (started_at) WHERE status = 'running'         -- ix_runs_stale
  INDEX (session_id, code_task_id, code_hash)         -- ix_runs_dedupe
```

---

## Промпты для агента

> Перед каждым промптом вставь блок «Общие правила для ИИ-агентов» из раздела 10 общего файла.

### Промпт 1: эндпоинты запусков (S3-Y1)

```
Задача: таблица code_runs и эндпоинты запусков кода по контракту docs/sprint-s3/00_contract.md,
раздел 6.2. Поля и индексы таблицы — docs/sprint-s3/02_danila.md, раздел «Таблица code_runs».

1. Модель CodeRunModel (SQLAlchemy 2.0 async, Mapped[...]), миграция Alembic с
   down_revision = последняя ревизия в main (миграция Юры с interview_sessions/messages).
   Частичные индексы через Index(..., postgresql_where=...), проверь их в сгенерированном файле.
2. app/api/runs.py:
   POST /api/interviews/{id}/runs:
   - сессия не найдена или чужая -> 404; не active -> 409 session_not_active;
     code_task_id пуст -> 409 no_task;
   - code_hash = sha256(код с единой нормализацией переводов строк и обрезкой пробелов в конце);
   - идемпотентность по (session_id, client_run_id): вернуть существующий запуск;
   - лимит: число запусков по session_id+code_task_id >= RUNS_PER_TASK_LIMIT -> 429 runs_limit;
   - создать запись status=queued -> 202 {runId, status}.
   GET /api/runs/{id}: владелец через join на interview_sessions, иначе 404; форма из контракта,
   result и aiReview отдаются как есть из jsonb (camelCase).
3. Схемы Pydantic v2 с camelCase-алиасами. Если у Юры уже есть заглушки этих эндпоинтов —
   замени их, сохранив пути и формы ответа.
Тесты (pytest + httpx.AsyncClient): 202 + queued; повтор clientRunId; 429 на лимите;
409 без задачи; 404 на чужой запуск.
```

### Промпт 2: очередь и цикл фонового обработчика (S3-D2, S3-Y3)

```
Задача: очередь запусков и процесс фонового обработчика `python -m app.worker`.
Песочницу и разбор кода НЕ реализуй — вызывай протоколы из контракта (раздел 7):
get_sandbox() -> Sandbox.run(code, entry, tests, limits) -> RunResult (может бросить SandboxError),
review_code(task, code, result, provider) -> CodeReview | None, get_chat_provider().
Если этих модулей ещё нет в main — создай только минимальные FakeSandbox (фиксированный
RunResult: 2 из 3 тестов прошли, verdict "failed") и используй FakeChatProvider; реальные
реализации пишет Ангелина, не трогай её файлы.

1. app/infrastructure/db/run_queue.py — PgCodeRunQueue:
   dequeue(worker_id) одним запросом:
     UPDATE code_runs SET status='running', started_at=now(), attempts=attempts+1, locked_by=:w
     WHERE id = (SELECT id FROM code_runs WHERE status='queued' ORDER BY created_at
                 FOR UPDATE SKIP LOCKED LIMIT 1)
     RETURNING *;
   mark_done(id, result, ai_review), mark_failed(id, error), requeue(id),
   cancel_runs_for_session(session_id): queued/running -> cancelled (её вызывает finish Юры),
   requeue_stale(older_than=60s): running с started_at старше порога и attempts<3 -> queued,
   attempts>=3 -> failed (error='stale').
2. app/worker/__main__.py: asyncio-цикл, WORKER_CONCURRENCY заданий параллельно (Semaphore),
   опрос раз в WORKER_POLL_MS. Для задания: загрузить code_task (tests, entry, limits) ->
   перед запуском проверить, что статус не cancelled -> sandbox.run -> сохранить result ->
   review_code(...) -> сохранить ai_review -> status=done.
   Правила: ошибка/None от review_code НЕ делает запуск failed (result сохраняется,
   ai_review=null); SandboxError -> attempts<3 ? requeue : failed. Раз в 30 c — requeue_stale.
   Graceful shutdown по SIGTERM: не брать новые задания, дождаться текущих.
   Логи JSON: run_id, session_id, verdict, attempts, duration_ms.
Тесты: два конкурентных dequeue не отдают одно задание дважды (на реальном postgres из compose
или testcontainers); обработчик с FakeSandbox и FakeChatProvider доводит запуск до done;
cancel_runs_for_session и requeue_stale работают.
```

### Промпт 3: compose (S3-Y4)

```
Задача: добавить в deploy/docker-compose.yml сервисы worker и docker-socket-proxy.
- docker-socket-proxy: образ tecnativa/docker-socket-proxy, монтирует /var/run/docker.sock:ro,
  разрешены только CONTAINERS=1, POST=1, ALLOW_START=1, ALLOW_STOP=1; IMAGES=0, VOLUMES=0,
  NETWORKS=0, EXEC=0; только во внутренней сети backend, наружу не публикуется.
- worker: тот же образ, что и api, command: python -m app.worker; переменные из .env
  (DATABASE_URL, LLM_*, SANDBOX_*, WORKER_*, DOCKER_HOST=tcp://docker-socket-proxy:2375);
  depends_on postgres (healthy) и docker-socket-proxy; restart: unless-stopped;
  stop_grace_period: 30s.
- образ песочницы собирается из sandbox/Dockerfile.runner (его делает Ангелина): добавь
  шаг в README/Makefile: docker build -f sandbox/Dockerfile.runner -t interview-sandbox sandbox.
- обнови deploy/.env.example всеми ключами из контракта (раздел 8), без значений секретов.
Проверка: docker compose up -d; создать запуск через API -> статус доходит до done.
```

### Промпт 4: задачи с тестами (S3-D4, половина)

```
Задача: 5 практических задач на Python для банка (тема python_basics): 2 junior, 2 middle,
1 senior. Для каждой: title, statement (markdown, по-русски, с примером входа и выхода),
entry (имя функции), starterCode (сигнатура + pass), tests (5–8 тестов в формате контракта
6.5: args/expected, обязательно граничные случаи — пустой вход, один элемент, большие числа),
limits, referenceSolution.
Файл: content/tasks/python_basics.json в формате импорта Юры
({tasks:[{topicCode:"python_basics", level, title, statement, entry, starterCode, tests,
limits, referenceSolution}]}).
Скрипт scripts/verify_tasks.py: прогоняет referenceSolution каждой задачи через
sandbox/runner.py (subprocess, без Docker; формат stdin — контракт 6.5) и падает, если хоть
один тест красный. Запусти его.
Идеи: два числа с суммой k; проверка скобочной последовательности; группировка анаграмм;
слияние интервалов; LRU-кэш на dict (senior).
```

### Промпт 5: тест-кейсы (S2-A1)

```
Задача: docs/tests/interview.md — тест-кейсы таблицей (ID, предусловие, шаги, ожидаемый
результат) по контракту docs/sprint-s3/00_contract.md: старт интервью; вторая активная сессия
-> 409; ответ интервьюера потоком; повтор с тем же clientMessageId -> без дубля; обрыв сети
посреди ответа + «Повторить»; сбой провайдера (LLM_PROVIDER=fake с ошибкой) -> понятное
сообщение и «Повторить»; перезагрузка страницы -> переписка восстановлена; выдача задачи;
запуск верного решения -> passed; неверного -> failed с actual; SyntaxError -> error с номером
строки; while True -> timeout примерно за 5 с; лимит запусков -> 429; AI-разбор с номерами строк;
завершение интервью -> незавершённые запуски cancelled; чужая сессия или запуск -> 404.
Добавь колонку «Результат» (пустая) — заполним при утреннем прогоне.
```

### Промпт 6: ТЗ (S2-D5)

```
Задача: docs/artifacts/ТЗ.md — техническое задание по структуре ГОСТ 34.602 (кратко):
1) общие сведения; 2) назначение и цели; 3) характеристика объекта автоматизации;
4) требования к системе (18 функциональных и 12 нефункциональных); 5) состав и содержание
работ (этапы = спринты); 6) порядок контроля и приёмки; 7) требования к документированию.
Источник — раздел 1.3 итогового отчёта (текст ниже); формулировки не выдумывать, только
переструктурировать.
[ВСТАВИТЬ ТЕКСТ РАЗДЕЛА 1.3 ОТЧЁТА]
```

## Чек-лист перед мержем

- [ ] Одна голова Alembic (`alembic heads`), `upgrade head` на чистой базе проходит
- [ ] `pytest` зелёный
- [ ] Верное и неверное решения дают разные результаты на стенде, контейнеры не остаются (`docker ps -a`)
- [ ] `verify_tasks.py` проходит для всех 5 задач
- [ ] В Notion: S3-Y1, S3-Y3, S3-Y4, S2-A1, S2-D5 → «Проверить»; S3-D2 (очередь) → «Проверить»; S3-D4 → «В работе» (5 из 10); S2-D6 → «Готово» (ERD и последовательность уже в отчёте)
