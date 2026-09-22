from meldingen_core.actions.mail import BasePreviewMailAction

from meldingen.mail import BaseMailRenderer


class PreviewMailAction(BasePreviewMailAction):
    _render: BaseMailRenderer

    def __init__(self, renderer: BaseMailRenderer):
        self._render = renderer

    async def __call__(self, title: str, preview_text: str, body_text: str) -> str:
        return (await self._render(title, preview_text, body_text)).html
