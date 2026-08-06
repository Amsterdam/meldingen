import logging
from typing import Any, Callable

import magic
from fastapi import HTTPException
from meldingen_core.exceptions import NotFoundException
from meldingen_core.validators import (
    AttachmentLimitReachedException,
    BaseAttachmentLimitValidator,
    BaseMediaTypeIntegrityValidator,
    BaseMediaTypeValidator,
    MediaTypeIntegrityError,
    MediaTypeNotAllowed,
)
from pydantic_media_type import MediaType
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from meldingen.jsonlogic import JSONLogicValidationException, JSONLogicValidator
from meldingen.models import Melding, StaticFormTypeEnum
from meldingen.repositories import StaticFormRepository

logger = logging.getLogger(__name__)


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
    _allowed_media_types: list[MediaType]

    def __init__(self, allowed_media_types: list[MediaType]) -> None:
        self._allowed_media_types = allowed_media_types

    def __call__(self, media_type: str) -> None:
        if media_type not in self._allowed_media_types:
            raise MediaTypeNotAllowed()


class MediaTypeIntegrityValidator(BaseMediaTypeIntegrityValidator):
    def __call__(self, media_type: str, data: bytes) -> None:
        magic_media_type = magic.from_buffer(data, mime=True)

        if media_type != magic_media_type:
            raise MediaTypeIntegrityError()


class MeldingFormAttachmentLimitValidator(BaseAttachmentLimitValidator[Melding]):
    _max_attachments: int

    def __init__(self, max_attachments: int) -> None:
        self._max_attachments = max_attachments

    async def __call__(self, melding: Melding) -> None:
        # This check is typically done before saving the new attachment to ensure we don't exceed the limit.
        # Form uploads don't register a user_id, so we  only count those without one.
        attachments = await melding.awaitable_attrs.attachments
        form_uploads = [att for att in attachments if att.user_id is None]

        if len(form_uploads) >= self._max_attachments:
            raise AttachmentLimitReachedException(f"Too many attachments. Maximum allowed is {self._max_attachments}.")


class BackofficeAttachmentLimitValidator(BaseAttachmentLimitValidator[Melding]):
    _max_attachments: int

    def __init__(self, max_attachments: int) -> None:
        self._max_attachments = max_attachments

    async def __call__(self, melding: Melding) -> None:
        # This check is typically done before saving the new attachment to ensure we don't exceed the limit.
        # Backoffice uploads register a user_id, so we only count those with one.
        attachments = await melding.awaitable_attrs.attachments
        backoffice_uploads = [att for att in attachments if att.user_id is not None]

        if len(backoffice_uploads) >= self._max_attachments:
            raise AttachmentLimitReachedException(f"Too many attachments. Maximum allowed is {self._max_attachments}.")


class MeldingPrimaryFormValidator:
    _static_form_repository: StaticFormRepository
    _validate_using_jsonlogic: JSONLogicValidator

    def __init__(self, static_form_repository: StaticFormRepository, jsonlogic_validator: JSONLogicValidator) -> None:
        self._static_form_repository = static_form_repository
        self._validate_using_jsonlogic = jsonlogic_validator

    async def __call__(self, melding_dict: dict[str, Any]) -> None:
        try:
            primary_form = await self._static_form_repository.find_by_type(StaticFormTypeEnum.primary)
            components = await primary_form.awaitable_attrs.components
            assert len(components) == 1
            component = components[0]
            jsonlogic = await component.awaitable_attrs.jsonlogic

            if jsonlogic is not None:
                self._validate_using_jsonlogic(jsonlogic, melding_dict)
        except NotFoundException:
            logger.warning("The primary form seems to be missing!")
        except JSONLogicValidationException as e:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                detail=[{"msg": e.msg, "input": e.input, "type": "value_error"}],
            ) from e
