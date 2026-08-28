"""Unit tests for the Application domain entity."""

import pytest
from datetime import datetime, UTC
from uuid import UUID, uuid4

from src.modules.shared.domain.entities import DomainError
from src.modules.applications.application.enums import ApplicationStatus
from src.modules.applications.domain.entities import Application


def make_application(
    *,
    candidate_id: UUID | None = None,
    job_id: UUID | None = None,
    cv_url: str = "https://s3.example.com/cv/abc123.pdf",
) -> Application:
    return Application(
        candidate_id=candidate_id if candidate_id is not None else uuid4(),
        job_id=job_id if job_id is not None else uuid4(),
        cv_url=cv_url,
    )


# ---------------------------------------------------------------------------
# creation
# ---------------------------------------------------------------------------


def test_application_defaults_to_submitted_status():
    application = make_application()
    assert application.status == ApplicationStatus.SUBMITTED


def test_application_generates_id():
    application = make_application()
    assert isinstance(application.id, UUID)


def test_application_rejects_empty_cv_url():
    with pytest.raises(DomainError, match="cv_url"):
        make_application(cv_url="   ")


def test_application_sets_created_at_and_updated_at():
    application = make_application()
    assert isinstance(application.created_at, datetime)
    assert isinstance(application.updated_at, datetime)


# ---------------------------------------------------------------------------
# status transitions
#   submitted -> reviewing
#   reviewing -> accepted
#   reviewing -> rejected
# ---------------------------------------------------------------------------


def test_move_to_reviewing_from_submitted():
    application = make_application()
    application.move_to_reviewing()
    assert application.status == ApplicationStatus.REVIEWING


def test_move_to_reviewing_raises_when_not_submitted():
    application = make_application()
    application.move_to_reviewing()
    with pytest.raises(DomainError, match="submitted"):
        application.move_to_reviewing()


def test_accept_from_reviewing():
    application = make_application()
    application.move_to_reviewing()
    application.accept()
    assert application.status == ApplicationStatus.ACCEPTED


def test_accept_raises_when_not_reviewing():
    application = make_application()  # still SUBMITTED
    with pytest.raises(DomainError, match="reviewing"):
        application.accept()


def test_reject_from_reviewing():
    application = make_application()
    application.move_to_reviewing()
    application.reject()
    assert application.status == ApplicationStatus.REJECTED


def test_reject_raises_when_not_reviewing():
    application = make_application()  # still SUBMITTED
    with pytest.raises(DomainError, match="reviewing"):
        application.reject()


def test_accept_raises_when_already_accepted():
    application = make_application()
    application.move_to_reviewing()
    application.accept()
    with pytest.raises(DomainError, match="reviewing"):
        application.accept()


def test_status_transition_touches_updated_at():
    application = make_application()
    original_updated_at = application.updated_at
    application.move_to_reviewing()
    assert application.updated_at >= original_updated_at
