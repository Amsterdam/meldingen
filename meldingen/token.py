from secrets import token_urlsafe

from meldingen_core.token import BaseTokenGenerator


class UrlSafeTokenGenerator(BaseTokenGenerator):
    async def __call__(self) -> str:
        return token_urlsafe()
