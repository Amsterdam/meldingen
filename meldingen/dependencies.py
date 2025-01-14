import logging
from functools import lru_cache
from typing import Annotated, AsyncIterator

from azure.storage.blob.aio import ContainerClient
from fastapi import BackgroundTasks, Depends
from httpx import AsyncClient
from jwt import PyJWKClient, PyJWT
from meldingen_core.actions.melding import (
    MeldingAddAttachmentsAction,
    MeldingAnswerQuestionsAction,
    MeldingCompleteAction,
    MeldingContactInfoAddedAction,
    MeldingCreateAction,
    MeldingProcessAction,
    MeldingSubmitLocationAction,
    MeldingUpdateAction,
)
from meldingen_core.classification import Classifier
from meldingen_core.image import BaseImageOptimizer, BaseThumbnailGenerator
from meldingen_core.statemachine import MeldingTransitions
from meldingen_core.token import BaseTokenGenerator, TokenVerifier
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from plugfs.azure import AzureStorageBlobsAdapter
from plugfs.filesystem import Adapter, Filesystem
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from meldingen.actions import (
    AddContactInfoToMeldingAction,
    AddLocationToMeldingAction,
    AnswerCreateAction,
    ClassificationCreateAction,
    ClassificationDeleteAction,
    ClassificationListAction,
    ClassificationRetrieveAction,
    ClassificationUpdateAction,
    DeleteAttachmentAction,
    DownloadAttachmentAction,
    FormCreateAction,
    FormDeleteAction,
    FormListAction,
    FormRetrieveAction,
    FormRetrieveByClassificationAction,
    FormUpdateAction,
    ListAttachmentsAction,
    MeldingListAction,
    MeldingRetrieveAction,
    StaticFormListAction,
    StaticFormRetrieveAction,
    StaticFormUpdateAction,
    UploadAttachmentAction,
    UserCreateAction,
    UserDeleteAction,
    UserListAction,
    UserRetrieveAction,
    UserUpdateAction,
)
from meldingen.classification import DummyClassifierAdapter
from meldingen.config import settings
from meldingen.database import DatabaseSessionManager
from meldingen.factories import AttachmentFactory
from meldingen.image import (
    ImageOptimizerTask,
    IMGProxyImageOptimizer,
    IMGProxyImageOptimizerUrlGenerator,
    IMGProxyImageProcessor,
    IMGProxySignatureGenerator,
    IMGProxyThumbnailGenerator,
    IMGProxyThumbnailUrlGenerator,
    Ingestor,
    ThumbnailGeneratorTask,
)
from meldingen.jsonlogic import JSONLogicValidator
from meldingen.location import (
    GeoJsonFeatureFactory,
    LocationOutputTransformer,
    MeldingLocationIngestor,
    ShapePointFactory,
    ShapeToGeoJSONTransformer,
    ShapeToWKBTransformer,
    WKBToShapeTransformer,
)
from meldingen.models import Melding
from meldingen.repositories import (
    AnswerRepository,
    AttachmentRepository,
    ClassificationRepository,
    FormIoQuestionComponentRepository,
    FormRepository,
    MeldingRepository,
    QuestionRepository,
    StaticFormRepository,
    UserRepository,
)
from meldingen.schemas.output_factories import (
    FormCheckboxComponentOutputFactory,
    FormComponentOutputFactory,
    FormComponentValueOutputFactory,
    FormOutputFactory,
    FormRadioComponentOutputFactory,
    FormSelectComponentDataOutputFactory,
    FormSelectComponentOutputFactory,
    FormTextAreaComponentOutputFactory,
    FormTextFieldInputComponentOutputFactory,
    MeldingOutputFactory,
    SimpleStaticFormOutputFactory,
    StaticFormCheckboxComponentOutputFactory,
    StaticFormComponentOutputFactory,
    StaticFormOutputFactory,
    StaticFormRadioComponentOutputFactory,
    StaticFormSelectComponentOutputFactory,
    StaticFormTextAreaComponentOutputFactory,
    StaticFormTextFieldInputComponentOutputFactory,
    ValidateAdder,
)
from meldingen.statemachine import (
    AddAttachments,
    AddContactInfo,
    AnswerQuestions,
    Classify,
    Complete,
    HasClassification,
    HasLocation,
    MeldingStateMachine,
    MpFsmMeldingStateMachine,
    Process,
    SubmitLocation,
)
from meldingen.token import UrlSafeTokenGenerator
from meldingen.validators import MediaTypeIntegrityValidator, MediaTypeValidator


