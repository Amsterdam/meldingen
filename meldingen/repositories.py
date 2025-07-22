from abc import ABCMeta, abstractmethod
from collections.abc import Sequence
from typing import Any, TypeVar

from meldingen_core import SortingDirection
from meldingen_core.exceptions import NotFoundException
from meldingen_core.repositories import (
    BaseAnswerRepository,
    BaseAssetRepository,
    BaseAssetTypeRepository,
    BaseAttachmentRepository,
    BaseClassificationRepository,
    BaseFormRepository,
    BaseMeldingRepository,
    BaseQuestionRepository,
    BaseRepository,
    BaseUserRepository,
)
from meldingen_core.statemachine import MeldingStates
from sqlalchemy import Select, delete, desc, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Relationship
from sqlalchemy.sql import func

from meldingen.models import (
    Answer,
    Asset,
    AssetType,
    Attachment,
    BaseDBModel,
    Classification,
    Form,
    FormIoQuestionComponent,
    Group,
    Melding,
    Question,
    StaticForm,
    User,
)


class AttributeNotFoundException(Exception):
    message: str

    def __init__(self, message: str):
        self.message = message


T = TypeVar("T", bound=BaseDBModel)


class BaseSQLAlchemyRepository(BaseRepository[T], metaclass=ABCMeta):
    """Base repository for SqlAlchemy based repositories."""

    _session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    def get_model_type(self) -> type[Any]: ...

    async def save(self, model: T, *, commit: bool = True) -> None:
        self._session.add(model)

        if commit:
            try:
                await self._session.commit()
            except IntegrityError as integrity_error:
                await self._session.rollback()
                raise integrity_error

            await self._session.refresh(model)

    async def flush(self) -> None:
        await self._session.flush()

    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
    ) -> Sequence[T]:
        _type = self.get_model_type()
        statement = select(_type)

        statement = self._handle_sorting(_type, statement, sort_attribute_name, sort_direction)

        if limit:
            statement = statement.limit(limit)

        if offset:
            statement = statement.offset(offset)

        results = await self._session.execute(statement)

        return results.scalars().unique().all()

    async def retrieve(self, pk: int) -> T | None:
        _type = self.get_model_type()
        statement = select(_type).where(_type.id == pk)
        results = await self._session.execute(statement)
        return results.scalars().unique().one_or_none()

    async def delete(self, pk: int) -> None:
        db_item = await self.retrieve(pk=pk)
        if db_item is None:
            raise NotFoundException()

        await self._session.delete(db_item)
        await self._session.commit()

    async def count(self) -> int:
        _type = self.get_model_type()
        statement = select(func.count(_type.id))
        result = await self._session.execute(statement)

        return result.scalars().one()

    def _handle_sorting(
        self,
        _type: type[Any],
        statement: Select[Any],
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
    ) -> Select[Any]:
        if sort_attribute_name is not None:
            sort_attribute = _type.__mapper__.attrs.get(sort_attribute_name)

            if sort_attribute is None:
                raise AttributeNotFoundException(f"Attribute {sort_attribute_name} not found")

            if isinstance(sort_attribute, Relationship):
                raise AttributeNotFoundException(f"Cannot sort on relationship {sort_attribute_name}")

            if sort_direction is None or sort_direction == SortingDirection.ASC:
                statement = statement.order_by(sort_attribute)
            elif sort_direction == SortingDirection.DESC:
                statement = statement.order_by(desc(sort_attribute))

        return statement


class MeldingRepository(BaseSQLAlchemyRepository[Melding], BaseMeldingRepository[Melding]):
    """Repository for Melding model."""

    def get_model_type(self) -> type[Melding]:
        return Melding

    async def delete_with_expired_token_and_in_states(self, states: Sequence[str]) -> Sequence[Melding]:
        _type = self.get_model_type()

        statement = delete(_type).where(_type.token_expires < func.now(), _type.state.in_(states)).returning(_type)

        result = await self._session.execute(statement)
        await self._session.commit()

        return result.scalars().unique().all()

    async def list_meldingen(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
        area: str | None = None,
        state: MeldingStates | None = None,
    ) -> Sequence[Melding]:
        _type = self.get_model_type()
        statement = select(_type)

        if area is not None:
            statement = statement.filter(func.ST_Contains(func.ST_GeomFromGeoJSON(area), Melding.geo_location))

        if state is not None:
            statement = statement.filter(Melding.state == state)

        statement = self._handle_sorting(_type, statement, sort_attribute_name, sort_direction)

        if limit:
            statement = statement.limit(limit)

        if offset:
            statement = statement.offset(offset)

        results = await self._session.execute(statement)

        return results.scalars().unique().all()


