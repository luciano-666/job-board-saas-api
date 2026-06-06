import abc
from typing import Generic, TypeVar, Any

# Định nghĩa TypeVar đại diện cho Domain Entity
T = TypeVar("T")


class AbstractRepository(abc.ABC, Generic[T]):
    """
    Abstract Base Class cho tất cả các Repositories trong hệ thống.
    Tuân thủ nguyên lý Dependency Inversion Principle (DIP).
    """

    def __init__(self) -> None:
        # Tập hợp chứa các entities được tác động trong phiên làm việc này,
        # phục vụ cho việc tracking và trigger Domain Events tại Unit of Work.
        self.seen: set[Any] = set()

    def add(self, entity: T) -> None:
        """Thêm một entity mới vào repository và đưa vào hàng đợi tracking."""
        self._add(entity)
        self.seen.add(entity)

    async def get(self, id_: Any) -> T | None:
        """Lấy một entity theo ID. Nếu tìm thấy, đưa vào hàng đợi tracking."""
        entity = await self._get(id_)
        if entity:
            self.seen.add(entity)
        return entity

    @abc.abstractmethod
    def _add(self, entity: T) -> None:
        """Hiện thực hóa logic thêm entity (bắt buộc override ở tầng adapter)."""
        raise NotImplementedError

    @abc.abstractmethod
    async def _get(self, id_: Any) -> T | None:
        """Hiện thực hóa logic truy vấn entity bất đồng bộ (bắt buộc override)."""
        raise NotImplementedError
