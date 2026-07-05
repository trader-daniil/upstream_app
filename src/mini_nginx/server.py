import asyncio
import logging
from dataclasses import dataclass
from itertools import cycle
from mini_nginx.upstream_pool import UpstreamPool
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("mini_nginx")

# Констануты таймаутов в wait_for
CONNECT_TIMEOUT = 5.0 # на установку соединения с upstream
READ_TIMEOUT = 30.0 # на каждый отдельный read
WRITE_TIMEOUT = 30.0 # на каждый drain
TOTAL_TIMEOUT = 60.0 # на весь запрос целиком с пересылкой к upstream и обратно клиенту

# Константы для ограничения соединений
MAX_CLIENTS = 100 # сколько клиентских соединений обслуживаем одновременно
MAX_UPSTREAM = 50 # сколько соединений к апстримам держим одновременно

client_sem = asyncio.Semaphore(MAX_CLIENTS) # лимит на клиентские соединения

pool = UpstreamPool(
    upstreams=[("127.0.0.1", 9001), ("127.0.0.1", 9002), ("127.0.0.1", 9003)],
    max_connections=MAX_UPSTREAM,
)


@dataclass
class RequestHead:
    method: str
    path: str
    version: str
    headers: list[tuple[str, str]]


def parse_request_head(data: bytes) -> RequestHead:
    """
    Парсит голову из  прочитанных байтов
    Ничего не вынимает из потока — только смотрит и раскладывает по полям.
    """
    head_bytes = data.split(b"\r\n\r\n", 1)[0]
    start_line, *header_lines = head_bytes.split(b"\r\n")

    method, path, version = start_line.split(b" ", 2)

    headers: list[tuple[str, str]] = []
    for line in header_lines:
        name, _, value = line.partition(b":")
        headers.append((name.strip().decode(), value.strip().decode()))

    return RequestHead(
        method=method.decode(),
        path=path.decode(),
        version=version.decode(),
        headers=headers,
    )


async def forward_request(client_reader, upstream_writer) -> None:
    """
    Пересылаем запрос клиента на upstream
    Перед отправкой данные нужно спасить и прологгировать.
    """
    buffer = bytearray()
    logged = False
    while True:
        data = await asyncio.wait_for(client_reader.read(4096), READ_TIMEOUT)
        if not data:
            break

        if not logged:
            buffer += data
            if b"\r\n\r\n" in buffer:
                head = parse_request_head(bytes(buffer))
                log.info("%s %s %s", head.method, head.path, head.version)
                logged = True

        upstream_writer.write(data)
        await asyncio.wait_for(upstream_writer.drain(), WRITE_TIMEOUT)


async def forward_response(upstream_reader, client_writer) -> None:
    """
    Пересылаем ответ upstream обратно клиенту
    Перед отправкой подсматриваем статус ответа и логируем его.
    """
    buffer = bytearray()
    logged = False
    while True:
        data = await asyncio.wait_for(upstream_reader.read(4096), READ_TIMEOUT)
        if not data:
            break

        if not logged:
            buffer += data
            if b"\r\n" in buffer:
                status_line = buffer.split(b"\r\n", 1)[0]
                parts = status_line.split(b" ", 2)
                if len(parts) > 1:

                    status = parts[1].decode()
                    log.info("status=%s", status)
                logged = True

        client_writer.write(data)
        await asyncio.wait_for(client_writer.drain(), WRITE_TIMEOUT)


async def handle(client_reader, client_writer) -> None:
    """
    Пересылаем нащ запрос на upstream, дожидаемся ответа и возвращаем ответ клиенту.
    """
    async with client_sem: # Задаем лимит клиентских подключений

        # Получаем следующий upstream(round robin)
        host, port = pool.next_upstream()
        log.info("Пересылка на upstream %s:%s", host, port)

        async with pool.limit(): # Лимит подключений к апстриму
            try:
                upstream_reader, upstream_writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    CONNECT_TIMEOUT,
                )
            except TimeoutError:
                log.warning("upstream connect timeout")
                client_writer.close()
                return

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        forward_request(client_reader, upstream_writer),
                        forward_response(upstream_reader, client_writer),
                    ),
                    TOTAL_TIMEOUT,
                )
            except TimeoutError:
                log.warning("proxy total timeout")
            finally:
                upstream_writer.close()
                client_writer.close()


async def main() -> None:
    server = await asyncio.start_server(handle, "127.0.0.1", 8888)
    async with server:
        await server.serve_forever()


asyncio.run(main())