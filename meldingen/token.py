from meldingen_core.token import BaseTokenGenerator
from secrets import token_urlsafe


class UrlSafeTokenGenerator(BaseTokenGenerator):
    async def __call__(self) -> str:
        return token_urlsafe()
