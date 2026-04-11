from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

load_dotenv()

from config.settings import DATABASE_URL, DB_PATH  # noqa: E402
from src.models import Base  # noqa: E402

# Alembic Config object
config = context.config

# Set the SQLAlchemy URL from the project's config (env-driven)
_url = DATABASE_URL or f"sqlite:///{DB_PATH}"
config.set_main_option("sqlalchemy.url", _url)

# Python logging from ini file (optional — only if [loggers]/[handlers]/[formatters]
# sections are present). alembic.ini intentionally omits them to keep config minimal,
# so we swallow the resulting KeyError rather than crash `alembic upgrade head`.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except KeyError:
        pass

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE support
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
