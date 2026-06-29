# О проекте

mini_nginx это  асинхронный HTTP reverse proxy на `asyncio`. Учебный проект:
принимает клиентские соединения, парсит HTTP-запрос, проксирует его на один из
апстримов по схеме round-robin и возвращает ответ клиенту.

## Возможности

- TCP-сервер на `asyncio.start_server` с логированием входящих соединений
- Парсер HTTP-запроса: стартовая строка (метод, путь, версия) + заголовки;
  тело передаётся как raw-стрим
- Двунаправленное проксирование с backpressure через `drain()`
- Round-robin балансировка по нескольким апстримам
- Таймауты на connect / read / write и общий total
- Лимиты одновременных соединений через `asyncio.Semaphore`
  (отдельно на клиентов и на коннекты к апстриму)
- Логирование: апстрим-хост, метод/путь, статус ответа

## Установка

```bash
poetry install
```

## Запуск

### 1. Поднять апстримы (echo-серверы на FastAPI)

В отдельных терминалах или в фоне — три апстрима на портах 9001–9003:

```bash
poetry run uvicorn mini_nginx.echo_app:app --host 127.0.0.1 --port 9001 --workers 1 &
poetry run uvicorn mini_nginx.echo_app:app --host 127.0.0.1 --port 9002 --workers 1 &
poetry run uvicorn mini_nginx.echo_app:app --host 127.0.0.1 --port 9003 --workers 1 &
```

Данные апстримы содержатся в константе UPSTREAMS в файле server.py

Остановить все апстримы:

```bash
pkill -f "uvicorn mini_nginx.echo_app"
```

### 2. Запустить прокси

```bash
poetry run python -m mini_nginx.server
```

Прокси слушает `127.0.0.1:8888`.

## Проверка

```bash
curl -v http://127.0.0.1:8888/
curl -v -X POST http://127.0.0.1:8888/echo -d 'hello world'
```

## Конфигурация

Параметры заданы константами в `server.py`:

| Константа | Назначение |
|-----------|------------|
| `CONNECT_TIMEOUT` | таймаут установки соединения с апстримом |
| `READ_TIMEOUT` | таймаут на отдельный read |
| `WRITE_TIMEOUT` | таймаут на drain |
| `TOTAL_TIMEOUT` | таймаут на всю пересылку |
| `MAX_CLIENTS` | лимит клиентских соединений |
| `MAX_UPSTREAM` | лимит коннектов к апстриму |
| `UPSTREAMS` | список апстримов для round-robin |