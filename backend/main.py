from fastapi import FastAPI

app = FastAPI(title="React LangGraph Backend")


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
