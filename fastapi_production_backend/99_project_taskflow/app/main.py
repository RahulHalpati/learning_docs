"""Application factory — wires config, middleware, routers, and handlers."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.observability.metrics import setup_metrics
from app.observability.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield
    # (dispose engines / close pools here if needed)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)      # request id + access log

    register_exception_handlers(app)
    setup_metrics(app)                                 # /metrics for Prometheus
    app.include_router(api_router)
    return app


app = create_app()
