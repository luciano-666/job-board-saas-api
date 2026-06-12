import pytest
from uuid import UUID, uuid4

from src.users.domain.model import User, UserRole
from src.users.domain import events
from src.shared.service_layer.unit_of_work import AbstractUnitOfWork, IntegrityConflict
from src.users.service_layer import services
from src.users.domain.commands import (
    RegisterUser,
    LoginUser,
    ChangePassword,
    SuspendUser,
    ApproveEmployer,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeUserRepository:
    """Store user aggregates in memory for application tests."""

    def __init__(self, users: list[User] | None = None):
        self.users: list[User] = users or []
        self.seen: list[User] = []

    def add(self, user: User) -> None:
        """Add a user."""
        self.users.append(user)
        self.seen.append(user)

    def get(self, user_id: UUID) -> User | None:
        """Return a user by identity."""
        user = next((u for u in self.users if u.id == user_id), None)
        if user:
            self.seen.append(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        """Return a user by normalized email."""
        user = next((u for u in self.users if u.email == email.strip().lower()), None)
        if user:
            self.seen.append(user)
        return user


class FakeUnitOfWork(AbstractUnitOfWork):
    """Provide an in-memory transaction boundary."""

    def __init__(
        self,
        users: list[User] | None = None,
        conflict_on_commit: bool = False,
    ):
        self.users = FakeUserRepository(users)
        self.conflict_on_commit = conflict_on_commit
        self.committed = False
        self.rolled_back = False

    @property
    def repositories(self):
        return [self.users]

    async def commit(self) -> None:
        """Record a commit."""
        if self.conflict_on_commit:
            raise IntegrityConflict
        self.committed = True

    async def rollback(self) -> None:
        """Record a rollback."""
        self.rolled_back = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_candidate(email: str = "candidate@example.com") -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password="bcrypt_password123",
        role=UserRole.candidate,
        is_active=True,
    )


def make_employer(email: str = "employer@example.com", active: bool = False) -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password="bcrypt_password123",
        role=UserRole.employer,
        is_active=active,
    )


def make_admin(email: str = "admin@example.com") -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password="bcrypt_admin123",
        role=UserRole.admin,
        is_active=True,
    )


pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# RegisterUser
# ---------------------------------------------------------------------------


class TestRegisterUser:
    """Test cases for registration orchestration."""

    async def test_registers_candidate_and_commits(self):
        """
        GIVEN a valid candidate registration command
        WHEN the handler executes
        THEN the user is persisted, activated immediately, and the UoW commits.
        """
        command = RegisterUser(
            email="ada@example.com",
            plain_password="securepass",
            role=UserRole.candidate,
        )
        uow = FakeUnitOfWork()

        user_id = await services.register_user(command, uow)

        assert isinstance(user_id, UUID)
        assert uow.committed
        stored = uow.users.get(user_id)
        assert stored is not None
        assert stored.is_active is True
        assert stored.role == UserRole.candidate

    async def test_registers_employer_as_pending(self):
        """
        GIVEN a valid employer registration command
        WHEN the handler executes
        THEN the user is persisted with is_active=False awaiting admin approval.
        """
        command = RegisterUser(
            email="company@example.com",
            plain_password="securepass",
            role=UserRole.employer,
        )
        uow = FakeUnitOfWork()

        user_id = await services.register_user(command, uow)

        stored = uow.users.get(user_id)
        assert stored is not None
        assert stored.is_active is False

    async def test_emits_user_registered_event(self):
        """
        GIVEN a successful registration
        WHEN events are collected after commit
        THEN a UserRegistered event is present with the correct email.
        """
        command = RegisterUser(
            email="ada@example.com",
            plain_password="securepass",
            role=UserRole.candidate,
        )
        uow = FakeUnitOfWork()

        await services.register_user(command, uow)

        emitted = list(uow.collect_new_events())
        assert any(
            isinstance(e, events.UserRegistered) and e.email == "ada@example.com"
            for e in emitted
        )

    async def test_raises_on_duplicate_email(self):
        """
        GIVEN an existing user with the same email
        WHEN the registration handler executes
        THEN IntegrityConflict is raised and the UoW does not commit.
        """
        existing = make_candidate(email="ada@example.com")
        uow = FakeUnitOfWork(users=[existing], conflict_on_commit=True)
        command = RegisterUser(
            email="ada@example.com",
            plain_password="securepass",
            role=UserRole.candidate,
        )

        with pytest.raises(IntegrityConflict):
            await services.register_user(command, uow)

        assert not uow.committed

    async def test_raises_on_invalid_email(self):
        """
        GIVEN a malformed email address
        WHEN the handler executes
        THEN ValueError is raised before any persistence occurs.
        """
        command = RegisterUser(
            email="not-an-email",
            plain_password="securepass",
            role=UserRole.candidate,
        )
        uow = FakeUnitOfWork()

        with pytest.raises(ValueError, match="Invalid email address"):
            await services.register_user(command, uow)

        assert not uow.committed

    async def test_raises_on_weak_password(self):
        """
        GIVEN a password below the minimum length
        WHEN the handler executes
        THEN ValueError is raised before any persistence occurs.
        """
        command = RegisterUser(
            email="ada@example.com",
            plain_password="123",
            role=UserRole.candidate,
        )
        uow = FakeUnitOfWork()

        with pytest.raises(ValueError, match="Password is too short"):
            await services.register_user(command, uow)

        assert not uow.committed


