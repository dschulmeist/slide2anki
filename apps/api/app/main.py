"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import init_db
from app.routers import (
    auth,
    decks,
    documents,
    exports,
    health,
    jobs,
    markdown,
    projects,
    review,
)
from app.routers import (
    settings as settings_router,
)
from app.services.storage import init_storage
from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize services on startup and cleanup on shutdown."""
    # Startup
    await init_db()
    await init_storage()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="slide2anki API",
    description="API for converting lecture slides to Anki flashcards",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - allow all origins in dev/Codespaces, restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_allow_all else settings.cors_origins,
    allow_credentials=not settings.cors_allow_all,  # credentials require specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(markdown.router, prefix="/api/v1", tags=["markdown"])
app.include_router(decks.router, prefix="/api/v1", tags=["decks"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(review.router, prefix="/api/v1", tags=["review"])
app.include_router(exports.router, prefix="/api/v1", tags=["exports"])
app.include_router(settings_router.router, prefix="/api/v1", tags=["settings"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
