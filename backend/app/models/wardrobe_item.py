from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User

if TYPE_CHECKING:
    from app.models.media_asset import MediaAsset


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(Text(), nullable=False)
    color: Mapped[str] = mapped_column(Text(), nullable=False)
    brand: Mapped[str] = mapped_column(Text(), nullable=False)
    attributes: Mapped[dict[str, object]] = mapped_column(
        JSON(),
        nullable=False,
        server_default="{}",
    )
    user: Mapped[User] = relationship(back_populates="wardrobe_items")
    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="wardrobe_item")
