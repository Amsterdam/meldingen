import pytest
from markdown_it import MarkdownIt

from meldingen.markdown import (
    MarkdownLinkSchemeValidator,
    MarkdownToPlainTextConverter,
    escape_markdown_link_syntax,
)


def test_strips_bold_markup() -> None:
    convert = MarkdownToPlainTextConverter()

    assert convert("**bold**") == "bold"


def test_strips_heading_and_link_markup() -> None:
    convert = MarkdownToPlainTextConverter()

    assert convert("# Title\n\nSee [the docs](https://example.com/very/long/url)") == "Title\nSee the docs"


def test_plain_text_is_shorter_than_markdown_source() -> None:
    convert = MarkdownToPlainTextConverter()
    text = "**" + ("a" * 2999) + "**"

    plain = convert(text)

    assert plain == "a" * 2999
    assert len(plain) < len(text)


class PermissiveMarkdownIt(MarkdownIt):
    """Stands in for the mail service: a renderer with raw HTML enabled and no scheme filtering of
    its own, so anything that survives escaping shows up as a link."""

    def validateLink(self, url: str) -> bool:
        return True


def render_permissively(text: str) -> str:
    html: str = PermissiveMarkdownIt("commonmark").render(text)
    return html


@pytest.mark.parametrize(
    "text",
    [
        "[Klik hier](tel:0900-1234)",
        "[Klik hier](javascript:alert(1))",
        '<a href="javascript:alert(1)">Klik hier</a>',
        "<tel:0900-1234>",
        "![alt](javascript:alert(1))",
        # A reporter escaping our escape: the backslash they typed must stay their backslash.
        "\\[Klik hier](tel:0900-1234)",
        "[Klik hier][ref]\n\n[ref]: tel:0900-1234",
    ],
)
def test_escaping_leaves_no_link_or_image_behind(text: str) -> None:
    html = render_permissively(escape_markdown_link_syntax(text))

    assert "<a " not in html
    assert "<img" not in html


@pytest.mark.parametrize(
    "text",
    [
        "[Klik hier](tel:0900-1234)",
        '<a href="javascript:alert(1)">Klik hier</a>',
        "Er ligt afval op de stoep. Kosten: 10-20 euro & meer!",
        # Text that already looks like a character reference must not be read as one.
        "&lt;script&gt;",
    ],
)
def test_escaping_keeps_the_text_the_reporter_typed_visible(text: str) -> None:
    convert = MarkdownToPlainTextConverter()

    assert convert(escape_markdown_link_syntax(text)) == text


def test_escaping_leaves_ordinary_text_untouched() -> None:
    text = "Er ligt afval op de stoep, ongeveer 10 meter voorbij nummer 12."

    assert escape_markdown_link_syntax(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "[Bel](tel:14020)",
        "[Site](https://amsterdam.nl)",
        "[Mail](mailto:meldingen@amsterdam.nl)",
        "[Melding](/melding/1)",
        "[Naar boven](#top)",
        "<tel:14020>",
        "Gewoon een zin zonder links.",
    ],
)
def test_link_scheme_validator_allows_allowlisted_destinations(text: str) -> None:
    validate = MarkdownLinkSchemeValidator(("http", "https", "mailto", "tel"))

    assert validate(text) == []


@pytest.mark.parametrize(
    ("text", "destination"),
    [
        ("[x](javascript:alert(1))", "javascript:alert(1)"),
        # markdown-it decodes character references in a destination, so neither may hide a scheme.
        ("[x](javascript&#58;alert(1))", "javascript:alert(1)"),
        ("[x](JAVASCRIPT:alert(1))", "JAVASCRIPT:alert(1)"),
        ("<javascript:alert(1)>", "javascript:alert(1)"),
        ("![x](data:text/html;base64,PHN2Zz4=)", "data:text/html;base64,PHN2Zz4="),
        ("[x](sms:0900-1234)", "sms:0900-1234"),
        # A destination behind a reference definition, and one nested in a block, are both reached.
        ("[x][ref]\n\n[ref]: vbscript:msgbox(1)", "vbscript:msgbox(1)"),
        ("> - [x](javascript:alert(1))\n", "javascript:alert(1)"),
    ],
)
def test_link_scheme_validator_reports_destinations_outside_the_allowlist(text: str, destination: str) -> None:
    validate = MarkdownLinkSchemeValidator(("http", "https", "mailto", "tel"))

    assert validate(text) == [destination]
