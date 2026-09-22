from html.parser import HTMLParser
from pathlib import Path
from typing import Final

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markupsafe import Markup

from meldingen.mail import BaseMailRenderer, RenderedMail

TEMPLATE_DIR: Final[Path] = Path(__file__).parent / "templates"
TEMPLATE_NAME: Final[str] = "mail.html.jinja"
LOGO_PATH: Final[Path] = TEMPLATE_DIR / "amsterdam-logo.png"

# Mail clients show the preview text followed by whatever comes next in the body. Padding it with
# zero width characters keeps the rest of the mail out of the inbox preview.
_PREHEADER_PADDING: Final[str] = "\u200c\u200b\u200d\u200e\u200f\ufeff" * 120

# Mail clients strip <style> blocks, so every tag markdown can produce needs its styling inline.
_INLINE_STYLES: Final[dict[str, str]] = {
    "p": "margin:0 0 16px 0;font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:24px;color:#000000;",
    "h1": "margin:24px 0 16px 0;font-family:Helvetica,Arial,sans-serif;font-size:28px;line-height:36px;"
    "font-weight:700;color:#000000;",
    "h2": "margin:24px 0 16px 0;font-family:Helvetica,Arial,sans-serif;font-size:22px;line-height:30px;"
    "font-weight:700;color:#000000;",
    "h3": "margin:24px 0 8px 0;font-family:Helvetica,Arial,sans-serif;font-size:18px;line-height:26px;"
    "font-weight:700;color:#000000;",
    "h4": "margin:16px 0 8px 0;font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:24px;"
    "font-weight:700;color:#000000;",
    "ul": "margin:0 0 16px 0;padding-left:20px;",
    "ol": "margin:0 0 16px 0;padding-left:20px;",
    "li": "margin:0 0 8px 0;font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:24px;color:#000000;",
    # #ec0000 on white is 4.6:1, which clears the WCAG AA threshold for body text. Underlined so the
    # link is not signalled by colour alone.
    "a": "color:#ec0000;text-decoration:underline;",
    "em": "font-style:italic;",
    "strong": "font-weight:700;",
    "blockquote": "margin:0 0 16px 0;padding-left:16px;border-left:4px solid #b4b4b4;",
    "hr": "border:none;border-top:1px solid #b4b4b4;margin:24px 0;",
}

_BLOCK_TAGS: Final[frozenset[str]] = frozenset({"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "div"})


class _PlainTextExtractor(HTMLParser):
    """Renders HTML down to readable plain text for the text/plain part of the mail.

    Link targets are kept: a recipient reading the plain text part should still be able to
    reach whatever the HTML part linked to.
    """

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._link_text = []
        elif tag == "br":
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            text = "".join(self._link_text).strip()
            href = self._href
            self._parts.append(text)
            # Repeating the target would only add noise when the link text already is the target,
            # which is what our tel: and mailto: links look like.
            if href and href != text and href.replace("tel:", "").replace(" ", "") != text.replace(" ", ""):
                self._parts.append(f" ({href})")
            self._href = None
            self._link_text = []
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._link_text.append(data)
        else:
            self._parts.append(data)

    @property
    def text(self) -> str:
        collapsed = "".join(self._parts)
        while "\n\n\n" in collapsed:
            collapsed = collapsed.replace("\n\n\n", "\n\n")
        return collapsed.strip()


class JinjaMailRenderer(BaseMailRenderer):
    """Renders our markdown into a mail body.

    ``logo_src`` is what the <img> points at. A sent mail carries the logo as a related MIME
    part and wants a ``cid:`` reference; a preview rendered in a browser cannot resolve that
    and wants a data URI instead.
    """

    _markdown: MarkdownIt
    _environment: Environment
    _logo_src: str
    _disclaimer: str

    def __init__(self, logo_src: str, disclaimer: str) -> None:
        # html=False matters: the body carries melding.text, which a reporter wrote. Raw HTML
        # would otherwise end up both in the mail and in the back office preview.
        self._markdown = MarkdownIt("commonmark", {"html": False, "linkify": False})
        self._environment = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(default=True),
        )
        self._logo_src = logo_src
        self._disclaimer = disclaimer

    async def __call__(self, title: str, preview_text: str, body_text: str) -> RenderedMail:
        body_html = self._render_markdown(body_text)

        html = self._environment.get_template(TEMPLATE_NAME).render(
            title=title,
            preview_text=preview_text,
            preheader_padding=_PREHEADER_PADDING,
            body_html=body_html,
            logo_src=self._logo_src,
            disclaimer=self._disclaimer,
        )

        return RenderedMail(html=html, text=self._to_plain_text(body_html))

    def _render_markdown(self, text: str) -> Markup:
        tokens = self._markdown.parse(text)
        self._apply_inline_styles(tokens)
        html = self._markdown.renderer.render(tokens, self._markdown.options, {})
        # Markup rather than |safe in the template: the markdown renderer runs with html=False,
        # so this is the one place that knows the output is already sanitised.
        return Markup(html)

    def _apply_inline_styles(self, tokens: list[Token]) -> None:
        for token in tokens:
            if token.type.endswith("_open") or token.type == "hr":
                style = _INLINE_STYLES.get(token.tag)
                if style is not None:
                    token.attrSet("style", style)

            if token.children:
                self._apply_inline_styles(token.children)

    def _to_plain_text(self, html: str) -> str:
        extractor = _PlainTextExtractor()
        extractor.feed(html)
        return extractor.text


def logo_bytes() -> bytes:
    return LOGO_PATH.read_bytes()
