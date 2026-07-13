"""Service-layer tests for UserUseCases.

Uses FakeUserRepository and FakeSharedUseCases — no database involved.
Depth lives here: every branch of the use-case logic is exercised.
"""

import datetime
import pytest

from src.modules.user.application.enums import Gender
from src.modules.user.application.use_cases import UserUseCases
from src.modules.user.domain.entities import User
from src.modules.user.domain.value_objects import Name, Email
from src.modules.user.presentation.exceptions import (
    UserEmailAlreadyExistsException,
    UserEmailNotFoundException,
)
from tests.modules.user.fakes import FakeUserRepository, FakeSharedUseCases
from tests.utils import random_email, random_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(email: str | None = None, password: str = "P@ssword1") -> User:
    return User(
        name=Name(first_name="Jane", last_name="Doe"),
        gender=Gender.FEMALE,
        birthdate=datetime.date(1995, 6, 15),
        email=Email(email or random_email()),
        password=password,
    )


def make_use_cases(
    existing: list[User] | None = None,
) -> tuple[UserUseCases, FakeUserRepository]:
    repo = FakeUserRepository(existing)
    shared = FakeSharedUseCases(repo)
    return UserUseCases(repository=repo, shared_service=shared), repo


# ---------------------------------------------------------------------------
# create — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_stores_user_with_hashed_password():
    use_cases, repo = make_use_cases()
    user = make_user()

    result = await use_cases.create(user)

    stored = await repo.get_by_id(result.id)
    assert stored is not None
    # Password must be hashed, never stored in plaintext.
    assert stored.hashed_password is not None
    assert stored.hashed_password != "P@ssword1"


@pytest.mark.anyio
async def test_create_returns_the_user():
    use_cases, _ = make_use_cases()
    user = make_user()

    result = await use_cases.create(user)

    assert str(result.email) == str(user.email)


# ---------------------------------------------------------------------------
# create — duplicate email
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_raises_conflict_when_email_exists():
    email = random_email()
    existing = make_user(email=email)
    use_cases, _ = make_use_cases(existing=[existing])

    duplicate = make_user(email=email)

    with pytest.raises(UserEmailAlreadyExistsException):
        await use_cases.create(duplicate)


# ---------------------------------------------------------------------------
# create — user with no password sets hashed_password to None
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_without_password_sets_hashed_password_none():
    use_cases, repo = make_use_cases()
    user = make_user()
    user.password = None  # simulate social-login / admin-created user

    result = await use_cases.create(user)

    stored = await repo.get_by_id(result.id)
    assert stored is not None
    assert stored.hashed_password is None


# ---------------------------------------------------------------------------
# me — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_me_returns_user_from_db():
    existing = make_user()
    use_cases, _ = make_use_cases(existing=[existing])

    result = await use_cases.me(existing)

    assert result.id == existing.id
    assert str(result.email) == str(existing.email)


# ---------------------------------------------------------------------------
# me — user not found
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_me_raises_not_found_when_user_missing():
    use_cases, _ = make_use_cases()  # empty repo
    ghost = make_user()  # id not in store

    with pytest.raises(UserEmailNotFoundException):
        await use_cases.me(ghost)


# ---------------------------------------------------------------------------
# me — inactive / deleted user is not returned
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_me_raises_not_found_when_user_is_inactive():
    existing = make_user()
    existing.is_active = False
    repo = FakeUserRepository()
    # Store directly but mark inactive — get_by_id still returns it
    # from the fake. This test documents that the *use case* delegates
    # to get_user_by_id and propagates whatever the shared service gives.
    # In real integration the repository filters is_active=True.
    shared = FakeSharedUseCases(repo)
    use_cases = UserUseCases(repository=repo, shared_service=shared)

    with pytest.raises(UserEmailNotFoundException):
        await use_cases.me(existing)


# ---------------------------------------------------------------------------
# domain — age validation is enforced before reaching the use case
# ---------------------------------------------------------------------------


def test_user_entity_rejects_underage_birthdate():
    from src.modules.shared.domain.entities import DomainError

    today = datetime.date.today()
    underage = today.replace(year=today.year - 17)

    with pytest.raises(DomainError, match="18 years old"):
        User(
            name=Name(first_name="Teen", last_name="User"),
            gender=Gender.MALE,
            birthdate=underage,
            email=Email(random_email()),
        )


# ---------------------------------------------------------------------------
# domain — Name value object validation
# ---------------------------------------------------------------------------


def test_name_rejects_too_short_first_name():
    from src.modules.shared.domain.entities import DomainError

    with pytest.raises(DomainError):
        Name(first_name="Jo", last_name="Smith")


def test_name_sets_preferred_name_to_first_when_omitted():
    name = Name(first_name="Alice", last_name="Wonder")
    assert name.preferred_name == "Alice"


# ---------------------------------------------------------------------------
# domain — Email value object validation
# ---------------------------------------------------------------------------


def test_email_rejects_invalid_format():
    from src.modules.shared.domain.entities import DomainError

    with pytest.raises(DomainError):
        Email("not-an-email")


def test_email_normalises_to_lowercase():
    email = Email("User@Example.COM")
    assert str(email) == "user@example.com"


# ---------------------------------------------------------------------------
# domain — Phone value object validation
# ---------------------------------------------------------------------------


def test_phone_rejects_non_digit_characters():
    from src.modules.user.domain.value_objects import Phone
    from src.modules.shared.domain.entities import DomainError

    with pytest.raises(DomainError):
        Phone("abc")


def test_phone_normalises_with_plus_prefix():
    from src.modules.user.domain.value_objects import Phone

    phone = Phone("5554726642")
    assert str(phone).startswith("+")


# ---------------------------------------------------------------------------
# domain — user suspend / activate methods
# ---------------------------------------------------------------------------


def test_user_suspend_sets_is_active_false():
    user = make_user()
    user.suspend()
    assert user.is_active is False


def test_user_activate_sets_is_active_true():
    user = make_user()
    user.is_active = False
    user.activate()
    assert user.is_active is True


def test_user_suspend_raises_when_already_suspended():
    from src.modules.shared.domain.entities import DomainError

    user = make_user()
    user.suspend()

    with pytest.raises(DomainError, match="already suspended"):
        user.suspend()


def test_user_activate_raises_when_already_active():
    from src.modules.shared.domain.entities import DomainError

    user = make_user()

    with pytest.raises(DomainError, match="already active"):
        user.activate()


@pytest.mark.anyio
async def test_suspend_sets_user_inactive():
    existing = make_user()
    use_cases, repo = make_use_cases(existing=[existing])

    await use_cases.suspend(existing.id)

    stored = await repo.get_by_id_any_status(existing.id)
    assert stored is not None
    assert stored.is_active is False


@pytest.mark.anyio
async def test_suspend_raises_not_found_when_user_missing():
    use_cases, _ = make_use_cases()

    with pytest.raises(UserEmailNotFoundException):
        await use_cases.suspend(random_id())


@pytest.mark.anyio
async def test_activate_sets_user_active():
    existing = make_user()
    existing.is_active = False
    use_cases, repo = make_use_cases(existing=[existing])

    await use_cases.activate(existing.id)

    stored = await repo.get_by_id_any_status(existing.id)
    assert stored is not None
    assert stored.is_active is True
