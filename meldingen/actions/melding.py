from collections.abc import Sequence
from typing import override

from fastapi import HTTPException
from meldingen_core import SortingDirection
from meldingen_core.actions.melding import MeldingAddAssetAction as BaseMeldingAddAssetAction
from meldingen_core.actions.melding import MeldingAddContactInfoAction as BaseMeldingAddContactInfoAction
from meldingen_core.actions.melding import MeldingListAction as BaseMeldingListAction
from meldingen_core.actions.melding import MeldingRetrieveAction as BaseMeldingRetrieveAction
from meldingen_core.actions.melding import MeldingSubmitAction as BaseMeldingSubmitAction
from meldingen_core.statemachine import MeldingStates
from meldingen_core.token import TokenVerifier
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from meldingen.models import Asset, AssetType, Melding
from meldingen.repositories import AttributeNotFoundException


class MeldingListAction(BaseMeldingListAction[Melding]):
    @override
    async def __call__(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: SortingDirection | None = None,
        area: str | None = None,
        state: MeldingStates | None = None,
    ) -> Sequence[Melding]:
        try:
            return await super().__call__(
                limit=limit,
                offset=offset,
                sort_attribute_name=sort_attribute_name,
                sort_direction=sort_direction,
                area=area,
                state=state,
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


class MeldingSubmitAction(BaseMeldingSubmitAction[Melding]): ...
