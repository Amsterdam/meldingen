from typing import Any, Callable

from meldingen_core.validators import BaseMediaTypeValidator, MediaTypeNotAllowed


def create_match_validator(match_value: Any, error_msg: str) -> Callable[[Any], Any]:
    """
    Create a validator function that checks if a value matches a given match_value.

    Examples:
    >>> validate = create_match_validator(5, "Value must be {match_value}")
    >>> validate(5)
    5
    >>> validate(6)
    AssertionError: Value must be 5
    """

    def validator(value: Any) -> Any:
        assert value == match_value, error_msg.format(value=value, match_value=match_value)
        return value

    return validator


def create_non_match_validator(match_value: Any, error_msg: str) -> Callable[[Any], Any]:
    """
    Create a validator function that checks if a value does not match a given match_value.

    Examples:
    >>> validate = create_non_match_validator("Hello", "Value must not match {match_value}")
    >>> validate("Hello")
    AssertionError: Value must not be 'Hello'
    >>> validate("world")
    'world'
    """

    def validator(value: Any) -> Any:
        assert value != match_value, error_msg.format(value=value, match_value=match_value)
        return value

    return validator


class MediaTypeValidator(BaseMediaTypeValidator):
    _allowed_media_types: list[str]

    def __init__(self, allowed_media_types: list[str]) -> None:
        self._allowed_media_types = allowed_media_types

    def __call__(self, media_type: str) -> None:
        if media_type not in self._allowed_media_types:
            raise MediaTypeNotAllowed()
