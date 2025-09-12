from collections.abc import Sequence
from typing import override

from fastapi import BackgroundTasks, HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from meldingen.location import MeldingLocationIngestor, WKBToPointShapeTransformer
from meldingen.models import Asset, AssetType, Melding
from meldingen.repositories import AttributeNotFoundException
from meldingen.schemas.types import Address, GeoJson
from meldingen.statemachine import MeldingStateMachine
from meldingen_core import SortingDirection
from meldingen_core.actions.melding import MeldingAddAssetAction as BaseMeldingAddAssetAction
from meldingen_core.actions.melding import MeldingAddContactInfoAction as BaseMeldingAddContactInfoAction
from meldingen_core.actions.melding import MeldingDeleteAssetAction as BaseMeldingDeleteAssetAction
from meldingen_core.actions.melding import MeldingListAction as BaseMeldingListAction
from meldingen_core.actions.melding import MeldingRetrieveAction as BaseMeldingRetrieveAction
from meldingen_core.actions.melding import MeldingSubmitAction as BaseMeldingSubmitAction
from meldingen_core.address import BaseAddressEnricher
from meldingen_core.exceptions import NotFoundException
from meldingen_core.filters import MeldingListFilters
from meldingen_core.repositories import BaseMeldingRepository
from meldingen_core.statemachine import MeldingBackofficeStates
from meldingen_core.token import TokenVerifier


class MeldingListAction(BaseMeldingListAction[Melding]):
    @override
    async def __call__(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
        filters: MeldingListFilters | None = None,
    ) -> Sequence[Melding]:
        try:
            return await super().__call__(
                limit=limit,
                offset=offset,
                sort_attribute_name=sort_attribute_name,
                sort_direction=sort_direction,
                filters=filters,
            )
        except AttributeNotFoundException as e:
            raise HTTPException(
                HTTP_422_UNPROCESSABLE_ENTITY,
                [{"loc": ("query", "sort"), "msg": e.message, "type": "attribute_not_found"}],
            )


class MeldingRetrieveAction(BaseMeldingRetrieveAction[Melding]): ...


class MelderMeldingRetrieveAction:
    _verify_token: TokenVerifier[Melding]

    def __init__(self, token_verifier: TokenVerifier[Melding]):
        self._verify_token = token_verifier

    async def __call__(self, melding_id: int, token: str) -> Melding:
        return await self._verify_token(melding_id, token)


class AddContactInfoToMeldingAction(BaseMeldingAddContactInfoAction[Melding]): ...


class MeldingAddAssetAction(BaseMeldingAddAssetAction[Melding, Asset, AssetType]): ...


class MeldingDeleteAssetAction(BaseMeldingDeleteAssetAction[Melding, Asset, AssetType]): ...


class MeldingSubmitAction(BaseMeldingSubmitAction[Melding]): ...


class AddLocationToMeldingAction:
    _verify_token: TokenVerifier[Melding]
    _ingest_location: MeldingLocationIngestor
    _background_task_manager: BackgroundTasks
    _add_address: BaseAddressEnricher[Melding, Address]
    _wkb_to_point_shape: WKBToPointShapeTransformer

    def __init__(
        self,
        token_verifier: TokenVerifier[Melding],
        location_ingestor: MeldingLocationIngestor,
        background_task_manager: BackgroundTasks,
        address_enricher: BaseAddressEnricher[Melding, Address],
        wkb_to_point_shape_transformer: WKBToPointShapeTransformer,
    ) -> None:
        self._verify_token = token_verifier
        self._ingest_location = location_ingestor
        self._background_task_manager = background_task_manager
        self._add_address = address_enricher
        self._wkb_to_point_shape = wkb_to_point_shape_transformer

    async def __call__(self, melding_id: int, token: str, location: GeoJson) -> Melding:
        melding = await self._verify_token(melding_id, token)
        melding = await self._ingest_location(melding, location)

        assert melding.geo_location is not None
        shape = self._wkb_to_point_shape(melding.geo_location)

        self._background_task_manager.add_task(self._add_address, melding, shape.x, shape.y)

        return melding


class MeldingGetPossibleNextStatesAction:
    _state_machine: MeldingStateMachine
    _melding_repository: BaseMeldingRepository[Melding]

    def __init__(self, state_machine: MeldingStateMachine, repository: BaseMeldingRepository[Melding]) -> None:
        self._state_machine = state_machine
        self._melding_repository = repository

    async def __call__(self, melding_id: int) -> list[str]:
        melding = await self._melding_repository.retrieve(melding_id)

        if melding is None:
            raise NotFoundException()

        melding_state = melding.state

        return [
            transition_name
            for transition_name, transition in self._state_machine._state_machine._transitions.items()
            if melding_state in transition.from_states and melding_state in MeldingBackofficeStates
        ]
