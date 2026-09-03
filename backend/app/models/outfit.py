from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class Outfit(Base):
    __tablename__ = "outfits"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("users.id"), nullable=False)
    occasion: Mapped[str] = mapped_column(Text(), nullable=False)
    item_ids: Mapped[list[object]] = mapped_column(
        JSON(),
        nullable=False,
        server_default="[]",
    )
    rationale: Mapped[dict[str, object]] = mapped_column(
        JSON(),
        nullable=False,
        server_default="{}",
    )
    user: Mapped[User] = relationship(back_populates="outfits")