# ---------------------------------------------------------------------------
# LoginUser
# ---------------------------------------------------------------------------


class TestLoginUser:
    """Test cases for login orchestration."""

    async def test_returns_user_on_valid_credentials(self):
        """
        GIVEN a registered active user and correct credentials
        WHEN the login handler executes
        THEN the user aggregate is returned.
        """
        user = make_candidate(email="ada@example.com")
        user.hashed_password = "bcrypt_securepass"
        uow = FakeUnitOfWork(users=[user])
        command = LoginUser(email="ada@example.com", plain_password="securepass")

        result = await services.login_user(command, uow)

        assert result.id == user.id

    async def test_raises_on_wrong_password(self):
        """
        GIVEN a registered active user and an incorrect password
        WHEN the login handler executes
        THEN an authentication error is raised.
        """
        user = make_candidate(email="ada@example.com")
        user.hashed_password = "bcrypt_securepass"
        uow = FakeUnitOfWork(users=[user])
        command = LoginUser(email="ada@example.com", plain_password="wrongpass")

        with pytest.raises(Exception):
            await services.login_user(command, uow)

    async def test_raises_on_unknown_email(self):
        """
        GIVEN no matching user in the repository
        WHEN the login handler executes
        THEN an authentication error is raised.
        """
        uow = FakeUnitOfWork()
        command = LoginUser(email="ghost@example.com", plain_password="securepass")

        with pytest.raises(Exception):
            await services.login_user(command, uow)

    async def test_raises_for_suspended_user(self):
        """
        GIVEN a suspended user
        WHEN the login handler executes
        THEN AccountSuspendedError propagates from the domain.
        """
        from src.users.domain.exceptions import AccountSuspendedError

        user = make_candidate(email="locked@example.com")
        user.hashed_password = "bcrypt_securepass"
        user.is_active = False
        uow = FakeUnitOfWork(users=[user])
        command = LoginUser(email="locked@example.com", plain_password="securepass")

        with pytest.raises(AccountSuspendedError):
            await services.login_user(command, uow)


# ---------------------------------------------------------------------------
# ChangePassword
# ---------------------------------------------------------------------------


class TestChangePassword:
    """Test cases for password change orchestration."""

    async def test_changes_password_and_commits(self):
        """
        GIVEN a valid user and a new password
        WHEN the handler executes
        THEN the hashed_password is updated and the UoW commits.
        """
        user = make_candidate()
        uow = FakeUnitOfWork(users=[user])
        command = ChangePassword(user_id=user.id, plain_new_password="newpassword123")

        await services.change_password(command, uow)

        assert uow.committed
        assert user.hashed_password != "bcrypt_password123"

    async def test_emits_password_changed_event(self):
        """
        GIVEN a successful password change
        WHEN events are collected
        THEN a PasswordChanged event is emitted for the user's email.
        """
        user = make_candidate(email="ada@example.com")
        uow = FakeUnitOfWork(users=[user])
        command = ChangePassword(user_id=user.id, plain_new_password="newpassword123")

        await services.change_password(command, uow)

        emitted = list(uow.collect_new_events())
        assert any(
            isinstance(e, events.PasswordChanged) and e.email == "ada@example.com"
            for e in emitted
        )

    async def test_raises_for_suspended_user(self):
        """
        GIVEN a suspended user
        WHEN the handler executes
        THEN AccountSuspendedError propagates and the UoW does not commit.
        """
        from src.users.domain.exceptions import AccountSuspendedError

        user = make_candidate()
        user.is_active = False
        uow = FakeUnitOfWork(users=[user])
        command = ChangePassword(user_id=user.id, plain_new_password="newpassword123")

        with pytest.raises(AccountSuspendedError):
            await services.change_password(command, uow)

        assert not uow.committed

    async def test_raises_for_unknown_user(self):
        """
        GIVEN a user_id that does not exist
        WHEN the handler executes
        THEN a lookup error is raised and nothing commits.
        """
        uow = FakeUnitOfWork()
        command = ChangePassword(user_id=uuid4(), plain_new_password="newpassword123")

        with pytest.raises(Exception):
            await services.change_password(command, uow)

        assert not uow.committed


