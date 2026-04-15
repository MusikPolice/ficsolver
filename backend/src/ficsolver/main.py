from fastapi import FastAPI

app = FastAPI(title="ficsolver")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
