# Юра: бэкенд интервью (API, БД, миграции)

> Сначала прочитай `00_ОБЩЕЕ_контекст_и_контракт.md`. Там контракт API, форматы JSON и переменные окружения, по ним и работаешь.
> Твоя зона: `server/app/api`, `server/app/infrastructure/db` (модели, репозитории), `server/alembic`, `server/tests`.
> Положить в репозиторий как `docs/sprint-s3/01_yura.md`: промпты ссылаются на этот путь.

## Что сделать за ночь

| # | Notion | Задача | Готово, когда |
|---|---|---|---|
| 0 | — | Заглушки всех эндпоинтов раздела 6 контракта (фейковые ответы, SSE через `FakeChatProvider`) | Егор может работать против стенда/локалки уже к 22:45 |
| 1 | S2-Y1 | Модели `interview_sessions`, `messages` + миграция Alembic | `alembic upgrade head` на чистой базе; частичный уникальный индекс «одна активная сессия» |
| 2 | S2-Y2 | `POST /interviews`, `POST /interviews/{id}/messages` (SSE), `POST /interviews/{id}/finish` | Ответ идёт потоком событиями `token` → `done`; ошибка AI → `event: error` |
| 3 | S2-Y3 | Идемпотентность по `clientMessageId` | Повтор запроса не создаёт второй ответ (тест) |
| 4 | S2-Y4 | `GET /interviews/{id}`, `GET /interviews/active`; хранение токенов и длительности | Переписка восстанавливается после перезагрузки |
| 5 | S3-Y2 | Выдача задачи в сессии (`code_task_id`) | Когда AI-слой говорит `assign_task`, сессия получает задачу и `done.taskAssigned` заполнен |
| 6 | (FR-16) | `POST /api/admin/import` для банка (темы, вопросы, задачи, тесты) + seed темы «Python: основы» и 10 вопросов | Задачи Дани и вопросы импортируются одной командой; на стенде есть данные для демо |

**Не твоё этой ночью:** запуски кода (`/runs`, таблица `code_runs`, очередь, фоновый обработчик, compose) делает Даня; песочница и весь AI/LLM-слой (промпты, провайдер, разбор кода) — Ангелина. В `finish` ты только вызываешь функцию Дани `cancel_runs_for_session(session_id)`. Пока её нет, оставь TODO.

## Порядок работы

1. Задача 0 к 22:45, чтобы разблокировать Егора: PR `feature/s3-api-stubs`.
2. Задачи 1 → 2 → 3 → 4 (интервью целиком).
3. Миграцию с `interview_sessions` и `messages` смержить **до 00:30**: Даня делает свою миграцию `code_runs` поверх неё (`down_revision` = твоя), чтобы не получилось двух голов Alembic.
4. Задачи 5 → 6.
5. В 03:00, когда AI-слой Ангелины окажется в main, подключить `interviewer_turn` / `decide_next_step` вместо фейка (контракт, раздел 7).

## Таблицы (точные поля)

```
interview_sessions: id uuid pk, user_id uuid fk users on delete cascade, topic_id int fk topics,
  level text check in (junior,middle,senior), status text check in (active,finished,abandoned) default active,
  code_task_id int fk code_tasks null, current_question_id int fk questions null, questions_asked int default 0,
  tokens_used int default 0, started_at timestamptz default now(), finished_at timestamptz null,
  last_activity_at timestamptz default now()
  UNIQUE (user_id) WHERE status = 'active'          -- ux_sessions_active
  INDEX (user_id, started_at desc, id desc)          -- ix_sessions_history

messages: id bigint identity pk, session_id uuid fk on delete cascade, role text check in (user,assistant,system),
  content text, question_id int null, client_message_id uuid null, reply_to_id bigint null,
  tokens_in int null, tokens_out int null, duration_ms int null, created_at timestamptz default now()
  UNIQUE (session_id, client_message_id)              -- ux_messages_idem
  INDEX (session_id, id)


(code_runs — у Дани, см. 02_danila.md)
```

---

## Промпты для агента

