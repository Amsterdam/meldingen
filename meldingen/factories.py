from abc import ABCMeta, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from meldingen_core.factories import BaseAssetFactory, BaseAttachmentFactory
from plugfs.filesystem import Filesystem

from meldingen.models import (
    Answer,
    AnswerTypeEnum,
    Asset,
    AssetType,
    Attachment,
    DateAnswer,
    FormIoCheckBoxComponent,
    FormIoComponentTypeEnum,
    FormIoDateComponent,
    FormIoQuestionComponent,
    FormIoRadioComponent,
    FormIoSelectComponent,
    FormIoTextAreaComponent,
    FormIoTextFieldComponent,
    FormIoTimeComponent,
    Melding,
    Question,
    TextAnswer,
    TimeAnswer,
    ValueLabelAnswer,
)
from meldingen.schemas.input import AnswerInputUnion


class AttachmentFactory(BaseAttachmentFactory[Attachment, Melding]):
    def __call__(self, original_filename: str, melding: Melding, media_type: str) -> Attachment:
        return Attachment(original_filename=original_filename, original_media_type=media_type, melding=melding)


class BaseFilesystemFactory(metaclass=ABCMeta):
    @abstractmethod
    def __call__(self) -> AsyncIterator[Filesystem]: ...


class AzureFilesystemFactory(BaseFilesystemFactory):
    async def __call__(self) -> AsyncIterator[Filesystem]:
        from meldingen.dependencies import azure_container_client, filesystem, filesystem_adapter

        async for client in azure_container_client():
            _filesystem = filesystem(filesystem_adapter(client))
            yield _filesystem


class AssetFactory(BaseAssetFactory[Asset, AssetType, Melding]):
    def __call__(self, external_id: str, asset_type: AssetType, melding: Melding) -> Asset:
        return Asset(external_id, asset_type, melding)


class UnsupportedAnswerTypeException(Exception):
    """Raised when an unsupported answer type is provided."""

    pass


class AnswerFactory:

    def __call__(self, answer_input: AnswerInputUnion, melding: Melding, question: Question) -> Answer:
        match answer_input.type:
            case AnswerTypeEnum.text:
                return TextAnswer(
                    type=answer_input.type,
                    melding=melding,
                    question=question,
                    original_question_text=question.text,
                    text=answer_input.text,
                )
            case AnswerTypeEnum.time:
                return TimeAnswer(
                    type=answer_input.type,
                    melding=melding,
                    question=question,
                    original_question_text=question.text,
                    time=answer_input.time,
                )
            case AnswerTypeEnum.date:
                return DateAnswer(
                    type=answer_input.type,
                    melding=melding,
                    question=question,
                    original_question_text=question.text,
                    date=answer_input.date.model_dump(),
                )
            case AnswerTypeEnum.value_label:
                return ValueLabelAnswer(
                    type=answer_input.type,
                    melding=melding,
                    question=question,
                    original_question_text=question.text,
                    values_and_labels=[v.model_dump() for v in answer_input.values_and_labels],
                )
            case _:
                raise UnsupportedAnswerTypeException(f"Unsupported answer type: {answer_input.type}")


class UnsupportedFormComponentTypeException(Exception):
    pass


class FormIoQuestionComponentFactory:

    def __call__(self, validated_component_input: dict[str, Any]) -> FormIoQuestionComponent:
        component_type = validated_component_input.get("type")

        match component_type:
            case FormIoComponentTypeEnum.text_area:
                return FormIoTextAreaComponent(
                    **validated_component_input,
                )
            case FormIoComponentTypeEnum.text_field:
                return FormIoTextFieldComponent(
                    **validated_component_input,
                )
            case FormIoComponentTypeEnum.time:
                return FormIoTimeComponent(
                    **validated_component_input,
                )
            case FormIoComponentTypeEnum.date:
                return FormIoDateComponent(
                    **validated_component_input,
                )
            case FormIoComponentTypeEnum.select:
                return FormIoSelectComponent(
                    **validated_component_input,
                )
            case FormIoComponentTypeEnum.radio:
                return FormIoRadioComponent(
                    **validated_component_input,
                )
            case FormIoComponentTypeEnum.checkbox:
                return FormIoCheckBoxComponent(
                    **validated_component_input,
                )
            case FormIoComponentTypeEnum.panel:
                raise UnsupportedFormComponentTypeException("Panel components are not supported in this context.")
            case _:
                raise UnsupportedFormComponentTypeException(f"Unsupported form component type: {component_type}")
