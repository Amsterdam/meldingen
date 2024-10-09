from typing import Any

import pytest
from meldingen_core.validators import FileSizeNotAllowed

from meldingen.validators import create_match_validator, create_non_match_validator, FileSizeValidator


@pytest.mark.parametrize(
    "value, match_value",
    [
        (1, 1),
        (1.0, 1),
        (1.0, 1.0),
        (True, 1),
        (True, True),
        ([1, 2], [1, 2]),
    ],
)
def test_match_validator(value: Any, match_value: Any) -> None:
    test_validator = create_match_validator(match_value, error_msg="{value} should match {match_value}!")
    assert test_validator(value) == value


@pytest.mark.parametrize(
    "value, match_value, error_msg",
    [
        ("invalid_value", 1, "Value should be 1"),
        (10, 2, "Value should be 2"),
        (5.0, 3, "Value should be 3"),
        (4, 5.0, "Value should be 3"),
        (True, 5, "Value should be 4"),
        ("world", "hello", "{value} should match {match_value}!"),
        ((1, 2, 3), [1, 2, 3], "Value should match!"),
    ],
)
def test_invalid_match_validator(value: Any, match_value: Any, error_msg: str) -> None:
    test_validator = create_match_validator(match_value, error_msg=error_msg)
    with pytest.raises(AssertionError, match=error_msg.format(value=value, match_value=match_value)):
        test_validator(value)


@pytest.mark.parametrize(
    "value, match_value",
    [
        (1, 2),
        (1.0, 2),
        (1.0, 2.0),
        (True, 0),
        (True, False),
        ([1, 2], [2, 1]),
        ("hello", "world"),
    ],
)
def test_non_match_validator(value: Any, match_value: Any) -> None:
    test_validator = create_non_match_validator(match_value, error_msg="{value} should not match {match_value}!")
    assert test_validator(value) == value


@pytest.mark.parametrize(
    "value, match_value, error_msg",
    [
        (1, 1, "Value should not be 1"),
        (1.0, 1, "Value should not be 1"),
        (True, True, "{value} should not be {match_value}"),
        ([1, 2], [1, 2], "Something went wrong!!!"),
        ("Hello", "Hello", "Hello not allowed!"),
    ],
)
def test_invalid_non_match_validator(value: Any, match_value: Any, error_msg: str) -> None:
    test_validator = create_non_match_validator(match_value, error_msg=error_msg)
    with pytest.raises(AssertionError, match=error_msg.format(value=value, match_value=match_value)):
        test_validator(value)


class TestFileSizeValidator:
    @pytest.fixture
    def validate(self) -> FileSizeValidator:
        return FileSizeValidator(123)

    def test_file_size_validation(self, validate: FileSizeValidator) -> None:
        validate(122)

    def test_file_size_invalid(self, validate: FileSizeValidator) -> None:
        with pytest.raises(FileSizeNotAllowed):
            validate(124)
