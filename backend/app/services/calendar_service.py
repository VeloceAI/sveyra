from collections import Counter
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import (
    OutfitNotFoundError,
    WardrobeItemNotFoundError,
    WearLogNotFoundError,
)
from app.models.wear_log import WearLog
from app.repositories.calendar_repository import CalendarRepository
from app.schemas.calendar_schema import (
    WardrobeUsageResponse,
    WearLogListResponse,
    WearLogPersistRequest,
    WearLogResponse,
    WornItemStat,
)

MOST_WORN_LIMIT = 10


class CalendarService:
    def __init__(self, repository: CalendarRepository | None = None) -> None:
        self.repository = repository or CalendarRepository()

    def persist(
        self, session: Session, user_id: UUID, payload: WearLogPersistRequest
    ) -> WearLogResponse:
        """Record what was worn on a day, replacing any existing entry.

        Upsert rather than insert: a calendar cell holds one outfit, and
        changing your mind about Thursday should not need a delete first.
        """
        if payload.outfit_id is not None:
            outfit = self.repository.get_outfit(session, payload.outfit_id)
            if outfit is None or outfit.user_id != user_id:
                raise OutfitNotFoundError
        if payload.item_ids:
            owned = self.repository.owned_item_ids(session, user_id)
            if not set(payload.item_ids) <= owned:
                raise WardrobeItemNotFoundError

        existing = self.repository.get_by_date(session, user_id, payload.worn_on)
        if existing is not None:
            self.repository.delete(session, existing)
            session.flush()

        entry = self.repository.create(
            session,
            user_id,
            payload.worn_on,
            payload.outfit_id,
            payload.item_ids,
            payload.occasion,
            payload.note,
            payload.planned,
        )
        session.commit()
        session.refresh(entry)
        return self._to_response(entry)

    def list_range(
        self, session: Session, user_id: UUID, start: date, end: date
    ) -> WearLogListResponse:
        if end < start:
            raise ValueError("end must not precede start")
        entries = self.repository.list_between(session, user_id, start, end)
        return WearLogListResponse(
            entries=[self._to_response(e) for e in entries],
            start=start,
            end=end,
            total=len(entries),
        )

    def delete(self, session: Session, user_id: UUID, worn_on: date) -> None:
        entry = self.repository.get_by_date(session, user_id, worn_on)
        if entry is None:
            raise WearLogNotFoundError
        self.repository.delete(session, entry)
        session.commit()

    def usage(self, session: Session, user_id: UUID) -> WardrobeUsageResponse:
        """What actually gets worn, and what never does.

        The second list is the point: a wardrobe's dead weight is invisible
        until something counts it.
        """
        entries = self.repository.list_all(session, user_id)
        counter: Counter[str] = Counter()
        for entry in entries:
            for raw in entry.item_ids or []:
                counter[str(raw)] += 1

        owned = self.repository.owned_item_ids(session, user_id)
        worn = {UUID(k) for k in counter}
        return WardrobeUsageResponse(
            most_worn=[
                WornItemStat(item_id=UUID(item), times_worn=count)
                for item, count in counter.most_common(MOST_WORN_LIMIT)
            ],
            never_worn_item_ids=sorted(owned - worn, key=str),
            logged_days=len(entries),
        )

    def _to_response(self, entry: WearLog) -> WearLogResponse:
        return WearLogResponse(
            id=entry.id,
            user_id=entry.user_id,
            worn_on=entry.worn_on,
            outfit_id=entry.outfit_id,
            item_ids=[UUID(str(i)) for i in (entry.item_ids or [])],
            occasion=entry.occasion,
            note=entry.note,
            planned=bool(entry.planned),
        )