def tracer_provider() -> TracerProvider:
    resource = Resource(attributes={SERVICE_NAME: settings.opentelemetry_service_name})
    tracer_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=str(settings.opentelemetry_collector_receiver_endpoint)))
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)

    return tracer_provider


@lru_cache
def database_engine(tracer_provider: Annotated[TracerProvider, Depends(tracer_provider)]) -> AsyncEngine:
    echo: bool | str = False
    match settings.log_level:  # pragma: no cover
        case logging.INFO:
            echo = True
        case logging.DEBUG:
            echo = "debug"

    engine = create_async_engine(str(settings.database_dsn), echo=echo)

    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=tracer_provider)

    return engine


def database_session_manager(engine: Annotated[AsyncEngine, Depends(database_engine)]) -> DatabaseSessionManager:
    return DatabaseSessionManager(engine)


async def database_session(
    sessionmanager: Annotated[DatabaseSessionManager, Depends(database_session_manager)]
) -> AsyncIterator[AsyncSession]:
    async with sessionmanager.session() as session:
        yield session


def classification_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> ClassificationRepository:
    return ClassificationRepository(session)


def classification_create_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationCreateAction:
    return ClassificationCreateAction(repository)


def classification_retrieve_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationRetrieveAction:
    return ClassificationRetrieveAction(repository)


def classification_list_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationListAction:
    return ClassificationListAction(repository)


def classification_delete_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationDeleteAction:
    return ClassificationDeleteAction(repository)


def classification_update_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)]
) -> ClassificationUpdateAction:
    return ClassificationUpdateAction(repository)


def user_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> UserRepository:
    return UserRepository(session)


def melding_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> MeldingRepository:
    return MeldingRepository(session)


def answer_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> AnswerRepository:
    return AnswerRepository(session)


def question_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> QuestionRepository:
    return QuestionRepository(session)


def attachment_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> AttachmentRepository:
    return AttachmentRepository(session)


def classifier(repository: Annotated[ClassificationRepository, Depends(classification_repository)]) -> Classifier:
    return Classifier(DummyClassifierAdapter(), repository)


def token_generator() -> BaseTokenGenerator:
    return UrlSafeTokenGenerator()


def token_verifier(
    repository: Annotated[MeldingRepository, Depends(melding_repository)]
) -> TokenVerifier[Melding, Melding]:
    return TokenVerifier(repository)


def attachment_factory() -> AttachmentFactory:
    return AttachmentFactory()


def melding_state_machine() -> MeldingStateMachine:
    return MeldingStateMachine(
        MpFsmMeldingStateMachine(
            {
                MeldingTransitions.CLASSIFY: Classify([HasClassification()]),
                MeldingTransitions.ANSWER_QUESTIONS: AnswerQuestions(),
                MeldingTransitions.ADD_ATTACHMENTS: AddAttachments(),
                MeldingTransitions.SUBMIT_LOCATION: SubmitLocation([HasLocation()]),
                MeldingTransitions.ADD_CONTACT_INFO: AddContactInfo(),
                MeldingTransitions.PROCESS: Process(),
                MeldingTransitions.COMPLETE: Complete(),
            }
        )
    )


def melding_create_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    classifier: Annotated[Classifier, Depends(classifier)],
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    token_generator: Annotated[BaseTokenGenerator, Depends(token_generator)],
) -> MeldingCreateAction[Melding, Melding]:
    return MeldingCreateAction(repository, classifier, state_machine, token_generator, settings.token_duration)


def melding_retrieve_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)]
) -> MeldingRetrieveAction:
    return MeldingRetrieveAction(repository)


def melding_list_action(repository: Annotated[MeldingRepository, Depends(melding_repository)]) -> MeldingListAction:
    return MeldingListAction(repository)


