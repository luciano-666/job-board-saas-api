from uuid import uuid4
from src.modules.applications.domain.value_objects import CvStorageKey


def test_storage_key_format():
    candidate_id = uuid4()
    application_id = uuid4()

    key = CvStorageKey(candidate_id=candidate_id, application_id=application_id)

    assert str(key) == f"applications/{candidate_id}/{application_id}.pdf"


def test_storage_key_is_deterministic():
    candidate_id = uuid4()
    application_id = uuid4()

    key_a = str(CvStorageKey(candidate_id=candidate_id, application_id=application_id))
    key_b = str(CvStorageKey(candidate_id=candidate_id, application_id=application_id))

    assert key_a == key_b
