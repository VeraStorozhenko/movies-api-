from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.db import init_db
from app.logging import configure_logging
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.movies import router as movies_router
from fastapi.security import HTTPBearer

security = HTTPBearer()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.auto_create_schema:
        init_db()
        logger.info("Database schema initialized")
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True}
    )
    from fastapi.openapi.utils import get_openapi

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=settings.app_name,
            version="1.0.0",
            routes=app.routes,
        )
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
            }
        }
        openapi_schema["security"] = [{"BearerAuth": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(movies_router)
    return app
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(movies_router)
    return app


app = create_app()
