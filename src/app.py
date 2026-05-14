import os
from fastapi import FastAPI
import uvicorn

app = FastAPI()


def add(a: int, b: int) -> int:
    return a + b


@app.get("/")
def read_root():
    return {"status": "OK", "message": "FastAPI service is running"}


@app.get("/add")
def add_endpoint(a: int = 0, b: int = 0):
    return {"result": add(a, b)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("src.app:app", host=host, port=port, reload=False)
