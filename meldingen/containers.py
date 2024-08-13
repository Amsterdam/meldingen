import logging
from typing import AsyncGenerator

from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Configuration, Factory, Resource, Singleton
from meldingen_core.actions.user import UserCreateAction, UserDeleteAction
from pydantic_core import MultiHostUrl
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from meldingen.actions import (
    FormCreateAction,
    FormDeleteAction,
    FormListAction,
    FormRetrieveAction,
    FormRetrieveByClassificationAction,
    FormUpdateAction,
    UserListAction,
    UserRetrieveAction,
    UserUpdateAction,
)
from meldingen.repositories import (
    ClassificationRepository,
    FormRepository,
    GroupRepository,
    QuestionRepository,
    StaticFormRepository,
    UserRepository,
)
from meldingen.schema_factories import (
    FormCheckboxComponentOutputFactory,
    FormComponentOutputFactory,
    FormComponentValueOutputFactory,
    FormOutputFactory,
    FormRadioComponentOutputFactory,
    FormSelectComponentDataOutputFactory,
    FormSelectComponentOutputFactory,
    FormTextAreaComponentOutputFactory,
    FormTextFieldInputComponentOutputFactory,
)


def get_database_engine(dsn: MultiHostUrl, log_level: int = logging.NOTSET) -> AsyncEngine:
    """Returns an async database engine.

    echo can be configured via the environment variable for log_level.

    "This has the effect of setting the Python logging level for the namespace
    of this element’s class and object reference. A value of boolean True
    indicates that the loglevel logging.INFO will be set for the logger,
    whereas the string value debug will set the loglevel to logging.DEBUG."

    More info on: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncEngine.echo
    """
    echo: bool | str = False
    match log_level:  # pragma: no cover
        case logging.INFO:
            echo = True
        case logging.DEBUG:
            echo = "debug"

    return create_async_engine(str(dsn), echo=echo)


async def get_database_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


class Container(DeclarativeContainer):
    """Dependency injection container."""

    wiring_config: WiringConfiguration = WiringConfiguration(
        modules=[
            "meldingen.api.v1.endpoints.melding",
            "meldingen.api.v1.endpoints.user",
            "meldingen.authentication",
            "meldingen.api.v1.endpoints.classification",
            "meldingen.api.v1.endpoints.form",
            "meldingen.api.v1.endpoints.static_form",
        ]
    )

    settings: Configuration = Configuration(strict=True)
    database_engine: Singleton[AsyncEngine] = Singleton(
        get_database_engine, dsn=settings.database_dsn, log_level=settings.log_level
    )
    database_session: Resource[AsyncSession] = Resource(get_database_session, engine=database_engine)

    # repositories
    user_repository: Factory[UserRepository] = Factory(UserRepository, session=database_session)
    group_repository: Factory[GroupRepository] = Factory(GroupRepository, session=database_session)
    classification_repository: Factory[ClassificationRepository] = Factory(
        ClassificationRepository, session=database_session
    )
    form_repository: Factory[FormRepository] = Factory(FormRepository, session=database_session)
    static_form_repository: Factory[StaticFormRepository] = Factory(StaticFormRepository, session=database_session)
    question_repository: Factory[QuestionRepository] = Factory(QuestionRepository, session=database_session)

    # Factories
    form_text_area_factory: Factory[FormTextAreaComponentOutputFactory] = Factory(FormTextAreaComponentOutputFactory)
    form_text_field_factory: Factory[FormTextFieldInputComponentOutputFactory] = Factory(
        FormTextFieldInputComponentOutputFactory
    )
    form_values_factory: Factory[FormComponentValueOutputFactory] = Factory(FormComponentValueOutputFactory)
    form_checkbox_factory: Factory[FormCheckboxComponentOutputFactory] = Factory(
        FormCheckboxComponentOutputFactory, values_factory=form_values_factory
    )
    form_radio_factory: Factory[FormRadioComponentOutputFactory] = Factory(
        FormRadioComponentOutputFactory, values_factory=form_values_factory
    )
    form_select_data_factory: Factory[FormSelectComponentDataOutputFactory] = Factory(
        FormSelectComponentDataOutputFactory, values_factory=form_values_factory
    )
    form_select_factory: Factory[FormSelectComponentOutputFactory] = Factory(
        FormSelectComponentOutputFactory, data_factory=form_select_data_factory
    )
    form_components_factory: Factory[FormComponentOutputFactory] = Factory(
        FormComponentOutputFactory,
        text_area_factory=form_text_area_factory,
        text_field_factory=form_text_field_factory,
        checkbox_factory=form_checkbox_factory,
        radio_factory=form_radio_factory,
        select_factory=form_select_factory,
    )
    form_output_factory: Factory[FormOutputFactory] = Factory(
        FormOutputFactory, components_factory=form_components_factory
    )

    # User actions
    user_create_action: Factory[UserCreateAction] = Factory(UserCreateAction, repository=user_repository)
    user_list_action: Factory[UserListAction] = Factory(UserListAction, repository=user_repository)
    user_retrieve_action: Factory[UserRetrieveAction] = Factory(UserRetrieveAction, repository=user_repository)
    user_delete_action: Factory[UserDeleteAction] = Factory(UserDeleteAction, repository=user_repository)
    user_update_action: Factory[UserUpdateAction] = Factory(UserUpdateAction, repository=user_repository)

    # Form actions
    form_list_action: Factory[FormListAction] = Factory(FormListAction, repository=form_repository)
    form_retrieve_action: Factory[FormRetrieveAction] = Factory(FormRetrieveAction, repository=form_repository)
    form_create_action: Factory[FormCreateAction] = Factory(
        FormCreateAction,
        repository=form_repository,
        classification_repository=classification_repository,
        question_repository=question_repository,
    )
    form_update_action: Factory[FormUpdateAction] = Factory(
        FormUpdateAction,
        repository=form_repository,
        classification_repository=classification_repository,
        question_repository=question_repository,
    )
    form_delete_action: Factory[FormDeleteAction] = Factory(FormDeleteAction, repository=form_repository)
    form_classification_action: Factory[FormRetrieveByClassificationAction] = Factory(
        FormRetrieveByClassificationAction, repository=form_repository
    )
