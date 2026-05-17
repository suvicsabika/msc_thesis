"""FastAPI application factory and server entrypoint.

This module builds the MCP Ticket Analyzer API application, configures
CORS and logging, attaches API routes, and ensures the database schema is
ready before the app starts.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.db.init_db import create_db_and_tables
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare the application lifecycle by ensuring database tables exist.

    This function runs before the application starts handling requests and
    guarantees that the database schema is created.
    """

    create_db_and_tables()
    yield


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""

    app = FastAPI(
        title="MCP Ticket Analyzer API",
        description="FastAPI backend for the MCP-based customer support ticket analyzer.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    configure_logging()

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)