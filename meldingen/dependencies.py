import logging
from functools import lru_cache
from typing import Annotated, Any, AsyncIterator

from amsterdam_mail_service_client.api.default_api import DefaultApi
from amsterdam_mail_service_client.api_client import ApiClient
from amsterdam_mail_service_client.configuration import Configuration
from azure.storage.blob.aio import ContainerClient
from fastapi import BackgroundTasks, Depends
from httpx import AsyncClient
from jwt import PyJWKClient, PyJWT
from meldingen_core.actions.melding import (
    MelderMeldingListQuestionsAnswersAction,
    MeldingAddAttachmentsAction,
    MeldingAnswerQuestionsAction,
    MeldingCompleteAction,
    MeldingContactInfoAddedAction,
    MeldingCreateAction,
    MeldingListQuestionsAnswersAction,
    MeldingProcessAction,
    MeldingSubmitLocationAction,
    MeldingUpdateAction,
)
from meldingen_core.classification import Classifier
from meldingen_core.image import BaseImageOptimizer, BaseThumbnailGenerator
from meldingen_core.mail import BaseMeldingCompleteMailer, BaseMeldingConfirmationMailer
from meldingen_core.malware import BaseMalwareScanner
from meldingen_core.statemachine import MeldingTransitions
from meldingen_core.token import BaseTokenGenerator, TokenVerifier
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from pdok_api_client.api.locatieserver_api import LocatieserverApi as PDOKApiInstance
from pdok_api_client.api_client import ApiClient as PDOKApiClient
from pdok_api_client.configuration import Configuration as PDOKApiConfiguration
from plugfs.azure import AzureStorageBlobsAdapter
from plugfs.filesystem import Adapter, Filesystem
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from meldingen.actions import (
    AddContactInfoToMeldingAction,
    AddLocationToMeldingAction,
    AnswerCreateAction,
    AssetTypeCreateAction,
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
    MelderDownloadAttachmentAction,
    MelderListAttachmentsAction,
    MelderMeldingRetrieveAction,
    MeldingListAction,
    MeldingRetrieveAction,
    MeldingSubmitAction,
    PreviewMailAction,
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
from meldingen.address import AddressEnricherTask, PDOKAddressResolver, PDOKAddressTransformer
from meldingen.classification import DummyClassifierAdapter
from meldingen.config import settings
from meldingen.database import DatabaseSessionManager
from meldingen.factories import AttachmentFactory, AzureFilesystemFactory, BaseFilesystemFactory
from meldingen.generators import PublicIdGenerator
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
    WKBToPointShapeTransformer,
)
from meldingen.mail import (
    AmsterdamMailServiceMailer,
    AmsterdamMailServiceMailPreviewer,
    AmsterdamMailServiceMeldingCompleteMailer,
    AmsterdamMailServiceMeldingConfirmationMailer,
    BaseMailer,
    BaseMailPreviewer,
    SendCompletedMailTask,
    SendConfirmationMailTask,
)
from meldingen.malware import AzureDefenderForStorageMalwareScanner, DummyMalwareScanner
from meldingen.models import Answer, Melding
from meldingen.repositories import (
    AnswerRepository,
    AssetTypeRepository,
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
    AnswerListOutputFactory,
    FormCheckboxComponentOutputFactory,
    FormComponentOutputFactory,
    FormComponentValueOutputFactory,
    FormOutputFactory,
    FormRadioComponentOutputFactory,
    FormSelectComponentDataOutputFactory,
    FormSelectComponentOutputFactory,
    FormTextAreaComponentOutputFactory,
    FormTextFieldInputComponentOutputFactory,
    MeldingCreateOutputFactory,
    MeldingOutputFactory,
    SimpleClassificationOutputFactory,
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
    HasAnsweredRequiredQuestions,
    HasClassification,
    HasLocation,
    MeldingStateMachine,
    MpFsmMeldingStateMachine,
    Process,
    Submit,
    SubmitLocation,
)
from meldingen.token import TokenInvalidator, UrlSafeTokenGenerator
from meldingen.validators import MediaTypeIntegrityValidator, MediaTypeValidator


