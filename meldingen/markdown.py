from collections.abc import Iterable, Iterator
from html.parser import HTMLParser
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token


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


# Characters that can start a link, an image or a raw HTML tag. The angle brackets and the
# ampersand are replaced by character references rather than backslash escapes: those survive
# every markdown dialect, whereas ``\<`` is only defined by CommonMark and would show up as a
# literal backslash in a renderer that follows the original Markdown escape set.
_LINK_SYNTAX_ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\\": "\\\\",
    "[": "\\[",
    "]": "\\]",
}


def escape_markdown_link_syntax(text: str) -> str:
    """Escapes the markdown constructs that turn text into a link, an image or an HTML tag.

    Text supplied by a reporter is typed into a plain text field, not authored as markdown, but
    it ends up inside a markdown mail template. Without escaping, a reporter controls the links
    of a mail that is sent, DKIM signed, from a municipal sender: ``[Bel ons](tel:0900-...)``
    becomes a link the recipient can tap. Escaping here keeps the text itself fully visible --
    the reporter still gets to read back what they submitted -- while making sure none of it is
    interpreted as markup.

    Emphasis and heading markers are deliberately left alone: they cannot carry a destination,
    and escaping them would put backslashes in front of the punctuation of every ordinary Dutch
    sentence.
    """
    return "".join(_LINK_SYNTAX_ESCAPES.get(character, character) for character in text)


class _UnfilteredMarkdownIt(MarkdownIt):
    """A parser that turns every link destination into a token instead of quietly dropping some.

    See ``MarkdownLinkSchemeValidator`` for why markdown-it's own link validation is in the way.
    """

    def validateLink(self, url: str) -> bool:
        return True


# The token types that carry a URL, and the attribute holding it.
_DESTINATION_ATTRIBUTES = {"link_open": "href", "image": "src"}


class MarkdownLinkSchemeValidator:
    """Collects link and image destinations whose URL scheme is not on the allowlist.

    markdown-it's own link validation is switched off on purpose. It silently drops a fixed set
    of dangerous schemes (``javascript:``, ``data:``, ``vbscript:``, ``file:``) instead of
    reporting them, which would hide exactly the destinations we want to refuse, and it lets
    everything else through, so it is a denylist where we need an allowlist. On top of that the
    markdown is rendered by the mail service, a different implementation that may well accept
    what markdown-it refuses, so its verdict is not something to depend on either way.
    """

    _markdown: MarkdownIt
    _allowed_schemes: frozenset[str]

    def __init__(self, allowed_schemes: Iterable[str]) -> None:
        self._markdown = _UnfilteredMarkdownIt()
        self._allowed_schemes = frozenset(scheme.lower() for scheme in allowed_schemes)

    def __call__(self, text: str) -> list[str]:
        return [
            destination
            for destination in self._destinations(self._markdown.parse(text))
            if not self._is_allowed(destination)
        ]

    def _destinations(self, tokens: Iterable[Token]) -> Iterator[str]:
        for token in tokens:
            attribute = _DESTINATION_ATTRIBUTES.get(token.type)
            if attribute is not None:
                destination = token.attrGet(attribute)
                if destination is not None:
                    yield str(destination)

            if token.children:
                yield from self._destinations(token.children)

    def _is_allowed(self, destination: str) -> bool:
        try:
            scheme = urlsplit(destination).scheme
        except ValueError:
            # A destination we cannot even parse is not one we should be sending out.
            return False

        # A destination without a scheme is relative, and so cannot select a protocol handler.
        return not scheme or scheme in self._allowed_schemes
