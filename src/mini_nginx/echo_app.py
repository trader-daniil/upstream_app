from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def root():
    """Простой ответ на GET / — проверка, что прокси вообще проксирует."""
    return {"message": "ok"}


@app.post("/echo")
async def echo(request: Request):
    """Принимает тело POST-запроса и возвращает его обратно."""
    body = await request.body()
    return {"echo": body.decode(errors="replace")}