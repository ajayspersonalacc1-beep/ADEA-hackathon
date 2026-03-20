"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adea.api import monitoring, optimization, pipelines
from adea.app.config import settings
from adea.utils.logging import configure_logging


configure_logging()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["pipelines"])
app.include_router(pipelines.public_router, tags=["pipelines-public"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(optimization.router, prefix="/api/v1/optimization", tags=["optimization"])


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Simple service health check."""

    return {"status": "ok"}
