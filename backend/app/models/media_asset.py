from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User
from app.models.wardrobe_item import WardrobeItem


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("users.id"), nullable=False)
    wardrobe_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("wardrobe_items.id"),
        nullable=True,
    )
    # Unique: a storage object belongs to exactly one asset row, so a second
    # user cannot claim a reference they do not own.
    reference: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    user: Mapped[User] = relationship(back_populates="media_assets")
    wardrobe_item: Mapped[WardrobeItem | None] = relationship(back_populates="media_assets")
