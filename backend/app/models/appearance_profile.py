from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class AppearanceProfile(Base):
    __tablename__ = "appearance_profiles"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
    )
    skin: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, server_default="{}")
    face: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, server_default="{}")
    eyes: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, server_default="{}")
    hair: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, server_default="{}")
    colour_analysis: Mapped[dict[str, object]] = mapped_column(
        JSON(),
        nullable=False,
        server_default="{}",
    )
    makeup: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, server_default="{}")
    evidence: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, server_default="{}")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    user: Mapped[User] = relationship(back_populates="appearance_profiles")