def melding_update_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
    classifier: Annotated[Classifier, Depends(classifier)],
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
) -> MeldingUpdateAction[Melding, Melding]:
    return MeldingUpdateAction(repository, token_verifier, classifier, state_machine)


def melding_add_contact_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
) -> AddContactInfoToMeldingAction:
    return AddContactInfoToMeldingAction(repository, token_verifier)


def melding_answer_questions_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
) -> MeldingAnswerQuestionsAction[Melding, Melding]:
    return MeldingAnswerQuestionsAction(state_machine, repository, token_verifier)


def melding_add_attachments_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
) -> MeldingAddAttachmentsAction[Melding, Melding]:
    return MeldingAddAttachmentsAction(state_machine, repository, token_verifier)


def melding_process_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
) -> MeldingProcessAction[Melding, Melding]:
    return MeldingProcessAction(state_machine, repository)


def melding_submit_location_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
) -> MeldingSubmitLocationAction[Melding, Melding]:
    return MeldingSubmitLocationAction(state_machine, repository, token_verifier)


def melding_complete_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
) -> MeldingCompleteAction[Melding, Melding]:
    return MeldingCompleteAction(state_machine, repository)


def jsonlogic_validator() -> JSONLogicValidator:
    return JSONLogicValidator()


def form_io_question_component_repository(
    session: Annotated[AsyncSession, Depends(database_session)]
) -> FormIoQuestionComponentRepository:
    return FormIoQuestionComponentRepository(session)


def melding_answer_create_action(
    answer_repository: Annotated[AnswerRepository, Depends(answer_repository)],
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
    melding_repository: Annotated[MeldingRepository, Depends(melding_repository)],
    question_repository: Annotated[QuestionRepository, Depends(question_repository)],
    component_repository: Annotated[FormIoQuestionComponentRepository, Depends(form_io_question_component_repository)],
    jsonlogic_validator: Annotated[JSONLogicValidator, Depends(jsonlogic_validator)],
) -> AnswerCreateAction:
    return AnswerCreateAction(
        answer_repository,
        token_verifier,
        melding_repository,
        question_repository,
        component_repository,
        jsonlogic_validator,
    )


async def azure_container_client() -> AsyncIterator[ContainerClient]:
    client = ContainerClient.from_connection_string(
        f"DefaultEndpointsProtocol=http;AccountName={settings.azure_account_name};"
        f"AccountKey={settings.azure_account_key};"
        f"BlobEndpoint={str(settings.azure_storage_url)}{settings.azure_account_name};",
        settings.azure_container,
    )
    async with client:
        yield client


def filesystem_adapter(container_client: Annotated[ContainerClient, Depends(azure_container_client)]) -> Adapter:
    return AzureStorageBlobsAdapter(container_client)


def filesystem(adapter: Annotated[Adapter, Depends(filesystem_adapter)]) -> Filesystem:
    return Filesystem(adapter)


def media_type_validator() -> MediaTypeValidator:
    return MediaTypeValidator(settings.attachment_allow_media_types)


def media_type_integrity_validator() -> MediaTypeIntegrityValidator:
    return MediaTypeIntegrityValidator()


def img_proxy_signature_generator() -> IMGProxySignatureGenerator:
    return IMGProxySignatureGenerator(settings.imgproxy_key, settings.imgproxy_salt)


def http_client(tracer_provider: Annotated[TracerProvider, Depends(tracer_provider)]) -> AsyncClient:
    client = AsyncClient()

    HTTPXClientInstrumentor.instrument_client(client=client, tracer_provider=tracer_provider)

    return client


def img_proxy_image_optimizer_url_generator(
    signature_generator: Annotated[IMGProxySignatureGenerator, Depends(img_proxy_signature_generator)],
) -> IMGProxyImageOptimizerUrlGenerator:
    return IMGProxyImageOptimizerUrlGenerator(signature_generator, settings.imgproxy_base_url)