# ---------------------------------------------------------------------------
# SuspendUser
# ---------------------------------------------------------------------------


class TestSuspendUser:
    """Test cases for user suspension orchestration."""

    async def test_admin_suspends_user_and_commits(self):
        """
        GIVEN an admin actor and an active target user
        WHEN the handler executes
        THEN the target is deactivated and the UoW commits.
        """
        admin = make_admin()
        target = make_candidate()
        uow = FakeUnitOfWork(users=[admin, target])
        command = SuspendUser(admin_id=admin.id, target_user_id=target.id)

        await services.suspend_user(command, uow)

        assert target.is_active is False
        assert uow.committed

    async def test_emits_user_suspended_event(self):
        """
        GIVEN an admin suspending a user
        WHEN events are collected
        THEN a UserSuspended event is emitted for the target's email.
        """
        admin = make_admin()
        target = make_candidate(email="victim@example.com")
        uow = FakeUnitOfWork(users=[admin, target])
        command = SuspendUser(admin_id=admin.id, target_user_id=target.id)

        await services.suspend_user(command, uow)

        emitted = list(uow.collect_new_events())
        assert any(
            isinstance(e, events.UserSuspended) and e.email == "victim@example.com"
            for e in emitted
        )

    async def test_non_admin_cannot_suspend(self):
        """
        GIVEN a non-admin actor
        WHEN the handler executes
        THEN InsufficientPermissionError is raised and nothing commits.
        """
        from src.users.domain.exceptions import InsufficientPermissionError

        actor = make_candidate(email="actor@example.com")
        target = make_candidate(email="target@example.com")
        uow = FakeUnitOfWork(users=[actor, target])
        command = SuspendUser(admin_id=actor.id, target_user_id=target.id)

        with pytest.raises(InsufficientPermissionError):
            await services.suspend_user(command, uow)

        assert not uow.committed
        assert target.is_active is True


# ---------------------------------------------------------------------------
# ApproveEmployer
# ---------------------------------------------------------------------------


class TestApproveEmployer:
    """Test cases for employer approval orchestration."""

    async def test_admin_approves_pending_employer(self):
        """
        GIVEN an admin actor and a pending employer
        WHEN the handler executes
        THEN the employer is activated and the UoW commits.
        """
        admin = make_admin()
        employer = make_employer()
        uow = FakeUnitOfWork(users=[admin, employer])
        command = ApproveEmployer(admin_id=admin.id, target_user_id=employer.id)

        await services.approve_employer(command, uow)

        assert employer.is_active is True
        assert uow.committed

    async def test_emits_user_approved_event(self):
        """
        GIVEN an admin approving an employer
        WHEN events are collected
        THEN a UserApproved event is emitted for the employer's email.
        """
        admin = make_admin()
        employer = make_employer(email="company@example.com")
        uow = FakeUnitOfWork(users=[admin, employer])
        command = ApproveEmployer(admin_id=admin.id, target_user_id=employer.id)

        await services.approve_employer(command, uow)

        emitted = list(uow.collect_new_events())
        assert any(
            isinstance(e, events.UserApproved) and e.email == "company@example.com"
            for e in emitted
        )

    async def test_non_admin_cannot_approve(self):
        """
        GIVEN a non-admin actor
        WHEN the handler executes
        THEN InsufficientPermissionError is raised and nothing commits.
        """
        from src.users.domain.exceptions import InsufficientPermissionError

        actor = make_candidate(email="actor@example.com")
        employer = make_employer()
        uow = FakeUnitOfWork(users=[actor, employer])
        command = ApproveEmployer(admin_id=actor.id, target_user_id=employer.id)

        with pytest.raises(InsufficientPermissionError):
            await services.approve_employer(command, uow)

        assert not uow.committed
        assert employer.is_active is False
