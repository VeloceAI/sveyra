from inspect import isgeneratorfunction

from sqlalchemy import JSON, DateTime, Text, Uuid
from sqlalchemy.engine.url import make_url

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db, get_engine, get_session_factory
from app.models import BodyProfile, MediaAsset, Outfit, StyleProfile, User, WardrobeItem


def test_declarative_base_exists() -> None:
    assert issubclass(User, Base)
    assert issubclass(StyleProfile, Base)
    assert issubclass(BodyProfile, Base)
    assert issubclass(WardrobeItem, Base)
    assert issubclass(MediaAsset, Base)
    assert issubclass(Outfit, Base)


def test_metadata_contains_0001_tables() -> None:
    assert {"users", "style_profiles"}.issubset(Base.metadata.tables)


def test_metadata_contains_body_profiles() -> None:
    assert "body_profiles" in Base.metadata.tables


def test_users_columns_match_0001_and_0006() -> None:
    table = User.__table__
    assert list(table.columns.keys()) == ["id", "email", "password_hash", "created_at"]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key
    assert isinstance(table.c.email.type, Text)
    assert table.c.email.nullable is False
    assert table.c.email.unique is True
    assert isinstance(table.c.password_hash.type, Text)
    assert table.c.password_hash.nullable is False
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert table.c.created_at.nullable is True
    assert table.c.created_at.server_default is not None


def test_style_profiles_columns_match_0001() -> None:
    table = StyleProfile.__table__
    assert list(table.columns.keys()) == [
        "id",
        "user_id",
        "preferences",
        "dislikes",
        "budget",
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key
    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.user_id.nullable is False
    for name in ("preferences", "dislikes", "budget"):
        column = table.c[name]
        assert isinstance(column.type, JSON)
        assert column.nullable is False
        assert column.server_default is not None


def test_style_profiles_user_id_fk_points_to_users_id() -> None:
    foreign_keys = list(StyleProfile.__table__.c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    referenced = foreign_keys[0].column
    assert referenced.table.name == "users"
    assert referenced.name == "id"


def test_engine_uses_settings_database_url() -> None:
    engine = get_engine()
    assert engine.url == make_url(settings.database_url)


def test_session_dependency_is_a_closing_generator() -> None:
    assert isgeneratorfunction(get_db)
    factory = get_session_factory()
    assert factory.kw["bind"] is get_engine()


def test_body_profiles_columns_match_0002() -> None:
    table = BodyProfile.__table__
    assert list(table.columns.keys()) == [
        "id",
        "user_id",
        "measurements",
        "fit_preferences",
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key
    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.user_id.nullable is False
    for name in ("measurements", "fit_preferences"):
        column = table.c[name]
        assert isinstance(column.type, JSON)
        assert column.nullable is False
        assert column.server_default is not None


def test_body_profiles_user_id_fk_points_to_users_id() -> None:
    foreign_keys = list(BodyProfile.__table__.c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    referenced = foreign_keys[0].column
    assert referenced.table.name == "users"
    assert referenced.name == "id"


def test_metadata_contains_wardrobe_items() -> None:
    assert "wardrobe_items" in Base.metadata.tables


def test_wardrobe_items_columns_match_0003() -> None:
    table = WardrobeItem.__table__
    assert list(table.columns.keys()) == [
        "id",
        "user_id",
        "category",
        "color",
        "brand",
        "attributes",
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key
    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.user_id.nullable is False
    for name in ("category", "color", "brand"):
        assert isinstance(table.c[name].type, Text)
        assert table.c[name].nullable is False
    assert isinstance(table.c.attributes.type, JSON)
    assert table.c.attributes.nullable is False
    assert table.c.attributes.server_default is not None


def test_wardrobe_items_user_id_fk_points_to_users_id() -> None:
    foreign_keys = list(WardrobeItem.__table__.c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    referenced = foreign_keys[0].column
    assert referenced.table.name == "users"
    assert referenced.name == "id"


def test_metadata_contains_media_assets() -> None:
    assert "media_assets" in Base.metadata.tables


def test_media_assets_columns_match_0004() -> None:
    table = MediaAsset.__table__
    assert list(table.columns.keys()) == [
        "id",
        "user_id",
        "wardrobe_item_id",
        "reference",
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key
    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.user_id.nullable is False
    assert isinstance(table.c.wardrobe_item_id.type, Uuid)
    assert table.c.wardrobe_item_id.nullable is True
    assert isinstance(table.c.reference.type, Text)
    assert table.c.reference.nullable is False
    unique_references = [
        constraint
        for constraint in table.constraints
        if getattr(constraint, "columns", None)
        and list(constraint.columns.keys()) == ["reference"]
        and type(constraint).__name__ == "UniqueConstraint"
    ]
    assert len(unique_references) == 1
    assert unique_references[0].name == "uq_media_assets_reference"
    unique_item_ids = [
        constraint
        for constraint in table.constraints
        if getattr(constraint, "columns", None)
        and list(constraint.columns.keys()) == ["wardrobe_item_id"]
        and type(constraint).__name__ == "UniqueConstraint"
    ]
    assert unique_item_ids == []


def test_media_assets_fks() -> None:
    user_fks = list(MediaAsset.__table__.c.user_id.foreign_keys)
    assert len(user_fks) == 1
    assert user_fks[0].column.table.name == "users"
    assert user_fks[0].column.name == "id"
    item_fks = list(MediaAsset.__table__.c.wardrobe_item_id.foreign_keys)
    assert len(item_fks) == 1
    assert item_fks[0].column.table.name == "wardrobe_items"
    assert item_fks[0].column.name == "id"


def test_metadata_contains_outfits() -> None:
    assert "outfits" in Base.metadata.tables


def test_outfits_columns_match_0005() -> None:
    table = Outfit.__table__
    assert list(table.columns.keys()) == [
        "id",
        "user_id",
        "occasion",
        "item_ids",
        "rationale",
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key
    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.user_id.nullable is False
    assert isinstance(table.c.occasion.type, Text)
    assert table.c.occasion.nullable is False
    assert isinstance(table.c.item_ids.type, JSON)
    assert table.c.item_ids.nullable is False
    assert table.c.item_ids.server_default is not None
    assert isinstance(table.c.rationale.type, JSON)
    assert table.c.rationale.nullable is False
    assert table.c.rationale.server_default is not None


def test_outfits_user_id_fk_points_to_users_id() -> None:
    foreign_keys = list(Outfit.__table__.c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    referenced = foreign_keys[0].column
    assert referenced.table.name == "users"
    assert referenced.name == "id"
