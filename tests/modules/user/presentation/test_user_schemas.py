import pytest
from pydantic import ValidationError

from src.modules.shared.application.enums import Role
from src.modules.user.presentation.schemas import CreateRequest


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


def test_create_request_accepts_admin_role():
    request = CreateRequest(**valid_payload(role=Role.ADMIN.value))
    assert request.role == Role.ADMIN


def test_create_request_requires_role_field():
    with pytest.raises(ValidationError):
        CreateRequest(**valid_payload())
