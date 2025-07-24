from meldingen_core.classification import BaseClassifierAdapter


class DummyClassifierAdapter(BaseClassifierAdapter):
    async def __call__(self, text: str) -> str:
        return text