> Перед каждым промптом вставь блок «Общие правила для ИИ-агентов» из раздела 10 общего файла.

### Промпт 0: заглушки API (S3, разблокировать фронт)

```
Задача: сделать рабочие заглушки эндпоинтов интервью и запусков по контракту
docs/sprint-s3/00_contract.md, разделы 6.1 и 6.2, чтобы фронтенд мог интегрироваться
до готовности реальной логики.

Сделай:
1. Роутер app/api/interviews.py и app/api/runs.py с эндпоинтами:
   POST /api/interviews, GET /api/interviews/active, GET /api/interviews/{id},
   POST /api/interviews/{id}/messages (SSE), POST /api/interviews/{id}/finish,
   POST /api/interviews/{id}/runs, GET /api/runs/{id}.
2. Схемы Pydantic v2 в app/api/schemas/ с camelCase-алиасами (alias_generator=to_camel,
   populate_by_name=True), ровно с полями из контракта.
3. Хранилище пока в памяти (dict), с поддержкой авторизации через уже существующую
   зависимость текущего пользователя (найди её в проекте).
4. SSE: StreamingResponse(media_type="text/event-stream"), события
   "event: token\ndata: {...}\n\n" и финальное "event: done". Текст бери из
   FakeChatProvider (если его ещё нет — сделай минимальный в app/infrastructure/ai/fake.py:
   отдаёт фиксированный ответ кусками по 3–5 слов с задержкой 50 мс).
   Заголовки: Cache-Control: no-cache, X-Accel-Buffering: no (чтобы nginx не буферизовал).
5. GET /api/runs/{id}: первые 2 секунды после создания возвращай "running", потом "done"
   с фиксированным RunResult (2 из 3 тестов прошли) и CodeReview с line=1.
6. Эндпоинты должны быть видны в Swagger /docs.

Проверка: curl -N на /messages показывает события token по мере генерации; pytest-тест
на форму ответа POST /api/interviews.
```

### Промпт 1: модели и миграция (S2-Y1)

```
Задача: добавить SQLAlchemy 2.0 (async, DeclarativeBase, Mapped[...]) модели
InterviewSessionModel, MessageModel и одну миграцию Alembic (code_runs делает Даня отдельной
миграцией поверх твоей — не трогай её).
Точные поля, ограничения и индексы — в docs/sprint-s3/01_yura.md, раздел «Таблицы».
Обязательно:
- частичный уникальный индекс ux_sessions_active: UNIQUE (user_id) WHERE status='active'
  (postgresql_where в Index);
- UNIQUE (session_id, client_message_id) для идемпотентности;
- check-ограничения на enum-поля (текст + CheckConstraint, не PG ENUM — проще мигрировать).
Сгенерируй миграцию autogenerate, затем вручную проверь, что частичные индексы попали в неё.
Проверка: на чистой базе `alembic upgrade head` и `alembic downgrade -1` проходят;
pytest-тест: вторая активная сессия того же пользователя -> IntegrityError.
```

### Промпт 2: интервью с потоковым ответом (S2-Y2, S2-Y3, S2-Y4)

