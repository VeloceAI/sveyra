from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    email: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    style_profiles: Mapped[list["StyleProfile"]] = relationship(back_populates="user")
    body_profiles: Mapped[list["BodyProfile"]] = relationship(back_populates="user")
    wardrobe_items: Mapped[list["WardrobeItem"]] = relationship(back_populates="user")
    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="user")
    outfits: Mapped[list["Outfit"]] = relationship(back_populates="user")
