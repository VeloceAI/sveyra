from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.calendar_handler import (
    delete_wear_log,
    list_wear_logs,
    persist_wear_log,
    wardrobe_usage,
)
from app.models.user import User
from app.schemas.calendar_schema import (
    WardrobeUsageResponse,
    WearLogListResponse,
    WearLogPersistRequest,
    WearLogResponse,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])

DEFAULT_WINDOW_DAYS = 30


@router.post("", response_model=WearLogResponse)
def create_entry(
    payload: WearLogPersistRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WearLogResponse:
    return persist_wear_log(payload, session, user)


@router.get("", response_model=WearLogListResponse)
def list_entries(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WearLogListResponse:
    # Default to the month around today, which is what a calendar shows.
    today = date.today()
    resolved_start = start or today - timedelta(days=DEFAULT_WINDOW_DAYS)
    resolved_end = end or today + timedelta(days=DEFAULT_WINDOW_DAYS)
    return list_wear_logs(resolved_start, resolved_end, session, user)


@router.get("/usage", response_model=WardrobeUsageResponse)
def usage(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WardrobeUsageResponse:
    return wardrobe_usage(session, user)


@router.delete("/{worn_on}", status_code=204)
def delete_entry(
    worn_on: date,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    delete_wear_log(worn_on, session, user)
