from unittest.mock import AsyncMock, Mock

import pytest
from meldingen_core.address import BaseAddressResolver
from pdok_api_client.api.locatieserver_api import LocatieserverApi
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
