"""Alembic environment.

Wires Alembic to the app's SQLAlchemy metadata and database URL (from
``app.core.config`` so there is a single source of truth). The app's tables live
in a dedicated Postgres schema (``settings.db_schema``); we ensure it exists and
keep Alembic's own version table inside it, and enable ``include_schemas`` so
autogenerate compares the right schema.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.schema import CreateSchema

from alembic import context

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401  (import registers tables on Base.metadata)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit migration SQL without a live connection (rarely used here)."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        version_table_schema=settings.db_schema,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # The version table and all app tables live in this schema, so it must
        # exist before Alembic touches the database.
        connection.execute(CreateSchema(settings.db_schema, if_not_exists=True))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=settings.db_schema,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
