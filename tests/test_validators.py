from os import path
from typing import Any, AsyncIterator

import pytest
from meldingen_core.validators import MediaTypeIntegrityError, MediaTypeNotAllowed
from pydantic_media_type import MediaType

from meldingen.validators import (
    MediaTypeIntegrityValidator,
    MediaTypeValidator,
    create_match_validator,
    create_non_match_validator,
)


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


class TestMediaTypeValidator:
    @pytest.fixture
    def media_type_validator(self) -> MediaTypeValidator:
        return MediaTypeValidator(
            [MediaType("image/jpeg"), MediaType("image/jpg"), MediaType("image/png"), MediaType("image/webp")]
        )

    @pytest.mark.parametrize(
        "media_type",
        [
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/webp",
        ],
    )
    def test_media_type_validator(self, media_type_validator: MediaTypeValidator, media_type: str) -> None:
        media_type_validator(media_type)

    def test_media_type_not_allowed(self, media_type_validator: MediaTypeValidator) -> None:
        with pytest.raises(MediaTypeNotAllowed):
            media_type_validator("application/octet-stream")


class TestMediaTypeIntegrityValidator:
    @pytest.fixture
    def media_type_integrity_validator(self) -> MediaTypeIntegrityValidator:
        return MediaTypeIntegrityValidator()

    async def _iterator(self) -> AsyncIterator[bytes]:
        with open(path.join(path.abspath(path.dirname(__file__)), "resources", "amsterdam-logo.png"), "rb") as file:
            while chunk := file.read(1024):
                yield chunk

    @pytest.mark.anyio
    async def test_media_type_matches(self, media_type_integrity_validator: MediaTypeIntegrityValidator) -> None:
        await media_type_integrity_validator("image/png", self._iterator())

    @pytest.mark.anyio
    async def test_media_type_does_not_match(self, media_type_integrity_validator: MediaTypeIntegrityValidator) -> None:
        with pytest.raises(MediaTypeIntegrityError):
            await media_type_integrity_validator("image/jpeg", self._iterator())
