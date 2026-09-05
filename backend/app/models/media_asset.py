from uuid import UUID

from sqlalchemy import ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User
from app.models.wardrobe_item import WardrobeItem


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (UniqueConstraint("reference", name="uq_media_assets_reference"),)

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("users.id"), nullable=False)
    wardrobe_item_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("wardrobe_items.id"),
        nullable=True,
    )
    reference: Mapped[str] = mapped_column(Text(), nullable=False)
    user: Mapped[User] = relationship(back_populates="media_assets")
    wardrobe_item: Mapped[WardrobeItem | None] = relationship(back_populates="media_assets")