def img_proxy_image_optimizer_processor(
    url_generator: Annotated[IMGProxyImageOptimizerUrlGenerator, Depends(img_proxy_image_optimizer_url_generator)],
    http_client: Annotated[AsyncClient, Depends(http_client)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
) -> IMGProxyImageProcessor:
    return IMGProxyImageProcessor(url_generator, http_client, filesystem)


def image_optimizer(
    processor: Annotated[IMGProxyImageProcessor, Depends(img_proxy_image_optimizer_processor)]
) -> BaseImageOptimizer:
    return IMGProxyImageOptimizer(processor)


def image_optimizer_task(
    image_optimizer: Annotated[BaseImageOptimizer, Depends(image_optimizer)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
) -> ImageOptimizerTask:
    return ImageOptimizerTask(image_optimizer, attachment_repository)


def img_proxy_thumbnail_url_generator(
    signature_generator: Annotated[IMGProxySignatureGenerator, Depends(img_proxy_signature_generator)],
) -> IMGProxyThumbnailUrlGenerator:
    return IMGProxyThumbnailUrlGenerator(
        signature_generator, settings.imgproxy_base_url, settings.thumbnail_width, settings.thumbnail_height
    )


def img_proxy_thumbnail_processor(
    url_generator: Annotated[IMGProxyThumbnailUrlGenerator, Depends(img_proxy_thumbnail_url_generator)],
    http_client: Annotated[AsyncClient, Depends(http_client)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
) -> IMGProxyImageProcessor:
    return IMGProxyImageProcessor(url_generator, http_client, filesystem)


def thumbnail_generator(
    processor: Annotated[IMGProxyImageProcessor, Depends(img_proxy_thumbnail_processor)]
) -> BaseThumbnailGenerator:
    return IMGProxyThumbnailGenerator(processor)


def thumbnail_generator_task(
    thumbnail_generator: Annotated[BaseThumbnailGenerator, Depends(thumbnail_generator)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
) -> ThumbnailGeneratorTask:
    return ThumbnailGeneratorTask(thumbnail_generator, attachment_repository)


def attachment_ingestor(
    filesystem: Annotated[Filesystem, Depends(filesystem)],
    background_task_manager: BackgroundTasks,
    optimizer_task: Annotated[ImageOptimizerTask, Depends(image_optimizer_task)],
    thumbnail_task: Annotated[ThumbnailGeneratorTask, Depends(thumbnail_generator_task)],
) -> Ingestor:
    return Ingestor(
        filesystem,
        background_task_manager,
        optimizer_task,
        thumbnail_task,
        str(settings.attachment_storage_base_directory),
    )


def melding_upload_attachment_action(
    factory: Annotated[AttachmentFactory, Depends(attachment_factory)],
    repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
    media_type_validator: Annotated[MediaTypeValidator, Depends(media_type_validator)],
    media_type_integrity_validator: Annotated[MediaTypeIntegrityValidator, Depends(media_type_integrity_validator)],
    ingestor: Annotated[Ingestor, Depends(attachment_ingestor)],
) -> UploadAttachmentAction:
    return UploadAttachmentAction(
        factory,
        repository,
        token_verifier,
        media_type_validator,
        media_type_integrity_validator,
        ingestor,
    )


def melding_download_attachment_action(
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
) -> DownloadAttachmentAction:
    return DownloadAttachmentAction(token_verifier, attachment_repository, filesystem)


def melding_list_attachments_action(
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
) -> ListAttachmentsAction:
    return ListAttachmentsAction(token_verifier, attachment_repository)


def melding_delete_attachment_action(
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
) -> DeleteAttachmentAction:
    return DeleteAttachmentAction(token_verifier, attachment_repository, filesystem)


def shape_point_factory() -> ShapePointFactory:
    return ShapePointFactory()


def geo_json_feature_factory() -> GeoJsonFeatureFactory:
    return GeoJsonFeatureFactory()


def shape_to_wkb_transformer() -> ShapeToWKBTransformer:
    return ShapeToWKBTransformer()


def wkb_to_shape_transformer() -> WKBToShapeTransformer:
    return WKBToShapeTransformer()


def shape_to_geojson_transformer(
    geojson_factory: Annotated[GeoJsonFeatureFactory, Depends(geo_json_feature_factory)]
) -> ShapeToGeoJSONTransformer:
    return ShapeToGeoJSONTransformer(geojson_factory)


def location_ingestor(
    melding_repository: Annotated[MeldingRepository, Depends(melding_repository)],
    shape_point_factory: Annotated[ShapePointFactory, Depends(shape_point_factory)],
    shape_to_wkb_transformer: Annotated[ShapeToWKBTransformer, Depends(shape_to_wkb_transformer)],
) -> MeldingLocationIngestor:
    return MeldingLocationIngestor(melding_repository, shape_point_factory, shape_to_wkb_transformer)


def location_output_transformer(
    wkb_to_shape_transformer: Annotated[WKBToShapeTransformer, Depends(wkb_to_shape_transformer)],
    shape_to_geojson_transformer: Annotated[ShapeToGeoJSONTransformer, Depends(shape_to_geojson_transformer)],
) -> LocationOutputTransformer:
    return LocationOutputTransformer(wkb_to_shape_transformer, shape_to_geojson_transformer)


def melding_add_location_action(
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
    location_ingestor: Annotated[MeldingLocationIngestor, Depends(location_ingestor)],
) -> AddLocationToMeldingAction:
    return AddLocationToMeldingAction(token_verifier, location_ingestor)


def melding_output_factory(
    location_output_transformer: Annotated[LocationOutputTransformer, Depends(location_output_transformer)]
) -> MeldingOutputFactory:
    return MeldingOutputFactory(location_output_transformer)


def melding_contact_info_added_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding, Melding], Depends(token_verifier)],
) -> MeldingContactInfoAddedAction[Melding, Melding]:
    return MeldingContactInfoAddedAction(state_machine, repository, token_verifier)


def form_component_value_output_factory() -> FormComponentValueOutputFactory:
    return FormComponentValueOutputFactory()


def form_select_component_data_output_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)]
) -> FormSelectComponentDataOutputFactory:
    return FormSelectComponentDataOutputFactory(factory)


