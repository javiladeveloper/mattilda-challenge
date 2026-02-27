from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html

from src.config import settings
from src.api.routes import router as api_router
from src.api.middlewares import RequestLoggingMiddleware
from src.infrastructure.logging import setup_logging, get_logger

# Setup structured logging
setup_logging()
logger = get_logger("main")

app = FastAPI(
    title=settings.project_name,
    version=settings.project_version,
    description="Backend system for school billing management",
    docs_url="/docs",
    redoc_url=None,  # Disable default, use custom
    openapi_url="/openapi.json",
)


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{settings.project_name} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
    )


# Middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
async def startup_event():
    logger.info("application_startup", version=settings.project_version)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_shutdown")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "version": settings.project_version,
        "service": "mattilda-api",
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Mattilda Backend API",
        "docs": "/docs",
        "health": "/health",
        "version": settings.project_version,
    }
