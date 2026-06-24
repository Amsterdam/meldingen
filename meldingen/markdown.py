from html.parser import HTMLParser

from markdown_it import MarkdownIt


class _PlainTextExtractor(HTMLParser):
    """Collects the textual content of an HTML document, ignoring the tags themselves."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    @property
    def text(self) -> str:
        return "".join(self._parts)


class MarkdownToPlainTextConverter:
    """Renders markdown and returns its plain text content.

    This is used to measure the length of a note as the user perceives it: markdown
    formatting characters (e.g. ``**bold**``, headings, link syntax) should not count
    towards the character limit, only the visible text does.
    """

    _markdown: MarkdownIt

    def __init__(self) -> None:
        self._markdown = MarkdownIt()

    def __call__(self, text: str) -> str:
        html = self._markdown.render(text)
        extractor = _PlainTextExtractor()
        extractor.feed(html)
        return extractor.text.strip()