class UserRepository(BaseSQLAlchemyRepository[User], BaseUserRepository):
    def get_model_type(self) -> type[User]:
        return User

    async def find_by_email(self, email: str) -> User:
        statement = select(User).where(User.email == email)

        results = await self._session.execute(statement)

        return results.scalars().unique().one()


class GroupRepository(BaseSQLAlchemyRepository[Group]):
    def get_model_type(self) -> type[Group]:
        return Group

    async def find_by_name(self, name: str) -> Group:
        statement = select(Group).where(Group.name == name)
        results = await self._session.execute(statement)

        return results.scalars().one()


class ClassificationRepository(BaseSQLAlchemyRepository[Classification], BaseClassificationRepository[Classification]):
    def get_model_type(self) -> type[Classification]:
        return Classification

    async def find_by_name(self, name: str) -> Classification:
        statement = select(Classification).where(Classification.name == name)
        result = await self._session.execute(statement)
        classification = result.scalars().one_or_none()

        if classification is None:
            raise NotFoundException()

        return classification


class FormRepository(BaseSQLAlchemyRepository[Form], BaseFormRepository):
    def get_model_type(self) -> type[Form]:
        return Form

    async def find_by_classification_id(self, classification_id: int) -> Form:
        _type = self.get_model_type()
        statement = select(_type).where(_type.classification_id == classification_id)

        result = await self._session.execute(statement)
        try:
            return result.scalars().one()
        except NoResultFound:
            raise NotFoundException()


class StaticFormRepository(BaseSQLAlchemyRepository[StaticForm]):
    def get_model_type(self) -> type[StaticForm]:
        return StaticForm


class QuestionRepository(BaseSQLAlchemyRepository[Question], BaseQuestionRepository):
    def get_model_type(self) -> type[Question]:
        return Question


class FormIoQuestionComponentRepository(BaseSQLAlchemyRepository[FormIoQuestionComponent]):
    def get_model_type(self) -> type[FormIoQuestionComponent]:
        return FormIoQuestionComponent

    async def find_component_by_question_id(self, question_id: int) -> FormIoQuestionComponent:
        _type = self.get_model_type()
        statement = select(_type).where(FormIoQuestionComponent.question_id == question_id)

        result = await self._session.execute(statement)
        try:
            return result.scalars().one()
        except NoResultFound:
            raise NotFoundException()


class AnswerRepository(BaseSQLAlchemyRepository[Answer], BaseAnswerRepository[Answer]):
    def get_model_type(self) -> type[Answer]:
        return Answer

    async def find_by_melding(self, melding_id: int) -> Sequence[Answer]:
        _type = self.get_model_type()
        statement = select(_type).where(_type.melding_id == melding_id)

        results = await self._session.execute(statement)

        return results.scalars().unique().all()


class AttachmentRepository(BaseSQLAlchemyRepository[Attachment], BaseAttachmentRepository[Attachment]):
    """Repository for Attachment model."""

    def get_model_type(self) -> type[Attachment]:
        return Attachment

    async def find_by_melding(self, melding_id: int) -> Sequence[Attachment]:
        statement = select(Attachment).where(Attachment.melding_id == melding_id)

        result = await self._session.execute(statement)

        return result.scalars().all()


class AssetTypeRepository(BaseSQLAlchemyRepository[AssetType], BaseAssetTypeRepository[AssetType]):
    def get_model_type(self) -> type[AssetType]:
        return AssetType

    async def find_by_name(self, name: str) -> AssetType | None:
        _type = self.get_model_type()
        statement = select(_type).where(_type.name == name)

        result = await self._session.execute(statement)

        return result.scalars().one_or_none()


class AssetRepository(BaseSQLAlchemyRepository[Asset], BaseAssetRepository[Asset]):
    def get_model_type(self) -> type[Asset]:
        return Asset

    async def find_by_external_id_and_asset_type_id(self, external_id: str, asset_type_id: int) -> Asset | None:
        _type = self.get_model_type()
        statement = select(_type).where(_type.external_id == external_id).where(_type.type_id == asset_type_id)

        result = await self._session.execute(statement)

        return result.scalars().one_or_none()
