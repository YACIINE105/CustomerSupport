from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import get_settings
from src.core.database import engine
from src.core.exceptions import ApplicationError
from src.routes.base import base_router
from src.routes.router import api_router
from src.utils.logger import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    try:
        yield
    finally:
        await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)


@app.exception_handler(ApplicationError)
async def application_error_handler(_, exc: ApplicationError):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


app.include_router(base_router)
app.include_router(api_router, prefix="/api/v1")
