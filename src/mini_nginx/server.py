import asyncio
import logging
from mini_nginx.upstream_pool import UpstreamPool
from mini_nginx.utils.http_parser import parse_request_head
from mini_nginx.config_loader import load_config


cfg = load_config("config.yaml") # Загружаем настройки из файла конфигурации

client_sem = asyncio.Semaphore(cfg.max_clients) # лимит на клиентские соединения

logging.basicConfig(level=cfg.log_level.upper(), format="%(asctime)s %(message)s")
log = logging.getLogger("mini_nginx")

pool = UpstreamPool(
    upstreams=cfg.upstreams,
    max_connections=cfg.max_upstream,
)


async def forward_request(client_reader, upstream_writer) -> None:
    """
    Пересылаем запрос клиента на upstream
    Перед отправкой данные нужно спасить и прологгировать.
    """
    buffer = bytearray()
    logged = False
    while True:
        data = await asyncio.wait_for(client_reader.read(4096), cfg.read_timeout)
        if not data:
            break

        if not logged:
            buffer += data
            if b"\r\n\r\n" in buffer:
                head = parse_request_head(bytes(buffer))
                log.info("%s %s %s", head.method, head.path, head.version)
                logged = True

        upstream_writer.write(data)
        await asyncio.wait_for(upstream_writer.drain(), cfg.write_timeout)


async def forward_response(upstream_reader, client_writer) -> None:
    """
    Пересылаем ответ upstream обратно клиенту
    Перед отправкой подсматриваем статус ответа и логируем его.
    """
    buffer = bytearray()
    logged = False
    while True:
        data = await asyncio.wait_for(upstream_reader.read(4096), cfg.read_timeout)
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
        await asyncio.wait_for(client_writer.drain(), cfg.write_timeout)


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
                    cfg.connect_timeout,
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
                    cfg.total_timeout,
                )
            except TimeoutError:
                log.warning("proxy total timeout")
            finally:
                upstream_writer.close()
                client_writer.close()


async def main() -> None:
    server = await asyncio.start_server(handle, cfg.host, cfg.port)
    async with server:
        await server.serve_forever()


asyncio.run(main())