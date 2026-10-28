# Развёртывание стенда

Стек из пяти сервисов: `postgres`, `api` (миграции, загрузка банка вопросов, uvicorn), `worker` (очередь запусков кода), `docker-socket-proxy` (единственный сервис с доступом к сокету Docker) и `web` (nginx: статический клиент Flutter и прокси `/api`). Снаружи опубликован только `web`.

## Локальный запуск

Команды из корня репозитория, нужен Docker.

```bash
cp deploy/.env.example deploy/.env        # заполнить пароли и LLM_*; для проверки без модели LLM_PROVIDER=fake
docker build -f sandbox/Dockerfile.runner -t interview-sandbox:latest sandbox
(cd client && flutter build web --release --dart-define=API_BASE_URL=/api)
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

Клиент открывается на `http://localhost:8080`. Вход демо-аккаунтом: токен доступа к API пока равен e-mail пользователя, роль администратора даёт токен из `ADMIN_TOKENS`.

Образ песочницы собирается отдельно: через docker-socket-proxy образы собирать и скачивать нельзя (`IMAGES=0`). Логи обработчика: `docker compose -f deploy/docker-compose.yml logs -f worker`.

Проверка: создать интервью `POST /api/interviews`, дойти до задачи, отправить код `POST /api/interviews/{id}/runs` и опрашивать `GET /api/runs/{id}`: статус доходит до `done`, а `docker ps -a` после запуска не содержит контейнеров песочницы.

Остановка `docker compose ... stop` отправляет обработчику SIGTERM: он перестаёт брать новые запуски и за 30 с доводит начатые.

## Выкладка по тегу

Тег `vX.Y.Z` запускает `.github/workflows/deploy.yml`: собираются и публикуются в GHCR образы `sandbox`, `server` и `web`, затем по SSH выполняется выкладка: образы скачиваются, `docker compose up -d --no-build`, проверяется `/api/openapi.json`. Если проверка не прошла, возвращается предыдущий тег из файла `.release`. Откат вручную: запустить workflow с нужным тегом.

На сервере один раз: Docker и Docker Compose, каталог `DEPLOY_PATH` с копией каталога `deploy/` и файлом `deploy/.env`. В секретах репозитория: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`.
