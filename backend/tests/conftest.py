from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.rate_limit import reset_auth_rate_limiter
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import BodyProfile, MediaAsset, Outfit, StyleProfile, User, WardrobeItem

assert User.__tablename__ == "users"
assert StyleProfile.__tablename__ == "style_profiles"
assert BodyProfile.__tablename__ == "body_profiles"
assert WardrobeItem.__tablename__ == "wardrobe_items"
assert MediaAsset.__tablename__ == "media_assets"
assert Outfit.__tablename__ == "outfits"


@pytest.fixture
def sqlite_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_auth_rate_limits() -> Generator[None, None, None]:
    reset_auth_rate_limiter()
    yield
    reset_auth_rate_limiter()


@pytest.fixture
def client(sqlite_engine: Engine) -> Generator[TestClient, None, None]:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_get_db() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
