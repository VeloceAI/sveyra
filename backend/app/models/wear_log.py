from datetime import date, datetime
from uuid import UUID

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class WearLog(Base):
    """What a user wore, or plans to wear, on a given day.

    One entry per user per day. A calendar answers "what did I wear" and
    "what am I wearing on Thursday" with the same row, distinguished by
    `planned`, because the second becomes the first once the day arrives.
    """

    __tablename__ = "wear_logs"
    __table_args__ = (UniqueConstraint("user_id", "worn_on", name="uq_wear_logs_user_date"),)

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("users.id"), nullable=False)
    worn_on: Mapped[date] = mapped_column(Date(), nullable=False)
    outfit_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("outfits.id"), nullable=True
    )
    item_ids: Mapped[list[object]] = mapped_column(JSON(), nullable=False, server_default="[]")
    occasion: Mapped[str | None] = mapped_column(Text(), nullable=True)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    planned: Mapped[bool] = mapped_column(nullable=False, server_default="0")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    user: Mapped[User] = relationship(back_populates="wear_logs")
