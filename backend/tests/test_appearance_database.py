from sqlalchemy import JSON, DateTime, Uuid

from app.db.base import Base
from app.models import AppearanceProfile


def test_appearance_profile_metadata_contract() -> None:
    assert issubclass(AppearanceProfile, Base)
    assert "appearance_profiles" in Base.metadata.tables
    table = AppearanceProfile.__table__
    assert list(table.columns.keys()) == [
        "id",
        "user_id",
        "skin",
        "face",
        "eyes",
        "hair",
        "colour_analysis",
        "makeup",
        "evidence",
        "created_at",
        "updated_at",
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key
    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.user_id.unique
    for name in ("skin", "face", "eyes", "hair", "colour_analysis", "makeup", "evidence"):
        assert isinstance(table.c[name].type, JSON)
        assert table.c[name].nullable is False
    assert isinstance(table.c.created_at.type, DateTime)
    assert isinstance(table.c.updated_at.type, DateTime)


def test_appearance_profile_user_fk() -> None:
    foreign_keys = list(AppearanceProfile.__table__.c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].column.table.name == "users"
    assert foreign_keys[0].column.name == "id"
