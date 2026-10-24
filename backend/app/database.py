"""Lazy PostgreSQL connections; no implicit table creation or migrations at startup."""

from collections.abc import Iterator

from fastapi import HTTPException, Request
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .auth import Identity
from .config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine: Engine | None = None
        self.sessions: sessionmaker[Session] | None = None
        if settings.database_url:
            self.engine = create_engine(
                settings.database_url.get_secret_value(),
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
                pool_timeout=5,
                connect_args={
                    "connect_timeout": 5,
                    "options": "-c statement_timeout=5000 -c lock_timeout=3000",
                },
                hide_parameters=True,
            )
            self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def dispose(self) -> None:
        if self.engine:
            self.engine.dispose()


def get_session(request: Request, principal: Identity) -> Iterator[Session]:
    database: Database = request.app.state.database
    if database.sessions is None:
        raise HTTPException(503, "Persistence is not configured")
    with database.sessions() as session:
        try:
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                session.execute(
                    text(
                        "SELECT set_config('nammamove.user_id', :uid, true), set_config('nammamove.role', :role, true)"
                    ),
                    {"uid": str(principal.id), "role": principal.role},
                )
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
