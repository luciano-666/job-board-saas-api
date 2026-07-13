"""Schema-layer tests for public registration via the authentication module."""

import pytest
from pydantic import ValidationError

from src.modules.shared.application.enums import Role
from src.modules.authentication.presentation.schemas import RegisterRequest


def valid_payload(**overrides) -> dict:
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "preferred_name": "Johnny",
        "gender": "male",
        "birthdate": "1990-06-15",
        "email": "john.doe@example.com",
        "phone": "+15554726642",
        "password": "Str0ng@Pass!",
    }
    payload.update(overrides)
    return payload


def test_register_request_rejects_admin_role():
    with pytest.raises(ValidationError):
        RegisterRequest(**valid_payload(role=Role.ADMIN.value))


def test_register_request_accepts_employer_role():
    request = RegisterRequest(**valid_payload(role=Role.EMPLOYER.value))
    assert request.role == Role.EMPLOYER


def test_register_request_defaults_to_candidate_role():
    request = RegisterRequest(**valid_payload())
    assert request.role == Role.CANDIDATE
