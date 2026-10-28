# Деплой по тегу

Тег вида `vX.Y.Z` запускает workflow `deploy`: он собирает образы песочницы и сервера, пушит их в GHCR (`ghcr.io/<owner>/<repo>/sandbox:<тег>`, `.../server:<тег>`) и по SSH обновляет стенд.

```bash
git tag v0.3.0
git push origin v0.3.0
```

## Что нужно настроить один раз

Секреты репозитория (Settings, Secrets and variables, Actions):

| Секрет | Что |
|---|---|
| `DEPLOY_HOST` | адрес сервера |
| `DEPLOY_USER` | пользователь SSH |
| `DEPLOY_SSH_KEY` | приватный ключ этого пользователя |
| `DEPLOY_PATH` | каталог с `docker-compose.yml` на сервере |

В `docker-compose.yml` образы должны ссылаться на тег: `image: ghcr.io/<owner>/<repo>/server:${IMAGE_TAG}` и `SANDBOX_IMAGE=ghcr.io/<owner>/<repo>/sandbox:${IMAGE_TAG}`. Образ сервера собирается, только если в репозитории есть `server/Dockerfile`.

## Откат

Запустить workflow вручную (Actions, deploy, Run workflow) с предыдущим тегом, например `v0.2.0`. Он заново выкатит образы этого тега. Файл `.release` на сервере хранит тег, который выкачен сейчас.

## Не проверено

Workflow ещё ни разу не запускался: нужны секреты, сервер и compose-файл из зоны деплоя.
