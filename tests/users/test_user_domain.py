import pytest

from src.users.domain.model import User, UserRole
from src.users.domain import events


def fake_password_hash(plain_password: str) -> str:
    return f"bcrypt_{plain_password}"


def fake_password_verifier(plain_password: str, hashed_password: str) -> bool:
    return hashed_password == f"bcrypt_{plain_password}"


def test_user_registration():
    user = User.register(
        email="candidate@example.com",
        plain_password="candidate123",
        role=UserRole.candidate,
        password_hasher=fake_password_hash,
    )

    assert user.hashed_password == "bcrypt_candidate123"
    assert user.is_activated is True

    # Kiểm tra Domain Event được ghi nhận để phục vụ gửi email chào mừng sau này
    assert len(user.events) == 1
    assert isinstance(user.events[0], events.UserRegistered)
    assert user.events[0].email == "candidate@example.com"


def test_user_password_verification():
    """
    Luật nghiệp vụ: Domain Model tự chịu trách nhiệm xác thực mật khẩu của chính nó
    thông qua hàm verifier được inject từ Service Layer.
    """
    user = User(
        email="user@example.com",
        hashed_password=fake_password_hash("user123"),
        role=UserRole.candidate,
    )
    # Trường hợp nhập đúng mật khẩu
    assert user.verify_password("user123", verifier_fn=fake_password_verifier) is True
    # Trường hợp nhập sai mật khẩu
    assert (
        user.verify_password("wrongpassword", verifier_fn=fake_password_verifier)
        is False
    )


def test_admin_user_can_suspend_normal_user():
    """
    Luật nghiệp vụ: Chỉ có Admin mới có quyền suspend (khóa) tài khoản của user khác.
    Khi khóa thành công, trạng thái kích hoạt về False và phát ra sự kiện UserSuspended.
    """
    candidate = User(
        email="candidate@example.com",
        hashed_password=fake_password_hash("candidate123"),
        role=UserRole.candidate,
    )
    admin = User(
        email="admin@example.com",
        hashed_password=fake_password_hash("admin123"),
        role=UserRole.admin,
    )

    # Thực hiện hành vi hành động từ phía Admin
    admin.suspend(target_user=candidate)

    assert admin.is_superuser is True
    assert candidate.is_activated is False

    # Kiểm tra Domain Event để kích hoạt ngầm hạ toàn bộ bài đăng (nếu là Employer)
    assert len(candidate.events) == 1
    assert isinstance(candidate.events[0], events.UserSuspended)
    assert candidate.events[0].email == "candidate@example.com"


def test_non_admin_cannot_suspend_users():
    """
    Ràng buộc bất biến (Invariant): Người dùng thông thường không thể tự ý khóa tài khoản khác.
    """
    candidate_1 = User(
        email="c1@example.com", hashed_password="...", role=UserRole.candidate
    )
    candidate_2 = User(
        email="c2@example.com", hashed_password="...", role=UserRole.candidate
    )

    with pytest.raises(PermissionError, match="Only admin can suspend users"):
        candidate_1.suspend(target_user=candidate_2)


def test_suspended_user_cannot_verify_password():
    """
    Ràng buộc bất biến: Tài khoản đã bị khóa (is_activated=False)
    thì không được phép kiểm tra mật khẩu (chặn đăng nhập ngay từ core).
    """
    suspended_user = User(
        email="locked@example.com",
        hashed_password=fake_password_hash("password123"),
        role=UserRole.candidate,
    )
    suspended_user.is_activated = False  # Giả lập trạng thái đã bị khóa

    with pytest.raises(PermissionError, match="This account is suspended!"):
        suspended_user.verify_password(
            "password123", verifier_fn=fake_password_verifier
        )


def test_employer_registration_requires_admin_approval():
    """
    Luật nghiệp vụ: Khác với Candidate, Employer đăng ký xong sẽ ở trạng thái chờ duyệt.
    Chỉ khi Admin gọi hành động approve() thì mới được kích hoạt.
    """
    # Bạn có thể điều chỉnh lại logic hàm register() để xử lý role Employer
    employer = User.register(
        email="company@example.com",
        plain_password="employer123",
        role=UserRole.employer,
        password_hasher=fake_password_hash,
    )

    # Giả sử theo thiết kế của bạn: Employer mới tạo sẽ chưa được kích hoạt ngay
    assert employer.is_activated is False

    admin = User(email="admin@example.com", hashed_password="...", role=UserRole.admin)

    # Hành vi Admin duyệt tài khoản doanh nghiệp
    admin.approve(target_user=employer)

    assert employer.is_activated is True
    assert any(isinstance(e, events.UserApproved) for e in employer.events)


