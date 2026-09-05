import importlib.util
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "alembic"
    / "versions"
    / "0007_media_assets_reference_unique.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_0007", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_pre_0007_schema(connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL DEFAULT ''
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TABLE media_assets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                wardrobe_item_id TEXT,
                reference TEXT NOT NULL
            )
            """
        )
    )


def _insert_media_asset(connection, reference: str) -> None:
    user_id = str(uuid4())
    asset_id = str(uuid4())
    connection.execute(
        text(
            "INSERT INTO users (id, email, password_hash) "
            "VALUES (:id, :email, 'hash')"
        ),
        {"id": user_id, "email": f"{asset_id}@example.com"},
    )
    connection.execute(
        text(
            "INSERT INTO media_assets (id, user_id, wardrobe_item_id, reference) "
            "VALUES (:id, :user_id, NULL, :reference)"
        ),
        {"id": asset_id, "user_id": user_id, "reference": reference},
    )


def _media_asset_count(connection) -> int:
    return connection.execute(text("SELECT COUNT(*) FROM media_assets")).scalar_one()


def _duplicate_rows(connection, reference: str) -> list[tuple[str, str]]:
    rows = connection.execute(
        text(
            "SELECT id, reference FROM media_assets "
            "WHERE reference = :reference ORDER BY id"
        ),
        {"reference": reference},
    ).fetchall()
    return [(row.id, row.reference) for row in rows]


@pytest.fixture
def migration_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        _create_pre_0007_schema(connection)
    yield engine
    engine.dispose()


def test_find_duplicate_references_empty_when_all_unique(migration_engine) -> None:
    module = _load_migration_module()
    with migration_engine.begin() as connection:
        _insert_media_asset(connection, "ref-a")
        _insert_media_asset(connection, "ref-b")
        assert module._find_duplicate_references(connection) == []


def test_find_duplicate_references_detects_duplicates(migration_engine) -> None:
    module = _load_migration_module()
    with migration_engine.begin() as connection:
        _insert_media_asset(connection, "shared-ref")
        _insert_media_asset(connection, "shared-ref")
        assert module._find_duplicate_references(connection) == ["shared-ref"]


def test_upgrade_adds_constraint_when_no_duplicates(migration_engine) -> None:
    module = _load_migration_module()
    with migration_engine.begin() as connection:
        _insert_media_asset(connection, "ref-a")
        _insert_media_asset(connection, "ref-b")

    with migration_engine.connect() as connection:
        with patch("alembic.op.get_bind", return_value=connection):
            with patch("alembic.op.create_unique_constraint") as create_uc:
                module.upgrade()
                create_uc.assert_called_once_with(
                    "uq_media_assets_reference",
                    "media_assets",
                    ["reference"],
                )


def test_upgrade_detects_duplicate_references(migration_engine) -> None:
    module = _load_migration_module()
    duplicate_reference = "shared-ref"
    with migration_engine.begin() as connection:
        _insert_media_asset(connection, duplicate_reference)
        _insert_media_asset(connection, duplicate_reference)

    with migration_engine.connect() as connection:
        with patch("alembic.op.get_bind", return_value=connection):
            with patch("alembic.op.create_unique_constraint") as create_uc:
                with pytest.raises(RuntimeError, match="duplicate media_assets.reference"):
                    module.upgrade()
                create_uc.assert_not_called()


def test_upgrade_does_not_delete_duplicate_rows(migration_engine) -> None:
    module = _load_migration_module()
    duplicate_reference = "shared-ref"
    with migration_engine.begin() as connection:
        _insert_media_asset(connection, duplicate_reference)
        _insert_media_asset(connection, duplicate_reference)
        before = _duplicate_rows(connection, duplicate_reference)

    with migration_engine.connect() as connection:
        with patch("alembic.op.get_bind", return_value=connection):
            with pytest.raises(RuntimeError):
                module.upgrade()

    with migration_engine.connect() as connection:
        after = _duplicate_rows(connection, duplicate_reference)
        assert len(after) == 2
        assert after == before


def test_downgrade_removes_unique_constraint() -> None:
    module = _load_migration_module()
    with patch("alembic.op.drop_constraint") as drop_uc:
        module.downgrade()
        drop_uc.assert_called_once_with(
            "uq_media_assets_reference",
            "media_assets",
            type_="unique",
        )


def test_migration_chain_metadata() -> None:
    module = _load_migration_module()
    assert module.revision == "0007_media_assets_reference_unique"
    assert module.down_revision == "0006_user_password_hash"