@lru_cache
def database_engine() -> AsyncEngine:
    echo: bool | str = False
    match settings.log_level:  # pragma: no cover
        case logging.INFO:
            echo = True
        case logging.DEBUG:
            echo = "debug"

    engine = create_async_engine(str(settings.database_dsn), echo=echo)

    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

    return engine


def database_session_manager(engine: Annotated[AsyncEngine, Depends(database_engine)]) -> DatabaseSessionManager:
    return DatabaseSessionManager(engine)


async def database_session(
    sessionmanager: Annotated[DatabaseSessionManager, Depends(database_session_manager)],
) -> AsyncIterator[AsyncSession]:
    async with sessionmanager.session() as session:
        yield session


def classification_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> ClassificationRepository:
    return ClassificationRepository(session)


def classification_create_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)],
) -> ClassificationCreateAction:
    return ClassificationCreateAction(repository)


def classification_retrieve_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)],
) -> ClassificationRetrieveAction:
    return ClassificationRetrieveAction(repository)


def classification_list_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)],
) -> ClassificationListAction:
    return ClassificationListAction(repository)


def classification_delete_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)],
) -> ClassificationDeleteAction:
    return ClassificationDeleteAction(repository)


def classification_update_action(
    repository: Annotated[ClassificationRepository, Depends(classification_repository)],
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


def form_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> FormRepository:
    return FormRepository(session)


def attachment_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> AttachmentRepository:
    return AttachmentRepository(session)


def classifier(repository: Annotated[ClassificationRepository, Depends(classification_repository)]) -> Classifier:
    return Classifier(DummyClassifierAdapter(), repository)


def token_generator() -> BaseTokenGenerator:
    return UrlSafeTokenGenerator()


def token_verifier(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
) -> TokenVerifier[Melding]:
    return TokenVerifier(repository)


def token_invalidator() -> TokenInvalidator:
    return TokenInvalidator()


def attachment_factory() -> AttachmentFactory:
    return AttachmentFactory()


def has_answered_required_questions(
    answer_repository: Annotated[AnswerRepository, Depends(answer_repository)],
    form_repository: Annotated[FormRepository, Depends(form_repository)],
) -> HasAnsweredRequiredQuestions:
    return HasAnsweredRequiredQuestions(answer_repository, form_repository)


def melding_state_machine(
    has_answered_required_questions: Annotated[HasAnsweredRequiredQuestions, Depends(has_answered_required_questions)],
) -> MeldingStateMachine:
    return MeldingStateMachine(
        MpFsmMeldingStateMachine(
            {
                MeldingTransitions.CLASSIFY: Classify([HasClassification()]),
                MeldingTransitions.ANSWER_QUESTIONS: AnswerQuestions([has_answered_required_questions]),
                MeldingTransitions.SUBMIT_LOCATION: SubmitLocation([HasLocation()]),
                MeldingTransitions.ADD_ATTACHMENTS: AddAttachments(),
                MeldingTransitions.ADD_CONTACT_INFO: AddContactInfo(),
                MeldingTransitions.SUBMIT: Submit(),
                MeldingTransitions.PROCESS: Process(),
                MeldingTransitions.COMPLETE: Complete(),
            }
        )
    )


def public_id_generator() -> PublicIdGenerator:
    return PublicIdGenerator()


def simple_classification_output_factory() -> SimpleClassificationOutputFactory:
    return SimpleClassificationOutputFactory()


def melding_create_output_factory(
    classification_output_factory: Annotated[
        SimpleClassificationOutputFactory, Depends(simple_classification_output_factory)
    ],
) -> MeldingCreateOutputFactory:
    return MeldingCreateOutputFactory(classification_output_factory)


def melding_create_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    classifier: Annotated[Classifier, Depends(classifier)],
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    token_generator: Annotated[BaseTokenGenerator, Depends(token_generator)],
) -> MeldingCreateAction[Melding]:
    return MeldingCreateAction(repository, classifier, state_machine, token_generator, settings.token_duration)


def melding_retrieve_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
) -> MeldingRetrieveAction:
    return MeldingRetrieveAction(repository)


def melder_melding_retrieve_action(
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
) -> MelderMeldingRetrieveAction:
    return MelderMeldingRetrieveAction(token_verifier)


