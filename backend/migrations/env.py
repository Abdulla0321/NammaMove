"""Read credentials from validated environment; never put URLs in alembic.ini."""

from alembic import context
from app.config import Settings
from app.models import Base
from app.transit import models as transit_models  # noqa: F401
from sqlalchemy import create_engine, pool

config = context.config
url = Settings().database_url
if url is None:
    raise RuntimeError("DATABASE_URL must be configured for migrations")


def include_name(name, type_, parent_names):
    return type_ != "schema" or name == "nammamove"


def include_object(obj, name, type_, reflected, compare_to):
    # Generated PostGIS column is maintained explicitly in reviewed migrations.
    return (
        not (type_ == "index" and name in {"ix_stops_location", "ix_gtfs_stops_location"})
        and not (type_ == "column" and name == "location")
        and not (type_ == "table" and name == "spatial_ref_sys")
    )


if context.is_offline_mode():
    context.configure(
        url=url.get_secret_value(),
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="nammamove",
        include_schemas=True,
    )
    with context.begin_transaction():
        context.execute("CREATE SCHEMA IF NOT EXISTS nammamove")
        context.run_migrations()
else:
    supplied = config.attributes.get("connection")

    def run(connection):
        # Keep private-schema reflection explicit even when the owner login is
        # named nammamove and PostgreSQL's $user search path selects that schema.
        connection.exec_driver_sql("SET search_path TO public")
        connection.dialect.default_schema_name = "public"
        # Commit schema bootstrap before Alembic creates its private version table.
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS nammamove")
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            version_table_schema="nammamove",
            include_schemas=True,
            include_object=include_object,
            include_name=include_name,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    if supplied is not None:
        run(supplied)
    else:
        engine = create_engine(
            url.get_secret_value(),
            poolclass=pool.NullPool,
            hide_parameters=True,
            connect_args={"connect_timeout": 5},
        )
        with engine.connect() as connection:
            run(connection)
        engine.dispose()
