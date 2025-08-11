from unittest.mock import AsyncMock, Mock

import pytest
from meldingen_core.address import BaseAddressResolver
from pdok_api_client.api.locatieserver_api import LocatieserverApi
from pdok_api_client.models.free200_response import Free200Response
from pdok_api_client.models.response import Response
from pydantic_core import ValidationError

from meldingen.address import (
    AddressEnricherTask,
    InvalidAPIRequestException,
    PDOKAddressResolver,
    PDOKAddressTransformer,
)
from meldingen.models import Melding
from meldingen.repositories import MeldingRepository
from meldingen.schemas.types import Address


class TestAddressEnricherTask:
    @pytest.mark.anyio
    async def test_address_enricher_when_address_cannot_be_resolved(self) -> None:
        resolver = AsyncMock(BaseAddressResolver)
        resolver.return_value = None

        enrich = AddressEnricherTask(resolver, Mock(MeldingRepository))
        melding = Melding("text")

        await enrich(melding, 123.0, 456.0)

        assert melding.street is None
        assert melding.house_number is None
        assert melding.house_number_addition is None
        assert melding.postal_code is None
        assert melding.city is None

    @pytest.mark.anyio
    async def test_address_enricher_when_address_can_be_resolved(self) -> None:
        address = Address(
            street="Straatweglaan",
            house_number=12,
            house_number_addition="A",
            postal_code="1111AA",
            city="Amsterdam",
        )
        resolver = AsyncMock(BaseAddressResolver)
        resolver.return_value = address

        enrich = AddressEnricherTask(resolver, Mock(MeldingRepository))
        melding = Melding("text")

        await enrich(melding, 123.0, 456.0)

        assert melding.street == "Straatweglaan"
        assert melding.house_number == 12
        assert melding.house_number_addition == "A"
        assert melding.postal_code == "1111AA"
        assert melding.city == "Amsterdam"


class TestPDOKAddressResolver:
    @pytest.mark.anyio
    async def test_raises_invalid_api_request_exception(self) -> None:
        api = AsyncMock(LocatieserverApi)
        api.reverse_geocoder.side_effect = ValidationError("Title", [])

        resolve = PDOKAddressResolver(api, Mock(PDOKAddressTransformer), {})

        with pytest.raises(InvalidAPIRequestException):
            await resolve(123.0, 456.0)

    @pytest.mark.anyio
    async def test_returns_none_when_address_can_be_resolved(self) -> None:
        data = Mock(Free200Response)
        data.response = Mock(Response)
        data.response.num_found = 0
        data.response.docs = []

        api = AsyncMock(LocatieserverApi)
        api.reverse_geocoder.return_value = data

        resolve = PDOKAddressResolver(api, Mock(PDOKAddressTransformer), {})

        resolved = await resolve(123.0, 456.0)

        assert resolved is None

    @pytest.mark.anyio
    async def test_address_can_be_resolved(self) -> None:
        doc: dict[str, str | int | None] = {}
        data = Mock(Free200Response)
        data.response = Mock(Response)
        data.response.num_found = 1
        data.response.docs = [doc]

        api = AsyncMock(LocatieserverApi)
        api.reverse_geocoder.return_value = data

        address = Address(
            street="Straatweglaan",
            house_number=12,
            house_number_addition="A",
            postal_code="1111AA",
            city="Amsterdam",
        )

        transformer = Mock(PDOKAddressTransformer)
        transformer.return_value = address

        resolve = PDOKAddressResolver(api, transformer, {})

        resolved = await resolve(123.0, 456.0)

        assert resolved == address


class TestPDOKAddressTransformer:
    def test_address_transormer(self) -> None:
        data: dict[str, str | int | None] = {
            "straatnaam": "Straatweglaan",
            "huisnummer": 12,
            "huisletter": "A",
            "postcode": "1111AA",
            "woonplaatsnaam": "Amsterdam",
        }

        transformer = PDOKAddressTransformer()

        address = transformer(data)

        assert address.city == "Amsterdam"
        assert address.postal_code == "1111AA"
        assert address.house_number == 12
        assert address.house_number_addition == "A"
        assert address.street == "Straatweglaan"