def melding_list_action(repository: Annotated[MeldingRepository, Depends(melding_repository)]) -> MeldingListAction:
    return MeldingListAction(repository)


def melding_update_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    classifier: Annotated[Classifier, Depends(classifier)],
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
) -> MeldingUpdateAction[Melding]:
    return MeldingUpdateAction(repository, token_verifier, classifier, state_machine)


def melding_add_contact_action(
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
) -> AddContactInfoToMeldingAction:
    return AddContactInfoToMeldingAction(repository, token_verifier)


def melding_answer_questions_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
) -> MeldingAnswerQuestionsAction[Melding]:
    return MeldingAnswerQuestionsAction(state_machine, repository, token_verifier)


def melding_add_attachments_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
) -> MeldingAddAttachmentsAction[Melding]:
    return MeldingAddAttachmentsAction(state_machine, repository, token_verifier)


def melding_process_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
) -> MeldingProcessAction[Melding]:
    return MeldingProcessAction(state_machine, repository)


def melding_submit_location_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
) -> MeldingSubmitLocationAction[Melding]:
    return MeldingSubmitLocationAction(state_machine, repository, token_verifier)


def mail_configuration() -> Configuration:
    return Configuration(host=settings.mail_service_api_base_url)


async def mail_api_client(
    configuration: Annotated[Configuration, Depends(mail_configuration)],
) -> AsyncIterator[ApiClient]:
    async with ApiClient(configuration) as api_client:
        yield api_client


def mail_default_api(api_client: Annotated[ApiClient, Depends(mail_api_client)]) -> DefaultApi:
    return DefaultApi(api_client)


def mail_previewer(api: Annotated[DefaultApi, Depends(mail_default_api)]) -> BaseMailPreviewer:
    return AmsterdamMailServiceMailPreviewer(api)


def preview_mail_action(previewer: Annotated[BaseMailPreviewer, Depends(mail_previewer)]) -> PreviewMailAction:
    return PreviewMailAction(previewer)


def mailer(api: Annotated[DefaultApi, Depends(mail_default_api)]) -> BaseMailer:
    return AmsterdamMailServiceMailer(api)


def send_confirmation_mail_task(
    mailer: Annotated[BaseMailer, Depends(mailer)],
) -> SendConfirmationMailTask:
    return SendConfirmationMailTask(
        mailer,
        settings.mail_melding_confirmation_title,
        settings.mail_melding_confirmation_preview_text,
        settings.mail_melding_confirmation_body_text,
        settings.mail_default_sender,
        settings.mail_melding_confirmation_subject,
    )


def melding_confirmation_mailer(
    background_task_manager: BackgroundTasks,
    send_confirmation_mail_task: Annotated[SendConfirmationMailTask, Depends(send_confirmation_mail_task)],
) -> BaseMeldingConfirmationMailer[Melding]:
    return AmsterdamMailServiceMeldingConfirmationMailer(
        background_task_manager,
        send_confirmation_mail_task,
    )


def melding_submit_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    token_invalidator: Annotated[TokenInvalidator, Depends(token_invalidator)],
    confirmation_mailer: Annotated[BaseMeldingConfirmationMailer[Melding], Depends(melding_confirmation_mailer)],
) -> MeldingSubmitAction:
    return MeldingSubmitAction(repository, state_machine, token_verifier, token_invalidator, confirmation_mailer)


def send_completed_mail_task(mailer: Annotated[BaseMailer, Depends(mailer)]) -> SendCompletedMailTask:
    return SendCompletedMailTask(
        mailer,
        settings.mail_melding_completed_title,
        settings.mail_melding_completed_preview_text,
        settings.mail_default_sender,
        settings.mail_melding_completed_subject,
    )


def melding_complete_mailer(
    background_task_manager: BackgroundTasks,
    send_completed_mail_task: Annotated[SendCompletedMailTask, Depends(send_completed_mail_task)],
) -> BaseMeldingCompleteMailer[Melding]:
    return AmsterdamMailServiceMeldingCompleteMailer(background_task_manager, send_completed_mail_task)