def static_form_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> StaticFormRepository:
    return StaticFormRepository(session)


def static_form_retrieve_action(
    repository: Annotated[StaticFormRepository, Depends(static_form_repository)]
) -> StaticFormRetrieveAction:
    return StaticFormRetrieveAction(repository)


def static_form_update_action(
    repository: Annotated[StaticFormRepository, Depends(static_form_repository)]
) -> StaticFormUpdateAction:
    return StaticFormUpdateAction(repository)


def static_form_list_action(
    repository: Annotated[StaticFormRepository, Depends(static_form_repository)]
) -> StaticFormListAction:
    return StaticFormListAction(repository)


def validate_adder() -> ValidateAdder:
    return ValidateAdder()


def static_form_text_area_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)]
) -> StaticFormTextAreaComponentOutputFactory:
    return StaticFormTextAreaComponentOutputFactory(_validate_adder)


def static_form_text_field_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)]
) -> StaticFormTextFieldInputComponentOutputFactory:
    return StaticFormTextFieldInputComponentOutputFactory(_validate_adder)


def static_form_checkbox_output_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> StaticFormCheckboxComponentOutputFactory:
    return StaticFormCheckboxComponentOutputFactory(factory, _validate_adder)


def static_form_radio_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> StaticFormRadioComponentOutputFactory:
    return StaticFormRadioComponentOutputFactory(factory, _validate_adder)


def static_form_select_factory(
    factory: Annotated[FormSelectComponentDataOutputFactory, Depends(form_select_component_data_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> StaticFormSelectComponentOutputFactory:
    return StaticFormSelectComponentOutputFactory(factory, _validate_adder)


def static_form_component_output_factory(
    text_area_factory: Annotated[
        StaticFormTextAreaComponentOutputFactory, Depends(static_form_text_area_output_factory)
    ],
    text_field_factory: Annotated[
        StaticFormTextFieldInputComponentOutputFactory, Depends(static_form_text_field_output_factory)
    ],
    checkbox_factory: Annotated[StaticFormCheckboxComponentOutputFactory, Depends(static_form_checkbox_output_factory)],
    radio_factory: Annotated[StaticFormRadioComponentOutputFactory, Depends(static_form_radio_factory)],
    select_factory: Annotated[StaticFormSelectComponentOutputFactory, Depends(static_form_select_factory)],
) -> StaticFormComponentOutputFactory:
    return StaticFormComponentOutputFactory(
        text_area_factory,
        text_field_factory,
        checkbox_factory,
        radio_factory,
        select_factory,
    )


def simple_static_form_output_factory() -> SimpleStaticFormOutputFactory:
    return SimpleStaticFormOutputFactory()


def static_form_output_factory(
    factory: Annotated[StaticFormComponentOutputFactory, Depends(static_form_component_output_factory)]
) -> StaticFormOutputFactory:
    return StaticFormOutputFactory(factory)


def form_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> FormRepository:
    return FormRepository(session)


def form_text_area_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)]
) -> FormTextAreaComponentOutputFactory:
    return FormTextAreaComponentOutputFactory(_validate_adder)


