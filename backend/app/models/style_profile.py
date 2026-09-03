from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("users.id"), nullable=False)
    preferences: Mapped[dict[str, object]] = mapped_column(
        JSON(),
        nullable=False,
        server_default="{}",
    )
    dislikes: Mapped[dict[str, object]] = mapped_column(
        JSON(),
        nullable=False,
        server_default="{}",
    )
    budget: Mapped[dict[str, object]] = mapped_column(
        JSON(),
        nullable=False,
        server_default="{}",
    )
    user: Mapped[User] = relationship(back_populates="style_profiles")
