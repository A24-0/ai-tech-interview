# Развёртывание стенда

Команды выполняются из корня репозитория на сервере с Docker и Docker Compose.

1. Настройки:

   ```bash
   cp deploy/.env.example deploy/.env   # заполнить пароли, JWT_SECRET и LLM_*
   ```

2. Образ песочницы. Обработчик создаёт контейнеры только из готового образа: через
   docker-socket-proxy скачивать и собирать образы нельзя (`IMAGES=0`).

   ```bash
   docker build -f sandbox/Dockerfile.runner -t interview-sandbox sandbox
   ```

3. Запуск:

   ```bash
   docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
   docker compose -f deploy/docker-compose.yml logs -f worker   # JSON-логи: run_processed, run_requeued...
   ```

4. Проверка: создать запуск через API (`POST /api/interviews/{id}/runs`) и опрашивать
   `GET /api/runs/{id}`: статус доходит до `done`, а `docker ps -a` после запуска не содержит
   контейнеров песочницы.

Остановка `docker compose ... stop` отправляет обработчику SIGTERM: он перестаёт брать новые
запуски и за 30 с (`stop_grace_period`) доводит начатые.
