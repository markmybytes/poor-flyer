from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_engine():
    try:
        return current_app.extensions['migrate'].db.engine
    except (TypeError, AttributeError):
        return current_app.extensions['migrate'].db.get_engine()


def get_engine_url() -> str:
    return str(get_engine().url).replace('%', '%%')


def get_metadata():
    return current_app.extensions['migrate'].db.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_engine_url(),
        target_metadata=get_metadata(),
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()
    config_args = current_app.extensions['migrate'].configure_args

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **config_args,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
