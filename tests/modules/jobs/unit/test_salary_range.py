"""Unit tests for the SalaryRange value object."""

import pytest

from src.modules.shared.domain.entities import DomainError
from src.modules.jobs.domain.value_objects import SalaryRange

# ---------------------------------------------------------------------------
# valid construction
# ---------------------------------------------------------------------------


def test_accepts_min_equal_to_max():
    salary = SalaryRange(min=4000, max=4000)
    assert salary.min == 4000
    assert salary.max == 4000


def test_accepts_only_min():
    salary = SalaryRange(min=3000, max=None)
    assert salary.min == 3000
    assert salary.max is None


def test_accepts_only_max():
    salary = SalaryRange(min=None, max=5000)
    assert salary.min is None
    assert salary.max == 5000


def test_accepts_both_none():
    salary = SalaryRange(min=None, max=None)
    assert salary.min is None
    assert salary.max is None


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------


def test_rejects_min_greater_than_max():
    with pytest.raises(DomainError, match="min.*max"):
        SalaryRange(min=5000, max=3000)


def test_rejects_negative_min():
    with pytest.raises(DomainError, match="negative"):
        SalaryRange(min=-100, max=5000)


def test_rejects_negative_max():
    with pytest.raises(DomainError, match="negative"):
        SalaryRange(min=1000, max=-100)


def test_equality_by_value():
    assert SalaryRange(min=3000, max=5000) == SalaryRange(min=3000, max=5000)


def test_str_representation_with_both_bounds():
    salary = SalaryRange(min=3000, max=5000)
    assert str(salary) == "3000-5000"


def test_str_representation_with_only_min():
    salary = SalaryRange(min=3000, max=None)
    assert str(salary) == "3000+"


def test_str_representation_with_only_max():
    salary = SalaryRange(min=None, max=5000)
    assert str(salary) == "up to 5000"


def test_str_representation_when_undisclosed():
    salary = SalaryRange(min=None, max=None)
    assert str(salary) == "undisclosed"
