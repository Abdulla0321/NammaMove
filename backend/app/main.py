from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .api import router as persistent_router
from .auth import TokenVerifier
from .config import Settings
from .database import Database
from .observability import RequestMiddleware, configure_logging, logger
from .simulator import router as simulator_router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    database = Database(config)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        yield
        database.dispose()

    configure_logging()
    application = FastAPI(
        title="NammaMove API",
        version="0.2.0",
        description="Persistent security APIs and separately labeled sample routing; no live transit integration",
        lifespan=lifespan,
    )
    application.state.settings = config
    application.state.database = database
    application.state.verifier = TokenVerifier(config)
    application.add_middleware(RequestMiddleware)
    application.include_router(simulator_router)
    application.include_router(persistent_router)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
        conflict = isinstance(error, IntegrityError)
        logger.warning(
            "database.conflict" if conflict else "database.unavailable",
            extra={"fields": {"request_id": getattr(request.state, "request_id", "unknown")}},
        )
        return JSONResponse(
            {
                "detail": "Record conflicts with stored data"
                if conflict
                else "Persistence unavailable"
            },
            status_code=409 if conflict else 503,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        # Never echo rejected values, JSON bodies or sensitive validation context.
        return JSONResponse(
            {
                "detail": "Invalid request",
                "errors": [{"location": list(e["loc"]), "type": e["type"]} for e in error.errors()],
            },
            status_code=422,
        )

    @application.get("/health/ready")
    def readiness() -> JSONResponse:
        if database.engine is None or config.issuer is None:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        try:
            with Session(database.engine) as session:
                revision = session.scalar(text("SELECT version_num FROM nammamove.alembic_version"))
                spatial = session.scalar(
                    text("SELECT extname FROM pg_extension WHERE extname='postgis'")
                )
                if revision != "0001_phase01" or spatial != "postgis":
                    return JSONResponse({"status": "unavailable"}, status_code=503)
            return JSONResponse({"status": "ready"})
        except SQLAlchemyError:
            return JSONResponse({"status": "unavailable"}, status_code=503)

    return application


app = create_app()
