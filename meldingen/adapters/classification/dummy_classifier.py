from meldingen_core.classification import BaseClassifierAdapter


# Only works as a placeholder classifier for testing purposes.
# Returns existing classification with the same name as the input text.
class DummyClassifierAdapter(BaseClassifierAdapter):
    async def __call__(self, text: str) -> str:
        return text
