import logging
from pathlib import Path

from yoyo import read_migrations
from yoyo import get_backend


MIGRATIONS_PATH = Path(__file__).parent.parent.parent / 'migrations'


def apply_migrations(db_path):
    connection_string = f'sqlite:///{db_path}'
    backend = get_backend(connection_string)
    migrations = read_migrations(str(MIGRATIONS_PATH))

    applied = False
    try:
        with backend.lock():
            # Apply any outstanding migrations
            backend.apply_migrations(backend.to_apply(migrations))
        applied = True
    finally:
        # Rollback all migrations
        if not applied:
            backend.rollback_migrations(backend.to_rollback(migrations))
