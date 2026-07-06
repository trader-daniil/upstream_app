from dataclasses import dataclass


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