from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graph.customer_service.graph import close_async_graph
from routes.chat import router as chat_router
from routes.data import router as data_router
from routes.memory import router as memory_router
from routes.providers import router as providers_router
from routes.sessions import router as sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_async_graph()


app = FastAPI(title="React LangGraph Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(data_router)
app.include_router(memory_router)
app.include_router(providers_router)
app.include_router(sessions_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
