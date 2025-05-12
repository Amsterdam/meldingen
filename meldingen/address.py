from abc import ABCMeta, abstractmethod
from typing import Any

from meldingen_core.address import BaseAddressEnricher, BaseAddressResolver
from pdok_api_client.api.locatieserver_api import LocatieserverApi as PDOKApi
from pydantic_core import ValidationError

from meldingen.models import Melding
from meldingen.repositories import MeldingRepository
from meldingen.schemas.types import Address


class InvalidAPIRequestException(Exception): ...


class BaseAddressTransformer(metaclass=ABCMeta):

    @abstractmethod
    def __call__(self, data: dict[str, Any]) -> Address: ...


class PDOKAddressTransformer(BaseAddressTransformer):

    def __call__(self, data: dict[str, Any]) -> Address:
        return Address(
            street=data.get("straatnaam", None),
            house_number=data.get("huisnummer", None),
            house_number_addition=data.get("huisletter", None),
            postal_code=data.get("postcode", None),
            city=data.get("woonplaatsnaam", None),
        )


class PDOKAddressResolver(BaseAddressResolver[Address]):
    _api: PDOKApi
    _transform_address: PDOKAddressTransformer
    _search_config: dict[str, Any]

    def __init__(
        self, api_instance: PDOKApi, address_transformer: PDOKAddressTransformer, search_config: dict[str, Any]
    ) -> None:
        self._api = api_instance
        self._transform_address = address_transformer
        self._search_config = search_config

    async def __call__(self, lat: float, lon: float) -> Address | None:
        try:
            data = await self._api.reverse_geocoder(lat=lat, lon=lon, **self._search_config)
        except ValidationError as e:
            raise InvalidAPIRequestException(e)

        results = data.response
        assert results is not None
        assert isinstance(results.docs, list)

        if results.num_found == 0:
            return None

        return self._transform_address(results.docs[0])


class AddressEnricherTask(BaseAddressEnricher[Melding, Address], metaclass=ABCMeta):
    _resolve_address: BaseAddressResolver[Address]
    _repository: MeldingRepository

    async def __call__(self, melding: Melding, lat: float, lon: float) -> None:
        address = await self._resolve_address(lat, lon)

        if address is None:
            return

        melding.street = address.street
        melding.house_number = address.house_number
        melding.house_number_addition = address.house_number_addition
        melding.postal_code = address.postal_code
        melding.city = address.city

        await self._repository.save(melding)
