from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.calendar_schema import (
    WardrobeUsageResponse,
    WearLogListResponse,
    WearLogPersistRequest,
    WearLogResponse,
)
from app.services.calendar_service import CalendarService


def persist_wear_log(
    payload: WearLogPersistRequest, session: Session, user: User
) -> WearLogResponse:
    return CalendarService().persist(session, user.id, payload)


def list_wear_logs(
    start: date, end: date, session: Session, user: User
) -> WearLogListResponse:
    return CalendarService().list_range(session, user.id, start, end)


def delete_wear_log(worn_on: date, session: Session, user: User) -> None:
    CalendarService().delete(session, user.id, worn_on)


def wardrobe_usage(session: Session, user: User) -> WardrobeUsageResponse:
    return CalendarService().usage(session, user.id)


def _unused(_: UUID) -> None:  # pragma: no cover
    return None