def melding_complete_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    mailer: Annotated[BaseMeldingCompleteMailer[Melding], Depends(melding_complete_mailer)],
) -> MeldingCompleteAction[Melding]:
    return MeldingCompleteAction(state_machine, repository, mailer)


def jsonlogic_validator() -> JSONLogicValidator:
    return JSONLogicValidator()


def form_io_question_component_repository(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> FormIoQuestionComponentRepository:
    return FormIoQuestionComponentRepository(session)


def melding_answer_create_action(
    answer_repository: Annotated[AnswerRepository, Depends(answer_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
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


def melding_list_questions_and_answers_action(
    answer_repository: Annotated[AnswerRepository, Depends(answer_repository)],
) -> MeldingListQuestionsAnswersAction[Answer]:
    return MeldingListQuestionsAnswersAction(answer_repository)


def melder_melding_list_questions_and_answers_action(
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    answer_repository: Annotated[AnswerRepository, Depends(answer_repository)],
) -> MelderMeldingListQuestionsAnswersAction[Melding, Answer]:
    return MelderMeldingListQuestionsAnswersAction(token_verifier, answer_repository)


async def azure_container_client() -> AsyncIterator[ContainerClient]:
    client = ContainerClient.from_connection_string(
        settings.azure_storage_connection_string, settings.azure_storage_container
    )

    async with client:
        yield client


def filesystem_adapter(container_client: Annotated[ContainerClient, Depends(azure_container_client)]) -> Adapter:
    return AzureStorageBlobsAdapter(container_client)


def filesystem(adapter: Annotated[Adapter, Depends(filesystem_adapter)]) -> Filesystem:
    return Filesystem(adapter)


def filesystem_factory() -> BaseFilesystemFactory:
    return AzureFilesystemFactory()


def media_type_validator() -> MediaTypeValidator:
    return MediaTypeValidator(settings.attachment_allow_media_types)


def media_type_integrity_validator() -> MediaTypeIntegrityValidator:
    return MediaTypeIntegrityValidator()


def img_proxy_signature_generator() -> IMGProxySignatureGenerator:
    return IMGProxySignatureGenerator(settings.imgproxy_key, settings.imgproxy_salt)


def http_client() -> AsyncClient:
    client = AsyncClient()

    HTTPXClientInstrumentor.instrument_client(client=client)

    return client


def img_proxy_image_optimizer_url_generator(
    signature_generator: Annotated[IMGProxySignatureGenerator, Depends(img_proxy_signature_generator)],
) -> IMGProxyImageOptimizerUrlGenerator:
    return IMGProxyImageOptimizerUrlGenerator(signature_generator, settings.imgproxy_base_url)


def img_proxy_image_optimizer_processor(
    url_generator: Annotated[IMGProxyImageOptimizerUrlGenerator, Depends(img_proxy_image_optimizer_url_generator)],
    http_client: Annotated[AsyncClient, Depends(http_client)],
    filesystem_factory: Annotated[BaseFilesystemFactory, Depends(filesystem_factory)],
) -> IMGProxyImageProcessor:
    return IMGProxyImageProcessor(url_generator, http_client, filesystem_factory)


def image_optimizer(
    processor: Annotated[IMGProxyImageProcessor, Depends(img_proxy_image_optimizer_processor)],
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
    filesystem_factory: Annotated[BaseFilesystemFactory, Depends(filesystem_factory)],
) -> IMGProxyImageProcessor:
    return IMGProxyImageProcessor(url_generator, http_client, filesystem_factory)


def thumbnail_generator(
    processor: Annotated[IMGProxyImageProcessor, Depends(img_proxy_thumbnail_processor)],
) -> BaseThumbnailGenerator:
    return IMGProxyThumbnailGenerator(processor)


def thumbnail_generator_task(
    thumbnail_generator: Annotated[BaseThumbnailGenerator, Depends(thumbnail_generator)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
) -> ThumbnailGeneratorTask:
    return ThumbnailGeneratorTask(thumbnail_generator, attachment_repository)


def malware_scanner(
    container_client: Annotated[ContainerClient, Depends(azure_container_client)],
) -> BaseMalwareScanner:
    if settings.azure_malware_scanner_enabled:
        return AzureDefenderForStorageMalwareScanner(
            container_client, settings.azure_malware_scanner_tries, settings.azure_malware_scanner_sleep_time
        )

    return DummyMalwareScanner()


def attachment_ingestor(
    scanner: Annotated[BaseMalwareScanner, Depends(malware_scanner)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
    background_task_manager: BackgroundTasks,
    optimizer_task: Annotated[ImageOptimizerTask, Depends(image_optimizer_task)],
    thumbnail_task: Annotated[ThumbnailGeneratorTask, Depends(thumbnail_generator_task)],
) -> Ingestor:
    return Ingestor(
        scanner,
        filesystem,
        background_task_manager,
        optimizer_task,
        thumbnail_task,
        str(settings.attachment_storage_base_directory),
    )


def melding_upload_attachment_action(
    factory: Annotated[AttachmentFactory, Depends(attachment_factory)],
    repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
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


def melder_melding_download_attachment_action(
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
) -> MelderDownloadAttachmentAction:
    return MelderDownloadAttachmentAction(token_verifier, attachment_repository, filesystem)


def download_attachment_action(
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
    filesystem: Annotated[Filesystem, Depends(filesystem)],
) -> DownloadAttachmentAction:
    return DownloadAttachmentAction(attachment_repository, filesystem)


def melding_list_attachments_action(
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
) -> ListAttachmentsAction:
    return ListAttachmentsAction(attachment_repository)


def melder_melding_list_attachments_action(
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    attachment_repository: Annotated[AttachmentRepository, Depends(attachment_repository)],
) -> MelderListAttachmentsAction:
    return MelderListAttachmentsAction(token_verifier, attachment_repository)


def melding_delete_attachment_action(
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
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


def wkb_to_point_shape_transformer() -> WKBToPointShapeTransformer:
    return WKBToPointShapeTransformer()


def shape_to_geojson_transformer(
    geojson_factory: Annotated[GeoJsonFeatureFactory, Depends(geo_json_feature_factory)],
) -> ShapeToGeoJSONTransformer:
    return ShapeToGeoJSONTransformer(geojson_factory)


def address_api_configuration() -> PDOKApiConfiguration:
    return PDOKApiConfiguration(retries=settings.address_api_resolver_retries)


async def address_api_client(
    configuration: Annotated[PDOKApiConfiguration, Depends(address_api_configuration)],
) -> AsyncIterator[PDOKApiClient]:
    async with PDOKApiClient(configuration) as api_client:
        yield api_client


def address_api_instance(api_client: Annotated[PDOKApiClient, Depends(address_api_client)]) -> PDOKApiInstance:
    return PDOKApiInstance(api_client)


def address_transformer() -> PDOKAddressTransformer:
    return PDOKAddressTransformer()


def pdok_search_config() -> dict[str, Any]:
    return {
        "rows": 1,
        "distance": 30,
        "type": "adres",
        "fl": "id, afstand, huisnummer, huisletter, postcode, straatnaam, woonplaatsnaam",
    }


def address_resolver(
    api_instance: Annotated[PDOKApiInstance, Depends(address_api_instance)],
    address_transformer: Annotated[PDOKAddressTransformer, Depends(address_transformer)],
    search_config: Annotated[dict[str, Any], Depends(pdok_search_config)],
) -> PDOKAddressResolver:
    return PDOKAddressResolver(api_instance, address_transformer, search_config)


def address_enricher_task(
    address_resolver: Annotated[PDOKAddressResolver, Depends(address_resolver)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
) -> AddressEnricherTask:
    return AddressEnricherTask(address_resolver, repository)


def location_ingestor(
    melding_repository: Annotated[MeldingRepository, Depends(melding_repository)],
    shape_point_factory: Annotated[ShapePointFactory, Depends(shape_point_factory)],
    shape_to_wkb_transformer: Annotated[ShapeToWKBTransformer, Depends(shape_to_wkb_transformer)],
) -> MeldingLocationIngestor:
    return MeldingLocationIngestor(melding_repository, shape_point_factory, shape_to_wkb_transformer)


def location_output_transformer(
    wkb_to_point_shape_transformer: Annotated[WKBToPointShapeTransformer, Depends(wkb_to_point_shape_transformer)],
    shape_to_geojson_transformer: Annotated[ShapeToGeoJSONTransformer, Depends(shape_to_geojson_transformer)],
) -> LocationOutputTransformer:
    return LocationOutputTransformer(wkb_to_point_shape_transformer, shape_to_geojson_transformer)


def melding_add_location_action(
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
    location_ingestor: Annotated[MeldingLocationIngestor, Depends(location_ingestor)],
    background_task_manager: BackgroundTasks,
    address_enricher_task: Annotated[AddressEnricherTask, Depends(address_enricher_task)],
    wkb_to_point_shape_transformer: Annotated[WKBToPointShapeTransformer, Depends(wkb_to_point_shape_transformer)],
) -> AddLocationToMeldingAction:
    return AddLocationToMeldingAction(
        token_verifier,
        location_ingestor,
        background_task_manager,
        address_enricher_task,
        wkb_to_point_shape_transformer,
    )


def melding_output_factory(
    location_output_transformer: Annotated[LocationOutputTransformer, Depends(location_output_transformer)],
    classification_output_factory: Annotated[
        SimpleClassificationOutputFactory, Depends(simple_classification_output_factory)
    ],
) -> MeldingOutputFactory:
    return MeldingOutputFactory(location_output_transformer, classification_output_factory)


def melding_contact_info_added_action(
    state_machine: Annotated[MeldingStateMachine, Depends(melding_state_machine)],
    repository: Annotated[MeldingRepository, Depends(melding_repository)],
    token_verifier: Annotated[TokenVerifier[Melding], Depends(token_verifier)],
) -> MeldingContactInfoAddedAction[Melding]:
    return MeldingContactInfoAddedAction(state_machine, repository, token_verifier)


def melding_list_questions_and_answers_output_factory() -> AnswerListOutputFactory:
    return AnswerListOutputFactory()


def form_component_value_output_factory() -> FormComponentValueOutputFactory:
    return FormComponentValueOutputFactory()


def form_select_component_data_output_factory(
    factory: Annotated[FormComponentValueOutputFactory, Depends(form_component_value_output_factory)],
) -> FormSelectComponentDataOutputFactory:
    return FormSelectComponentDataOutputFactory(factory)


def static_form_repository(session: Annotated[AsyncSession, Depends(database_session)]) -> StaticFormRepository:
    return StaticFormRepository(session)


def static_form_retrieve_action(
    repository: Annotated[StaticFormRepository, Depends(static_form_repository)],
) -> StaticFormRetrieveAction:
    return StaticFormRetrieveAction(repository)


def static_form_update_action(
    repository: Annotated[StaticFormRepository, Depends(static_form_repository)],
) -> StaticFormUpdateAction:
    return StaticFormUpdateAction(repository)


def static_form_list_action(
    repository: Annotated[StaticFormRepository, Depends(static_form_repository)],
) -> StaticFormListAction:
    return StaticFormListAction(repository)


def validate_adder() -> ValidateAdder:
    return ValidateAdder()


def static_form_text_area_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> StaticFormTextAreaComponentOutputFactory:
    return StaticFormTextAreaComponentOutputFactory(_validate_adder)


def static_form_text_field_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
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
    factory: Annotated[StaticFormComponentOutputFactory, Depends(static_form_component_output_factory)],
) -> StaticFormOutputFactory:
    return StaticFormOutputFactory(factory)


def form_text_area_output_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
) -> FormTextAreaComponentOutputFactory:
    return FormTextAreaComponentOutputFactory(_validate_adder)


def form_text_field_input_factory(
    _validate_adder: Annotated[ValidateAdder, Depends(validate_adder)],
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
    factory: Annotated[FormComponentOutputFactory, Depends(form_component_output_factory)],
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
    repository: Annotated[FormRepository, Depends(form_repository)],
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


def asset_type_repository(database_session: Annotated[AsyncSession, Depends(database_session)]) -> AssetTypeRepository:
    return AssetTypeRepository(database_session)


def asset_type_create_action(
    repository: Annotated[AssetTypeRepository, Depends(asset_type_repository)],
) -> AssetTypeCreateAction:
    return AssetTypeCreateAction(repository)
