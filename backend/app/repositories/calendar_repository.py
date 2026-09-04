from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.outfit import Outfit
from app.models.wardrobe_item import WardrobeItem
from app.models.wear_log import WearLog


class CalendarRepository:
    def get_by_date(self, session: Session, user_id: UUID, worn_on: date) -> WearLog | None:
        return session.scalars(
            select(WearLog).where(WearLog.user_id == user_id, WearLog.worn_on == worn_on)
        ).first()

    def list_between(
        self, session: Session, user_id: UUID, start: date, end: date
    ) -> list[WearLog]:
        return list(
            session.scalars(
                select(WearLog)
                .where(
                    WearLog.user_id == user_id,
                    WearLog.worn_on >= start,
                    WearLog.worn_on <= end,
                )
                .order_by(WearLog.worn_on)
            ).all()
        )

    def list_all(self, session: Session, user_id: UUID) -> list[WearLog]:
        return list(
            session.scalars(select(WearLog).where(WearLog.user_id == user_id)).all()
        )

    def create(
        self,
        session: Session,
        user_id: UUID,
        worn_on: date,
        outfit_id: UUID | None,
        item_ids: list[UUID],
        occasion: str | None,
        note: str | None,
        planned: bool,
    ) -> WearLog:
        entry = WearLog(
            id=uuid4(),
            user_id=user_id,
            worn_on=worn_on,
            outfit_id=outfit_id,
            item_ids=[str(i) for i in item_ids],
            occasion=occasion,
            note=note,
            planned=planned,
        )
        session.add(entry)
        return entry

    def delete(self, session: Session, entry: WearLog) -> None:
        session.delete(entry)

    def get_outfit(self, session: Session, outfit_id: UUID) -> Outfit | None:
        return session.get(Outfit, outfit_id)

    def owned_item_ids(self, session: Session, user_id: UUID) -> set[UUID]:
        return set(
            session.scalars(
                select(WardrobeItem.id).where(WardrobeItem.user_id == user_id)
            ).all()
        )
