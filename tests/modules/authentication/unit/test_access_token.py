"""Unit tests for AccessToken domain entity.

Covers all lifecycle methods:
  - revoke / activate
  - stamp_created_at
  - rotate_jti
  - set_claims (happy path + guard clauses)
"""

from datetime import datetime, UTC, timedelta
from uuid import UUID, uuid4

import pytest

from src.modules.authentication.domain.entities import AccessToken
from src.modules.shared.application.enums import Role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_access_token(
    *,
    expires_at: datetime | None = None,
    permission: Role = Role.CANDIDATE,
) -> AccessToken:
    return AccessToken(
        expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=15),
        permission=permission,
    )


def _valid_claims_kwargs(access_token: AccessToken) -> dict:
    """Return kwargs that satisfy set_claims() preconditions."""
    return dict(
        iss="https://issuer.example.com",
        sub=uuid4(),
        aud="https://api.example.com",
        jti=uuid4(),
        grant_id="user@example.com",
        scope="candidate",
    )


# ---------------------------------------------------------------------------
# revoke
# ---------------------------------------------------------------------------


def test_revoke_sets_revoked_to_true():
    token = make_access_token()

    token.revoke()

    assert token.revoked is True


def test_revoke_stamps_revoked_at():
    token = make_access_token()
    before = datetime.now(UTC)

    token.revoke()

    assert token.revoked_at is not None
    assert token.revoked_at >= before


def test_revoke_idempotent_second_call_updates_revoked_at():
    token = make_access_token()
    token.revoke()
    first_revoked_at = token.revoked_at

    token.revoke()

    # Still revoked, revoked_at refreshed (not necessarily equal due to clock)
    assert token.revoked is True
    assert token.revoked_at is not None
    assert first_revoked_at is not None
    assert token.revoked_at >= first_revoked_at


# ---------------------------------------------------------------------------
# activate
# ---------------------------------------------------------------------------


def test_activate_clears_revoked_flag():
    token = make_access_token()
    token.revoke()

    token.activate()

    assert token.revoked is False


def test_activate_clears_revoked_at():
    token = make_access_token()
    token.revoke()

    token.activate()

    assert token.revoked_at is None


def test_activate_on_non_revoked_token_is_a_no_op():
    token = make_access_token()
    assert token.revoked is False

    token.activate()  # should not raise

    assert token.revoked is False
    assert token.revoked_at is None


# ---------------------------------------------------------------------------
# stamp_created_at
# ---------------------------------------------------------------------------


def test_stamp_created_at_sets_a_datetime():
    token = make_access_token()
    assert token.created_at is None

    token.stamp_created_at()

    assert isinstance(token.created_at, datetime)


def test_stamp_created_at_is_timezone_aware():
    token = make_access_token()

    token.stamp_created_at()

    assert token.created_at is not None
    assert token.created_at.tzinfo is not None


def test_stamp_created_at_is_close_to_now():
    token = make_access_token()
    before = datetime.now(UTC)

    token.stamp_created_at()

    assert token.created_at is not None
    assert token.created_at >= before


# ---------------------------------------------------------------------------
# rotate_jti
# ---------------------------------------------------------------------------


def test_rotate_jti_saves_current_hashed_jti_as_previous():
    token = make_access_token()
    token.hashed_jti = "abc123"

    token.rotate_jti()

    assert token.previous_hashed_jti == "abc123"


def test_rotate_jti_does_not_clear_current_hashed_jti():
    token = make_access_token()
    token.hashed_jti = "abc123"

    token.rotate_jti()

    # hashed_jti is still set; caller is responsible for setting the new one
    assert token.hashed_jti == "abc123"


def test_rotate_jti_when_hashed_jti_is_none_sets_previous_to_none():
    token = make_access_token()
    assert token.hashed_jti is None

    token.rotate_jti()

    assert token.previous_hashed_jti is None


def test_rotate_jti_overwrites_previous_on_second_rotation():
    token = make_access_token()
    token.hashed_jti = "first"
    token.rotate_jti()

    token.hashed_jti = "second"
    token.rotate_jti()

    assert token.previous_hashed_jti == "second"


# ---------------------------------------------------------------------------
# set_claims — guard clause
# ---------------------------------------------------------------------------


def test_set_claims_raises_value_error_when_created_at_is_none():
    token = make_access_token()
    assert token.created_at is None

    with pytest.raises(ValueError, match="created_at"):
        token.set_claims(**_valid_claims_kwargs(token))


# ---------------------------------------------------------------------------
# set_claims — happy path
# ---------------------------------------------------------------------------


def test_set_claims_populates_claims_object():
    token = make_access_token()
    token.stamp_created_at()
    kwargs = _valid_claims_kwargs(token)

    token.set_claims(**kwargs)

    assert token.claims is not None


def test_set_claims_stores_correct_iss():
    token = make_access_token()
    token.stamp_created_at()
    kwargs = _valid_claims_kwargs(token)

    token.set_claims(**kwargs)

    assert token.claims is not None
    assert token.claims.iss == kwargs["iss"]


def test_set_claims_stores_correct_sub():
    token = make_access_token()
    token.stamp_created_at()
    kwargs = _valid_claims_kwargs(token)

    token.set_claims(**kwargs)

    assert token.claims is not None
    assert token.claims.sub == kwargs["sub"]


def test_set_claims_exp_matches_expires_at():
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    token = make_access_token(expires_at=expires_at)
    token.stamp_created_at()

    token.set_claims(**_valid_claims_kwargs(token))

    assert token.claims is not None
    assert token.claims.exp == int(expires_at.timestamp())


def test_set_claims_iat_matches_created_at():
    token = make_access_token()
    token.stamp_created_at()
    assert token.created_at is not None
    expected_iat = int(token.created_at.timestamp())

    token.set_claims(**_valid_claims_kwargs(token))

    assert token.claims is not None
    assert token.claims.iat == expected_iat


def test_set_claims_nbf_equals_iat():
    token = make_access_token()
    token.stamp_created_at()

    token.set_claims(**_valid_claims_kwargs(token))

    assert token.claims is not None
    assert token.claims.nbf == token.claims.iat


def test_set_claims_jti_matches_provided_value():
    token = make_access_token()
    token.stamp_created_at()
    kwargs = _valid_claims_kwargs(token)
    expected_jti: UUID = kwargs["jti"]

    token.set_claims(**kwargs)

    assert token.claims is not None
    assert token.claims.jti == expected_jti


def test_set_claims_is_overwritable_on_second_call():
    token = make_access_token()
    token.stamp_created_at()

    token.set_claims(**_valid_claims_kwargs(token))
    assert token.claims is not None
    first_jti = token.claims.jti

    new_kwargs = _valid_claims_kwargs(token)
    new_kwargs["jti"] = uuid4()
    token.set_claims(**new_kwargs)

    assert token.claims is not None
    assert token.claims.jti != first_jti
