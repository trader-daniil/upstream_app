import os
from fastapi import FastAPI, Request

app = FastAPI()

# имя апстрима из переменной окружения (задаём при запуске uvicorn)
UPSTREAM_NAME = os.getenv("UPSTREAM_NAME", "unknown")


@app.get("/")
async def root():
    """Простой ответ на GET / — проверка, что прокси вообще проксирует."""
    return {"message": "ok", "upstream": UPSTREAM_NAME}


@app.post("/echo")
async def echo(request: Request):
    """Принимает тело POST-запроса и возвращает его обратно."""
    body = await request.body()
    return {"echo": body.decode(errors="replace"), "upstream": UPSTREAM_NAME}