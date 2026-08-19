from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.wardrobe_item import WardrobeItem


class WardrobeRepository:
    def get_user_by_id(self, session: Session, user_id: UUID) -> User | None:
        return session.get(User, user_id)

    def create_item(
        self,
        session: Session,
        user_id: UUID,
        category: str,
        color: str,
        brand: str,
        attributes: dict[str, object],
    ) -> WardrobeItem:
        item = WardrobeItem(
            id=uuid4(),
            user_id=user_id,
            category=category,
            color=color,
            brand=brand,
            attributes=attributes,
        )
        session.add(item)
        return item

    def get_item_by_id(self, session: Session, item_id: UUID) -> WardrobeItem | None:
        return session.get(WardrobeItem, item_id)

    def list_items_by_user_id(
        self,
        session: Session,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[WardrobeItem], int]:
        filters = WardrobeItem.user_id == user_id
        total = session.scalar(select(func.count()).select_from(WardrobeItem).where(filters)) or 0
        items = list(
            session.scalars(
                select(WardrobeItem).where(filters).offset(offset).limit(limit)
            ).all()
        )
        return items, total

    def list_all_items_by_user_id(
        self, session: Session, user_id: UUID
    ) -> list[WardrobeItem]:
        return list(
            session.scalars(select(WardrobeItem).where(WardrobeItem.user_id == user_id)).all()
        )

    def update_item_metadata(
        self,
        session: Session,
        item: WardrobeItem,
        *,
        category: str,
        color: str,
        attributes: dict[str, object],
    ) -> WardrobeItem:
        item.category = category
        item.color = color
        item.attributes = attributes
        session.add(item)
        return item

    def update_item_fields(
        self,
        session: Session,
        item: WardrobeItem,
        *,
        category: str | None = None,
        color: str | None = None,
        brand: str | None = None,
        attributes: dict[str, object] | None = None,
    ) -> WardrobeItem:
        if category is not None:
            item.category = category
        if color is not None:
            item.color = color
        if brand is not None:
            item.brand = brand
        if attributes is not None:
            item.attributes = attributes
        session.add(item)
        return item

    def delete_item(self, session: Session, item: WardrobeItem) -> None:
        session.delete(item)
