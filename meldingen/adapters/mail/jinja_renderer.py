from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markupsafe import Markup

from meldingen.mail import BaseMailRenderer, RenderedMail

TEMPLATE_DIR = Path(__file__).parent / "templates"
LOGO_PATH = TEMPLATE_DIR / "amsterdam-logo.png"

_TEXT = "font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:24px;color:#000000;"

# Mail clients strip <style> blocks, so styling has to be inline
_INLINE_STYLES = {
    "p": f"margin:0 0 16px 0;{_TEXT}",
    "h3": "margin:24px 0 8px 0;font-family:Helvetica,Arial,sans-serif;font-size:18px;line-height:26px;"
    "font-weight:700;color:#000000;",
    "ul": "margin:0 0 16px 0;padding-left:20px;",
    "ol": "margin:0 0 16px 0;padding-left:20px;",
    "li": f"margin:0 0 8px 0;{_TEXT}",
    "a": "color:#ec0000;text-decoration:underline;",
}


class JinjaMailRenderer(BaseMailRenderer):
    _markdown: MarkdownIt
    _environment: Environment
    _logo_src: str
    _disclaimer: str

    def __init__(self, logo_src: str, disclaimer: str) -> None:
        # melding.text is user input, so no raw html
        self._markdown = MarkdownIt("commonmark", {"html": False})
        self._environment = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        self._logo_src = logo_src
        self._disclaimer = disclaimer

    async def __call__(self, title: str, preview_text: str, body_text: str) -> RenderedMail:
        html = self._environment.get_template("mail.html.jinja").render(
            title=title,
            preview_text=preview_text,
            body_html=self._render_markdown(body_text),
            logo_src=self._logo_src,
            disclaimer=self._disclaimer,
        )

        return RenderedMail(html=html, text=body_text)

    def _render_markdown(self, text: str) -> Markup:
        tokens = self._markdown.parse(text)
        self._apply_inline_styles(tokens)

        return Markup(self._markdown.renderer.render(tokens, self._markdown.options, {}))

    def _apply_inline_styles(self, tokens: list[Token]) -> None:
        for token in tokens:
            style = _INLINE_STYLES.get(token.tag)
            if token.type.endswith("_open") and style is not None:
                token.attrSet("style", style)

            if token.children:
                self._apply_inline_styles(token.children)


def logo_bytes() -> bytes:
    return LOGO_PATH.read_bytes()
