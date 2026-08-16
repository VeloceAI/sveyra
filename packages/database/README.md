# Database Package

Owns Postgres schema, Alembic configuration, and migration history.

Application code should import database sessions through backend infrastructure, not from migration files.