```
Задача: заменить заглушки интервью на реальную логику с БД.

Слои:
- app/domain/interview.py: класс InterviewSession (паттерн State): status, методы
  add_message(), assign_task(), finish(), abandon(); недопустимые переходы -> DomainError.
- app/infrastructure/db/repositories.py: SqlAlchemyInterviewRepository
  (get, get_active_for_user, add, add_message, find_message_by_client_id, list_messages).
- app/api/interviews.py: эндпоинты по контракту 6.1.

POST /api/interviews: проверить отсутствие активной сессии (иначе 409 active_session_exists),
создать сессию, выбрать первый вопрос из questions по topic_id+level (is_active, случайный
из не заданных), получить первую реплику интервьюера (пока через FakeChatProvider, позже
interviewer_turn из app/infrastructure/ai/interviewer.py — см. контракт, раздел 7),
сохранить её как message(role=assistant, question_id=...).

POST /messages (SSE):
1) если message с таким client_message_id уже есть и на него есть ответ (reply_to_id) —
   отдать сохранённый ответ одним token + done, ничего не создавая;
2) сохранить сообщение пользователя;
3) step = await decide_next_step(ctx, provider); если step == "next_question" — выбрать
   следующий вопрос из банка (та же тема и уровень, ещё не заданный) и передать его;
   стримить interviewer_turn(ctx, step, provider, next_question) клиенту, накапливая текст;
4) по завершении сохранить ответ ассистента с tokens_in/out и duration_ms, обновить
   last_activity_at, questions_asked, tokens_used; если шаг assign_task — назначить
   code_task_id (первая активная задача темы и уровня) и вернуть taskAssigned в done;
5) при исключении провайдера — event: error {code:"ai_unavailable", retryable:true},
   сообщение пользователя остаётся, повтор с тем же clientMessageId должен сработать.
Важно: стрим не должен держать транзакцию БД открытой всё время генерации — сохрани
сообщение пользователя и закоммить до начала стрима, ответ сохраняй отдельной транзакцией.

GET /api/interviews/{id} и /active — сессия, все сообщения по порядку, task.
POST /finish — status=finished, finished_at; затем вызвать cancel_runs_for_session(session_id)
из app/infrastructure/db/run_queue.py (это код Дани; если его ещё нет в main — оставь TODO и
не реализуй сам).
Чужая сессия -> 404 (не 403).

Тесты pytest (httpx.AsyncClient + FakeChatProvider): старт, ответ потоком, повтор с тем же
clientMessageId не создаёт второй ответ, 409 на вторую сессию, finish, 404 на чужую.
```

### Промпт 3: импорт банка и seed для демо (FR-16)

```
Задача: эндпоинт POST /api/admin/import (только role=admin) и seed-данные для демо.
Формат файла — JSON: {topics:[{code,title}], questions:[{topicCode, level, kind, text,
expectedAnswer}], tasks:[{topicCode, level, title, statement, entry, starterCode, tests,
limits, referenceSolution}]}. Формат tests — контракт 6.5. Импорт идемпотентный: повторный
импорт того же файла не создаёт дублей (ключ: topic.code; question — topic+text; task —
topic+title), всё в одной транзакции, в ответе — сколько создано/обновлено.
Если моделей questions/code_tasks в проекте ещё нет или в них не хватает полей
(entry, limits, reference_solution) — добавь отдельной миграцией.
Seed: content/seed/python_basics.json — тема «Python: основы» (code python_basics) и 10
теоретических вопросов (по 4 junior/middle, 2 senior) с expected_answer; задачи туда кладёт
Даня (content/tasks/python_basics.json) — импорт должен принимать оба файла.
Команда: python -m app.scripts.import_bank content/seed/python_basics.json content/tasks/python_basics.json
Тесты: импорт создаёт записи; повторный импорт ничего не дублирует; user -> 403.
```

### Промпт 4: подключение AI-слоя Ангелины (после её мержа)

```
Задача: заменить FakeChatProvider в интервью на реальный AI-слой.
Используй get_chat_provider() из app/infrastructure/ai (по LLM_PROVIDER), функции
decide_next_step(ctx, provider) и interviewer_turn(ctx, step, provider, next_question)
(сигнатуры — контракт, раздел 7). AIUnavailable -> event: error. Собери
InterviewContext из сессии: тема, уровень, текущий вопрос из банка (text, expected_answer),
последние сообщения, число заданных вопросов. Ничего не меняй в промптах — это зона Ангелины.
Проверь, что тесты с LLM_PROVIDER=fake по-прежнему зелёные.
```

## Чек-лист перед мержем

- [ ] `alembic upgrade head` на чистой базе
- [ ] `pytest` зелёный
- [ ] Эндпоинты видны в Swagger, поля в camelCase
- [ ] `curl -N` по `/messages` показывает поток, а не один кусок в конце (проверь и через nginx)
- [ ] Seed и задачи Дани импортированы на стенде
- [ ] В Notion: S2-Y1…Y4, S3-Y2 → «Проверить»; S2-Y5 → «Готово» (компонентная диаграмма уже в отчёте)
