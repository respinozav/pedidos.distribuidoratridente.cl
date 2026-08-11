from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Sistema de Pedidos Distribuidora Tridente API",
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*settings.cors_origin_list, "http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/api/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}