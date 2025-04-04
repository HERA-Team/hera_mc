import json
import os.path as op
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# this will overwrite the init file sqlalchemy.url
# path with the path from ~/.hera_mc/mc_config.json
config_path = op.expanduser("~/.hera_mc/mc_config.json")
with open(config_path) as f:
    config_data = json.load(f)
db_name = config_data.get("default_db_name")
db_data = config_data.get("databases")
db_data = db_data.get(db_name)
db_url = db_data.get("url")
if "postgresql" in db_url and "postgresql+psycopg" not in db_url:
    db_url = db_url.replace("postgresql", "postgresql+psycopg")
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# for 'autogenerate' support
from hera_mc import mc  # noqa

target_metadata = mc.MCDeclarativeBase.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# Don't drop any tables.
# See https://alembic.sqlalchemy.org/en/latest/cookbook.html#don-t-generate-any-drop-table-directives-with-autogenerate
def include_object(object, name, type_, reflected, compare_to):  # noqa A002
    if type_ == "table" and reflected and compare_to is None:
        return False
    else:
        return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
