"""
Abstract Repository pattern - theo "Architecture Patterns with Python".
Repository chỉ trả về aggregate, không lộ chi tiết database.
Hỗ trợ async và cơ chế `seen` để UoW biết aggregate nào đã được load.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Set
from uuid import UUID

T = TypeVar("T")  # Aggregate root type
ID = TypeVar("ID", str, UUID, int)


class AbstractRepository(ABC, Generic[T, ID]):
    """
    Repository trừu tượng.
    Các lớp con cần override _add và _get.
    Public methods add(), get() tự động cập nhật `seen`.
    """

    def __init__(self):
        self.seen: Set[T] = (
            set()
        )  # Tập hợp các aggregate đã được load trong unit of work hiện tại

    @abstractmethod
    async def _add(self, entity: T) -> None:
        """Thực hiện thêm entity vào storage (override bởi subclass)."""
        raise NotImplementedError

    @abstractmethod
    async def _get(self, id: ID) -> Optional[T]:
        """Thực hiện truy vấn entity theo ID (override bởi subclass)."""
        raise NotImplementedError

    @abstractmethod
    async def _update(self, entity: T) -> None:
        """Thực hiện cập nhật entity trong storage (override bởi subclass)."""
        raise NotImplementedError

    @abstractmethod
    async def _delete(self, id: ID) -> None:
        """Thực hiện xóa entity theo ID (override bởi subclass)."""
        raise NotImplementedError

    @abstractmethod
    async def _list(self, skip: int = 0, limit: int = 100, **filters) -> List[T]:
        """Thực hiện liệt kê entity (override bởi subclass)."""
        raise NotImplementedError

    # --- Public methods (tự động ghi nhận seen) ---

    async def add(self, entity: T) -> None:
        """Thêm entity và đánh dấu là đã seen."""
        await self._add(entity)
        self.seen.add(entity)

    async def get(self, id: ID) -> Optional[T]:
        """Lấy entity, đánh dấu là seen nếu tìm thấy."""
        entity = await self._get(id)
        if entity:
            self.seen.add(entity)
        return entity

    async def update(self, entity: T) -> None:
        """Cập nhật entity và đánh dấu là seen (nếu chưa có)."""
        await self._update(entity)
        self.seen.add(entity)

    async def delete(self, id: ID) -> None:
        """Xóa entity. Lưu ý: không tự động xóa khỏi seen (để tránh lỗi tham chiếu)."""
        await self._delete(id)
        # Xóa khỏi seen nếu có (tuỳ chọn)
        self.seen = {e for e in self.seen if getattr(e, "id", None) != id}

    async def list(self, skip: int = 0, limit: int = 100, **filters) -> List[T]:
        """Liệt kê entity – không tự động thêm vào seen vì có thể rất nhiều."""
        return await self._list(skip, limit, **filters)


# =============================================================================
# Fake Repository dành cho unit test (dùng in-memory)
# =============================================================================


class FakeRepository(AbstractRepository[T, ID]):
    """
    Repository giả lưu trữ trong dict.
    Dùng cho unit test service layer.
    """

    def __init__(self):
        super().__init__()
        self._storage: dict[ID, T] = {}
        self._sequence = 0

    def _next_id(self) -> int:
        self._sequence += 1
        return self._sequence

    async def _add(self, entity: T) -> None:
        # Gán id nếu entity chưa có (giả sử entity có attribute 'id')
        if hasattr(entity, "id") and getattr(entity, "id") is None:
            setattr(entity, "id", self._next_id())
        entity_id = getattr(entity, "id")
        if entity_id is None:
            raise ValueError("Entity must have an 'id' attribute")
        self._storage[entity_id] = entity

    async def _get(self, id: ID) -> Optional[T]:
        return self._storage.get(id)

    async def _update(self, entity: T) -> None:
        entity_id = getattr(entity, "id")
        if entity_id not in self._storage:
            raise KeyError(f"Entity with id {entity_id} not found")
        self._storage[entity_id] = entity

    async def _delete(self, id: ID) -> None:
        if id in self._storage:
            del self._storage[id]

    async def _list(self, skip: int = 0, limit: int = 100, **filters) -> List[T]:
        results = list(self._storage.values())
        # Lọc theo filters (so sánh bằng)
        for attr, value in filters.items():
            results = [e for e in results if getattr(e, attr, None) == value]
        return results[skip : skip + limit]

    def clear(self) -> None:
        """Xoá toàn bộ dữ liệu (dùng trong teardown test)."""
        self._storage.clear()
        self.seen.clear()
        self._sequence = 0