def test_user_can_change_password_and_triggers_event():
    """
    Luật nghiệp vụ: Khi đổi mật khẩu, mật khẩu mới phải được băm
    và phát sinh sự kiện PasswordChanged để hệ thống xóa JWT cũ trên Redis.
    """
    user = User(
        email="user@example.com",
        hashed_password=fake_password_hash("old_password"),
        role=UserRole.candidate,
    )
    user.events.clear()  # Xóa các event khởi tạo nếu có

    # Thực hiện đổi mật khẩu
    user.change_password(
        plain_new_password="new_password123", password_hasher=fake_password_hash
    )

    assert user.hashed_password == "bcrypt_new_password123"
    assert len(user.events) == 1
    assert isinstance(user.events[0], events.PasswordChanged)
    assert user.events[0].email == "user@example.com"


def test_cannot_register_with_invalid_email_or_weak_password():
    """
    Ràng buộc bất biến: Domain từ chối khởi tạo nếu dữ liệu vi phạm định dạng cơ bản.
    """
    with pytest.raises(ValueError, match="Email không hợp lệ"):
        User.register(
            email="invalid-email-format",
            plain_password="validPassword123",
            role=UserRole.candidate,
            password_hasher=fake_password_hash,
        )

    with pytest.raises(ValueError, match="Mật khẩu quá ngắn"):
        User.register(
            email="valid@example.com",
            plain_password="123",  # Quá ngắn
            role=UserRole.candidate,
            password_hasher=fake_password_hash,
        )


def test_employer_registration_starts_as_pending():
    """
    Luật nghiệp vụ: Employer đăng ký xong phải ở trạng thái PENDING (is_activated=False),
    khác với Candidate được kích hoạt ngay lập tức.
    Chỉ sau khi Admin gọi approve() thì mới chuyển sang ACTIVE.
    """
    employer = User.register(
        email="company@example.com",
        plain_password="employer123",
        role=UserRole.employer,
        password_hasher=fake_password_hash,
    )

    assert employer.is_activated is False

    # Event phát ra vẫn là UserRegistered, không phải UserApproved
    assert len(employer.events) == 1
    assert isinstance(employer.events[0], events.UserRegistered)
    assert employer.events[0].email == "company@example.com"

    # Sau khi Admin approve mới chuyển sang ACTIVE và phát UserApproved
    admin = User(
        email="admin@example.com",
        hashed_password=fake_password_hash("admin123"),
        role=UserRole.admin,
    )
    admin.approve(target_user=employer)

    assert employer.is_activated is True
    assert any(isinstance(e, events.UserApproved) for e in employer.events)


def test_non_admin_cannot_approve_users():
    """
    Ràng buộc bất biến: Đối xứng với suspend, chỉ Admin mới được phép
    phê duyệt tài khoản Employer. Mọi role khác đều bị từ chối.
    """
    employer = User(
        email="company@example.com",
        hashed_password=fake_password_hash("employer123"),
        role=UserRole.employer,
    )
    another_employer = User(
        email="other@example.com",
        hashed_password=fake_password_hash("other123"),
        role=UserRole.employer,
    )
    candidate = User(
        email="candidate@example.com",
        hashed_password=fake_password_hash("candidate123"),
        role=UserRole.candidate,
    )

    with pytest.raises(PermissionError, match="Only admin can approve users"):
        another_employer.approve(target_user=employer)

    with pytest.raises(PermissionError, match="Only admin can approve users"):
        candidate.approve(target_user=employer)


def test_suspended_user_cannot_change_password():
    """
    Ràng buộc bất biến: Tài khoản bị đình chỉ (is_activated=False) bị chặn
    toàn bộ hành vi tương tác — bao gồm cả đổi mật khẩu.
    Đảm bảo kẻ xấu không thể chiếm lại tài khoản sau khi bị Admin khóa.
    """
    suspended_user = User(
        email="locked@example.com",
        hashed_password=fake_password_hash("password123"),
        role=UserRole.candidate,
    )
    suspended_user.is_activated = False

    with pytest.raises(PermissionError, match="This account is suspended!"):
        suspended_user.change_password(
            plain_new_password="new_password123",
            password_hasher=fake_password_hash,
        )

    # Mật khẩu không được thay đổi
    assert suspended_user.hashed_password == fake_password_hash("password123")
    # Không có event nào được phát ra
    assert not any(isinstance(e, events.PasswordChanged) for e in suspended_user.events)
