from dataclasses import dataclass

import yaml


@dataclass
class Config:
    host: str
    port: int
    upstreams: list[tuple[str, int]]
    connect_timeout: float # на установку соединения с upstream
    read_timeout: float # на каждый отдельный read
    write_timeout: float # на каждый drain
    total_timeout: float # на весь запрос целиком с пересылкой к upstream и обратно клиенту
    max_clients: int # сколько клиентских соединений обслуживаем одновременно
    max_upstream: int # сколько соединений к апстримам держим одновременно
    log_level: str


def load_config(path: str) -> Config:
    """Читает YAML файл и разбирает в Config."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    host, port = raw["listen"].split(":")

    upstreams = [(u["host"], u["port"]) for u in raw["upstreams"]]

    # таймауты храним в секундах
    timeouts = raw["timeouts"]
    limits = raw["limits"]

    return Config(
        host=host,
        port=int(port),
        upstreams=upstreams,
        connect_timeout=timeouts["connect_ms"] / 1000,
        read_timeout=timeouts["read_ms"] / 1000,
        write_timeout=timeouts["write_ms"] / 1000,
        total_timeout=timeouts["total_ms"] / 1000,
        max_clients=limits["max_client_conns"],
        max_upstream=limits["max_conns_per_upstream"],
        log_level=raw["logging"]["level"],
    )