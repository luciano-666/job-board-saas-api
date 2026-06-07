import abc
from typing import Generator, Any


class AbstractUnitOfWork(abc.ABC):
    """
    Abstract Base Class quản lý Atomicity (Transactions) dưới dạng Async Context Manager.
    Kết nối chặt chẽ với Repository để tracking và dispatch Domain Events.
    """

    # Các module con sẽ định nghĩa các repositories cụ thể tại đây khi kế thừa.
    # Ví dụ: users: AbstractUserRepository

    async def __aenter__(self) -> "AbstractUnitOfWork":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Tự động rollback nếu xảy ra exception (lỗi) trong block `async with uow`.
        Nếu không có lỗi, lập trình viên phải chủ động gọi `await uow.commit()`.
        """
        if exc_type is not None:
            await self.rollback()
        else:
            # Ngăn chặn việc quên commit, tuy nhiên trong DDD,
            # việc tường minh gọi commit vẫn là best practice.
            pass

    async def commit(self) -> None:
        """Thực hiện commit transaction xuống database."""
        await self._commit()

    def collect_events(self) -> Generator[Any, None, None]:
        """
        Thu thập toàn bộ các Domain Events từ các Entity đã tương tác qua các Repositories.
        Hàm này sẽ được Message Bus gọi ngay sau khi commit thành công.
        """
        # Duyệt qua tất cả các repositories được định nghĩa trên UoW instance này
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            # Kiểm tra nếu thuộc tính đó là một Repository có chứa tập hợp `seen`
            if hasattr(attr, "seen"):
                for entity in attr.seen:
                    if hasattr(entity, "events"):
                        while entity.events:
                            yield entity.events.pop(0)

    @abc.abstractmethod
    async def _commit(self) -> None:
        """Hiện thực hóa logic commit bất đồng bộ của DB Driver."""
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        """Hiện thực hóa logic rollback khi có lỗi xảy ra."""
        raise NotImplementedError
