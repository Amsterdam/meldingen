from secrets import token_urlsafe
from typing import override

from meldingen_core.statemachine import MeldingStates
from meldingen_core.token import BaseTokenGenerator, BaseTokenInvalidator

from meldingen.models import Melding


class UrlSafeTokenGenerator(BaseTokenGenerator):
    async def __call__(self) -> str:
        return token_urlsafe()


class TokenInvalidator(BaseTokenInvalidator[Melding]):

    @override
    @property
    def allowed_states(self) -> list[str]:
        return [MeldingStates.SUBMITTED]
