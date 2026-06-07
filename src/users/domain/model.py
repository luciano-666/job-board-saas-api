import re
from enum import Enum
from typing import List, Callable
from src.users.domain.events import (
    DomainEvent,
    UserRegistered,
    UserSuspended,
    UserApproved,
    PasswordChanged,
)

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LENGTH = 8


class UserRole(str, Enum):
    admin = "admin"
    employer = "employer"
    candidate = "candidate"


class User:
    def __init__(
        self,
        email: str,
        hashed_password: str,
        role: UserRole,
        is_activated: bool = True,
    ):
        self.email = email
        self.hashed_password = hashed_password
        self.role = role
        self.is_activated = is_activated

        # Nơi lưu trữ các sự kiện nghiệp vụ phát sinh (DDD Pattern)
        self.events: List[DomainEvent] = []

    @property
    def is_superuser(self) -> bool:
        return self.role == UserRole.admin

    def _guard_suspended(self) -> None:
        if not self.is_activated:
            raise PermissionError("This account is suspended!")

    @classmethod
    def register(
        cls,
        email: str,
        plain_password: str,
        role: UserRole,
        password_hasher: Callable[[str], str],
    ) -> User:
        """Factory method tạo User mới và tự động ghi nhận sự kiện Đăng ký"""
        if not _EMAIL_REGEX.match(email):
            raise ValueError("Email không hợp lệ")
        if len(plain_password) < _MIN_PASSWORD_LENGTH:
            raise ValueError("Mật khẩu quá ngắn")

        hashed_password = password_hasher(plain_password)

        # Employer bắt đầu ở trạng thái PENDING, chờ Admin duyệt
        is_activated = role != UserRole.employer

        user = cls(
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_activated=is_activated,
        )
        user.events.append(UserRegistered(email=email, role=role.value))
        return user

    def verify_password(
        self, plain_password: str, verifier_fn: Callable[[str, str], bool]
    ) -> bool:
        """Kiểm tra mật khẩu bằng cách mượn hàm băm từ bên ngoài (DIP)"""
        self._guard_suspended()
        return verifier_fn(plain_password, self.hashed_password)

    def change_password(
        self, plain_new_password: str, password_hasher: Callable[[str], str]
    ) -> None:
        """Đổi mật khẩu — bị chặn nếu tài khoản đã bị đình chỉ."""
        self._guard_suspended()
        self.hashed_password = password_hasher(plain_new_password)
        self.events.append(PasswordChanged(email=self.email))

    def suspend(self, target_user: User) -> None:
        """Nghiệp vụ Admin thực hiện khóa tài khoản người dùng"""
        if not self.is_superuser:
            raise PermissionError("Only admin can suspend users.")
        target_user.is_activated = False
        target_user.events.append(
            UserSuspended(email=target_user.email, role=target_user.role.value)
        )

    def approve(self, target_user: User) -> None:
        """Admin phê duyệt tài khoản Employer đang ở trạng thái PENDING."""
        if not self.is_superuser:
            raise PermissionError("Only admin can approve users")
        target_user.is_activated = True
        target_user.events.append(
            UserApproved(email=target_user.email, role=target_user.role.value)
        )
