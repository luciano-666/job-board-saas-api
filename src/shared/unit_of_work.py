"""
Abstract Unit of Work pattern - theo "Architecture Patterns with Python".
Quản lý transaction và là nơi duy nhất để lấy repository.
Có khả năng thu thập các domain events từ các aggregate đã seen.
"""

from abc import ABC, abstractmethod

# from contextlib import asynccontextmanager
from typing import TypeVar, List  # ,Generic, Optional

from src.shared.repository import AbstractRepository  # ,T

T_co = TypeVar("T_co", covariant=True)


class AbstractUnitOfWork(ABC):
    """
    Đơn vị công việc trừu tượng.
    Các lớp con cung cấp các repository attributes (ví dụ: uow.products, uow.batches)
    và override _commit, _rollback, _close.
    """

    def __init__(self):
        # Các repository sẽ được gán trong subclass (ví dụ: self.products = SomeRepo())
        pass

    async def __aenter__(self):
        """Bắt đầu context, khởi tạo transaction."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Thoát context: rollback nếu có lỗi, commit nếu không."""
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()
        await self.close()

    @abstractmethod
    async def _commit(self) -> None:
        """Thực hiện commit thực tế (override bởi subclass)."""
        raise NotImplementedError

    @abstractmethod
    async def _rollback(self) -> None:
        """Thực hiện rollback thực tế (override bởi subclass)."""
        raise NotImplementedError

    @abstractmethod
    async def _close(self) -> None:
        """Giải phóng tài nguyên (đóng session, ...)."""
        raise NotImplementedError

    # --- Public methods ---

    async def commit(self) -> None:
        """Commit transaction và sau đó publish events từ các aggregate đã seen."""
        await self._commit()
        await self.publish_events()

    async def rollback(self) -> None:
        """Rollback transaction."""
        await self._rollback()

    async def close(self) -> None:
        """Đóng kết nối / session."""
        await self._close()

    async def collect_new_events(self) -> List[object]:
        """
        Thu thập tất cả domain events từ các aggregate đã seen,
        đồng thời xoá chúng khỏi aggregate để tránh publish lại.
        Được gọi bởi message bus sau mỗi handler.
        """
        events = []
        # Duyệt qua tất cả repository hiện có trong UoW
        for repo in self._get_all_repositories():
            for aggregate in repo.seen:
                while hasattr(aggregate, "events") and aggregate.events:
                    events.append(aggregate.events.pop(0))
        return events

    async def publish_events(self) -> None:
        """
        Gửi events đến message bus ngay lập tức (thường dùng trong commit).
        Nếu bạn muốn message bus xử lý events một cách đồng bộ, hãy gọi handle ở đây.
        Tuy nhiên, theo sách, message bus sẽ tự gọi collect_new_events, nên publish_events
        có thể để trống hoặc chỉ đánh dấu.
        """
        # Trong triển khai đơn giản, không làm gì cả.
        # Message bus sẽ tự gọi collect_new_events.
        pass

    def _get_all_repositories(self) -> List[AbstractRepository]:
        """Lấy tất cả repository attributes của UoW (dùng introspection)."""
        repos = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, AbstractRepository):
                repos.append(attr)
        return repos


# =============================================================================
# Fake Unit of Work dành cho unit test
# =============================================================================


class FakeUnitOfWork(AbstractUnitOfWork):
    """
    UoW giả dùng in-memory, không có database thật.
    Có thể gán các fake repository vào các attribute.
    """

    def __init__(self, **repositories):
        super().__init__()
        for name, repo in repositories.items():
            setattr(self, name, repo)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def _commit(self) -> None:
        self.committed = True

    async def _rollback(self) -> None:
        self.rolled_back = True

    async def _close(self) -> None:
        self.closed = True

    # Hỗ trợ truy cập repository qua tên (nếu chưa có attribute)
    def __getattr__(self, name):
        # Nếu không tìm thấy attribute, trả về None (hoặc có thể raise)
        return None


# =============================================================================
# Factory function để tạo nhanh FakeUnitOfWork với các fake repository
# =============================================================================


def create_fake_uow(repo_mapping: dict[str, AbstractRepository]) -> FakeUnitOfWork:
    """
    Tạo FakeUnitOfWork và gán các repository đã cho.
    Ví dụ:
        uow = create_fake_uow({"products": FakeProductRepository(), "jobs": FakeJobRepository()})
    """
    return FakeUnitOfWork(**repo_mapping)
