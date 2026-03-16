from abc import ABCMeta, abstractmethod
from collections.abc import AsyncIterator

from meldingen_core.factories import BaseAssetFactory, BaseAttachmentFactory
from plugfs.filesystem import Filesystem

from meldingen.models import (
    Answer,
    AnswerTypeEnum,
    Asset,
    AssetType,
    Attachment,
    DateAnswer,
    Melding,
    Question,
    TextAnswer,
    TimeAnswer,
    ValueLabelAnswer,
    FormIoSelectComponent, FormIoComponentTypeEnum, FormIoDateComponent, FormIoTimeComponent, FormIoTextFieldComponent,
    FormIoTextAreaComponent, FormIoRadioComponent, FormIoCheckBoxComponent, FormIoQuestionComponent,
)
from meldingen.schemas.input import AnswerInputUnion, FormComponentInputUnion, FormComponentInput


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
        fields = {
            "type": answer_input.type,
            "melding": melding,
            "question": question,
            "original_question_text": question.text,
        }

        match answer_input.type:
            case AnswerTypeEnum.text:
                return TextAnswer(
                    **fields,
                    text=answer_input.text,
                )
            case AnswerTypeEnum.time:
                return TimeAnswer(
                    **fields,
                    time=answer_input.time,
                )
            case AnswerTypeEnum.date:
                return DateAnswer(
                    **fields,
                    date=answer_input.date.model_dump(),
                )
            case AnswerTypeEnum.value_label:
                return ValueLabelAnswer(
                    **fields,
                    values_and_labels=[v.model_dump() for v in answer_input.values_and_labels],
                )
            case _:
                raise UnsupportedAnswerTypeException(f"Unsupported answer type: {answer_input.type}")


class UnsupportedFormComponentTypeException(Exception):
    pass


class FormIoQuestionComponentFactory:

    def __call__(self, component_input: FormComponentInputUnion) -> FormIoQuestionComponent:
        dumped = component_input.model_dump(exclude={"validate_", "values", "data"})

        match component_input.type:
            case FormIoComponentTypeEnum.text_area:
                return FormIoTextAreaComponent(
                    **dumped,
                )
            case FormIoComponentTypeEnum.text_field :
                return FormIoTextFieldComponent(
                    **dumped,
                )
            case FormIoComponentTypeEnum.time:
                return FormIoTimeComponent(
                    **dumped,
                )
            case FormIoComponentTypeEnum.date:
                return FormIoDateComponent(
                    **dumped,
                )
            case FormIoComponentTypeEnum.select:
                return FormIoSelectComponent(
                    **dumped,
                )
            case FormIoComponentTypeEnum.radio:
                return FormIoRadioComponent(
                    **dumped,
                )
            case FormIoComponentTypeEnum.checkbox:
                return FormIoCheckBoxComponent(
                    **dumped,
                )
            case FormIoComponentTypeEnum.panel:
                    raise UnsupportedFormComponentTypeException("Panel components are not supported in this context.")
            case _:
                raise UnsupportedFormComponentTypeException(f"Unsupported form component type: {component_input.type}")
