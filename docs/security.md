# Безопасность песочницы

Код кандидата запускается в одноразовом контейнере `interview-sandbox` (ADR-002). Параметры контейнера задаёт `DockerSandbox`: без сети, 256 МБ памяти без swap, 1 CPU, 64 процесса, корневая файловая система только для чтения, `/tmp` в памяти (16 МБ), `cap_drop ALL`, `no-new-privileges`, пользователь 65534, пустое окружение.

Проверки автоматизированы в `sandbox/tests/evil/` (нужны Docker и образ):

```bash
docker build -f sandbox/Dockerfile.runner -t interview-sandbox:latest sandbox
server/.venv/bin/python -m pytest sandbox/tests/evil -q
```

| Проверка | Как проверяли | Результат |
|---|---|---|
| Время | `while True`, тест `test_infinite_loop_times_out` | Локально 25.10: `timeout`, не дольше 7 с. На стенде не проверено |
| Память | `bytearray(1 ГБ)`, `test_one_gigabyte_allocation_does_not_kill_the_host` | Локально 25.10: запуск не `passed`, хост цел. На стенде не проверено |
| Процессы | `os.fork()` в цикле, `test_fork_bomb_is_stopped_by_pids_limit` | Локально 25.10: остановлено лимитом процессов. На стенде не проверено |
| Сеть | `urllib.request.urlopen` наружу, `test_network_request_fails_without_network` | Локально 25.10: запуск не `passed`, сети нет. На стенде не проверено |
| Файловая система: запись | `open('/pwned', 'w')`, `test_cannot_write_to_root_filesystem` | Локально 25.10: `Read-only file system` |
| Файловая система: `/tmp` | запись 64 МБ в `/tmp`, `test_tmp_is_writable_but_limited_in_size` | Локально 25.10: запуск не `passed`, лимит 16 МБ |
| Файловая система: чтение | `open('/etc/shadow')`, `test_etc_shadow_is_not_readable` | Локально 25.10: `Permission denied`, процесс идёт от пользователя 65534 |
| Вывод | `print` 10 МБ, `test_ten_megabytes_of_output_is_truncated` | Локально 25.10: `truncated`, stdout не больше `maxOutputBytes` |
| Секреты | `LLM_API_KEY` и `DATABASE_URL` заданы у процесса сервера, внутри контейнера их нет, `test_host_secrets_are_not_visible_inside` | Локально 25.10: переменных в контейнере нет |
| Контейнер удалён | после каждого сценария нет контейнеров с меткой `ai-tech-interview.sandbox` | Локально 25.10: 0 контейнеров |
| `docker-socket-proxy` не даёт exec и работу с образами | настройки прокси в `deploy/` | Не проверено, нужен стенд |

## Известные ограничения

- Код пользователя работает в одном процессе с драйвером теста, поэтому может подделать результат своего теста. Вердикт всего запуска подделать нельзя: nonce знает только `runner.py`.
- `SubprocessSandbox` не изолирует сеть и файловую систему и нужен только для разработки без Docker. В продакшене `SANDBOX_BACKEND=docker`.
- `docker-socket-proxy` должен разрешать `POST /containers/*/attach`, иначе stdin в контейнер не передастся.
