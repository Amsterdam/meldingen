import re
from abc import ABCMeta, abstractmethod
from typing import Any

from meldingen_core.address import Address, BaseAddressEnricher, BaseAddressResolver
from pdok_api_client.api.locatieserver_api import LocatieserverApi as PDOKApi
from pydantic_core import ValidationError

from meldingen.models import Melding
from meldingen.repositories import MeldingRepository


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


class AddressFormatter:
    """
    Based on the format classes found in django.utils.dateformat
    """

    re_formatchars = re.compile(r"(?<!\\)([OhltTpPW])")
    re_escaped = re.compile(r"\\(.)")

    def __init__(self, address: Address):
        self.address = address

    def O(self) -> str:
        """
        Openbare ruimte
        """
        return self.address.street if self.address and self.address.street else ""

    def h(self) -> str:
        """
        Huisnummer
        """
        return str(self.address.house_number) if self.address and self.address.house_number else ""

    # def l(self) -> str:
    #     """
    #     Huisletter
    #     """
    #     return self.address["huisletter"] if self.address and "huisletter" in self.address else ""

    def t(self) -> str:
        """
        Huisnummer toevoeging  without a hyphen
        """
        return self.address.house_number_addition if self.address and self.address.house_number_addition else ""

    def T(self) -> str:
        """
        Huisnummer toevoeging with a hyphen
        """
        if self.address and self.address.house_number_addition and len(self.address.house_number_addition.strip()) > 0:
            return f"-{self.address.house_number_addition}"
        else:
            return ""

    def p(self) -> str:
        """
        Postcode without a space between the digits and the characters
        """
        # Returns a postal code in the following format "1234AA"
        return self.address.postal_code.strip().replace(" ", "") if self.address and self.address.postal_code else ""

    def P(self) -> str:
        """
        Postcode with a space between the digits and the characters
        """
        # Returns a postal code in the following format "1234 AA"
        return (
            str(re.sub("(^[0-9]+)", r" \1 ", self.address.postal_code)).strip()
            if self.address and self.address.postal_code
            else ""
        )

    def W(self) -> str:
        """
        Woonplaats
        """
        return self.address.city if self.address and self.address.city else ""

    def format(self, format_str: str = "O hT, P W") -> str:
        formatted_string = []
        for i, format_char in enumerate(self.re_formatchars.split(str(format_str))):
            if i % 2:
                formatted_string.append(str(getattr(self, format_char)()))
            elif format_char:
                formatted_string.append(self.re_escaped.sub(r"\1", format_char))
        return "".join(formatted_string)