def form_text_field_input_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)]
) -> FormTextFieldInputComponentOutputFactory:
    return FormTextFieldInputComponentOutputFactory(_validate_adder)


def form_checkbox_output_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> FormCheckboxComponentOutputFactory:
    return FormCheckboxComponentOutputFactory(factory, _validate_adder)


def form_radio_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> FormRadioComponentOutputFactory:
    return FormRadioComponentOutputFactory(factory, _validate_adder)


def form_select_factory(
    factory: Annotated[FormSelectComponentDataOutputFactory, Depends(form_select_component_data_output_factory)],
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> FormSelectComponentOutputFactory:
    return FormSelectComponentOutputFactory(factory, _validate_adder)


def form_component_output_factory(
    text_area_factory: Annotated[FormTextAreaComponentOutputFactory, Depends(form_text_area_output_factory)],
    text_field_factory: Annotated[FormTextFieldInputComponentOutputFactory, Depends(form_text_field_input_factory)],
    checkbox_factory: Annotated[FormCheckboxComponentOutputFactory, Depends(form_checkbox_output_factory)],
    radio_factory: Annotated[FormRadioComponentOutputFactory, Depends(form_radio_factory)],
    select_factory: Annotated[FormSelectComponentOutputFactory, Depends(form_select_factory)],
) -> FormComponentOutputFactory:
    return FormComponentOutputFactory(
        text_area_factory,
        text_field_factory,
        checkbox_factory,
        radio_factory,
        select_factory,
    )


def form_output_factory(
    factory: Annotated[FormComponentOutputFactory, Depends(form_component_output_factory)]
) -> FormOutputFactory:
    return FormOutputFactory(factory)


def form_create_action(
    repository: Annotated[FormRepository, Depends(form_repository)],
    classification_repository: Annotated[ClassificationRepository, Depends(classification_repository)],
    question_repository: Annotated[QuestionRepository, Depends(question_repository)],
) -> FormCreateAction:
    return FormCreateAction(repository, classification_repository, question_repository)


def form_list_action(repository: Annotated[FormRepository, Depends(form_repository)]) -> FormListAction:
    return FormListAction(repository)


def form_retrieve_action(repository: Annotated[FormRepository, Depends(form_repository)]) -> FormRetrieveAction:
    return FormRetrieveAction(repository)


def form_retrieve_by_classification_action(
    repository: Annotated[FormRepository, Depends(form_repository)]
) -> FormRetrieveByClassificationAction:
    return FormRetrieveByClassificationAction(repository)


def form_update_action(
    repository: Annotated[FormRepository, Depends(form_repository)],
    classification_repository: Annotated[ClassificationRepository, Depends(classification_repository)],
    question_repository: Annotated[QuestionRepository, Depends(question_repository)],
) -> FormUpdateAction:
    return FormUpdateAction(repository, classification_repository, question_repository)


def form_delete_action(repository: Annotated[FormRepository, Depends(form_repository)]) -> FormDeleteAction:
    return FormDeleteAction(repository)


def jwks_client() -> PyJWKClient:
    return PyJWKClient(settings.jwks_url)


def py_jwt() -> PyJWT:
    return PyJWT()


def user_create_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserCreateAction:
    return UserCreateAction(repository)


def user_list_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserListAction:
    return UserListAction(repository)


def user_retrieve_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserRetrieveAction:
    return UserRetrieveAction(repository)


def user_update_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserUpdateAction:
    return UserUpdateAction(repository)


def user_delete_action(repository: Annotated[UserRepository, Depends(user_repository)]) -> UserDeleteAction:
    return UserDeleteAction(repository)
