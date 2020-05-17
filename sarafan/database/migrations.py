import logging
from pathlib import Path

from yoyo import read_migrations
from yoyo import get_backend

from core_service.logging import ServiceLoggerAdapter


MIGRATIONS_PATH = Path(__file__).parent.parent.parent / 'migrations'


log = ServiceLoggerAdapter(logging.getLogger('sarafan.database.service'),
                           extra={'service': 'DatabaseService'})


class MigrationError(Exception):
    pass


def apply_migrations(db_path):
    connection_string = f'sqlite:///{db_path}'
    backend = get_backend(connection_string)
    migrations = read_migrations(str(MIGRATIONS_PATH))

    applied = False
    try:
        with backend.lock():
            # Apply any outstanding migrations
            to_apply = backend.to_apply(migrations)
            if to_apply:
                log.info("Applying migrations:\n%s",
                         pretty_migration_list(to_apply))
                backend.apply_migrations(to_apply)
                log.info("Migrations successfully applied.")
            else:
                log.info("All migrations already applied.")
        applied = True
    finally:
        # Rollback all migrations
        if not applied:
            rollback = backend.to_rollback(migrations)
            log.error("Error while applying migration. "
                      "Rolling back migrations:\n%s",
                      pretty_migration_list(rollback))
            backend.rollback_migrations(rollback)
            raise MigrationError()


def pretty_migration_list(migrations):
    return "\t * " + "\n\t * ".join([
        migration.id for migration in migrations
    ])
