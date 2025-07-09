from meldingen_core.actions.mail import BasePreviewMailAction

from meldingen.mail import BaseMailPreviewer


class PreviewMailAction(BasePreviewMailAction):
    _get_preview: BaseMailPreviewer

    def __init__(self, previewer: BaseMailPreviewer):
        self._get_preview = previewer

    async def __call__(self, title: str, preview_text: str, body_text: str) -> str:
        return await self._get_preview(title, preview_text, body_text)
