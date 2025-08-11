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

    def __call__(self, data: dict[str, str | int | None]) -> Address:
        street = data.get("straatnaam")
        assert isinstance(street, str)
        house_number = data.get("huisnummer")
        assert isinstance(house_number, int)
        house_number_addition = data.get("huisletter")
        assert isinstance(house_number_addition, str) or house_number_addition is None
        postal_code = data.get("postcode")
        assert isinstance(postal_code, str)
        city = data.get("woonplaatsnaam")
        assert isinstance(city, str)

        return Address(
            street=street,
            house_number=house_number,
            house_number_addition=house_number_addition,
            postal_code=postal_code,
            city=city,
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
            raise InvalidAPIRequestException(e) from e

        results = data.response
        assert results is not None
        assert isinstance(results.docs, list)

        if results.num_found == 0:
            return None

        return self._transform_address(results.docs[0])


class AddressEnricherTask(BaseAddressEnricher[Melding, Address]):
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
