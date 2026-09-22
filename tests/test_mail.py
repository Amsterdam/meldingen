from email.message import EmailMessage
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import aiosmtplib
import pytest

from meldingen.adapters.mail.jinja_renderer import JinjaMailRenderer, logo_bytes
from meldingen.adapters.mail.smtp_mailer import LOGO_CONTENT_ID, LOGO_SRC, SmtpMailer
from meldingen.mail import (
    BaseMailer,
    BaseMailRenderer,
    EmailAddressMissingException,
    MailException,
    RenderedMail,
    SendCompletedMailTask,
    SendConfirmationMailTask,
)
from meldingen.models import Melding

DISCLAIMER = "U kunt niet op dit bericht antwoorden."


def renderer(logo_src: str = LOGO_SRC) -> JinjaMailRenderer:
    return JinjaMailRenderer(logo_src, DISCLAIMER)


def parts(message: EmailMessage) -> list[EmailMessage]:
    """typeshed types get_payload as a broad union, which multipart assertions cannot narrow."""
    return cast(list[EmailMessage], message.get_payload())


class TestJinjaMailRenderer:
    @pytest.mark.anyio
    async def test_renders_title_preview_text_and_disclaimer(self) -> None:
        mail = await renderer()("Uw melding", "Uw melding: 2026-000123", "Hallo")

        assert "<title>Uw melding</title>" in mail.html
        assert "Uw melding: 2026-000123" in mail.html
        assert DISCLAIMER in mail.html

    @pytest.mark.anyio
    async def test_declares_dutch_as_the_document_language(self) -> None:
        mail = await renderer()("Titel", "Preview", "Hallo")

        assert 'lang="nl"' in mail.html

    @pytest.mark.anyio
    async def test_points_the_logo_at_the_configured_source(self) -> None:
        mail = await renderer("data:image/png;base64,AAAA")("Titel", "Preview", "Hallo")

        assert 'src="data:image/png;base64,AAAA"' in mail.html

    @pytest.mark.anyio
    async def test_styles_markdown_inline(self) -> None:
        """Mail clients strip <style> blocks, so every tag needs its styling on the element."""
        mail = await renderer()("Titel", "Preview", "### Kopje\n\nEen alinea met [een link](https://example.com).")

        assert "<h3 style=" in mail.html
        assert "<p style=" in mail.html
        assert '<a href="https://example.com" style=' in mail.html

    @pytest.mark.anyio
    async def test_sizes_are_absolute(self) -> None:
        """Outlook renders with the Word engine, which does not understand rem."""
        mail = await renderer()("Titel", "Preview", "### Kopje\n\nEen alinea.")

        assert "rem" not in mail.html

    @pytest.mark.anyio
    async def test_escapes_html_in_the_body(self) -> None:
        """The body carries melding.text, which a reporter wrote."""
        mail = await renderer()("Titel", "Preview", "Kijk: <script>alert(1)</script>")

        assert "<script>" not in mail.html
        assert "&lt;script&gt;" in mail.html

    @pytest.mark.anyio
    async def test_does_not_render_javascript_links(self) -> None:
        mail = await renderer()("Titel", "Preview", "[klik hier](javascript:alert(1))")

        # Left as inert literal text instead of becoming a link, so nothing silently disappears.
        assert 'href="javascript:' not in mail.html
        assert "[klik hier](javascript:alert(1))" in mail.html

    @pytest.mark.anyio
    async def test_plain_text_drops_markup(self) -> None:
        mail = await renderer()("Titel", "Preview", "### Kopje\n\nEen **vette** alinea.")

        assert "<" not in mail.text
        assert "Kopje" in mail.text
        assert "Een vette alinea." in mail.text

    @pytest.mark.anyio
    async def test_plain_text_keeps_link_targets(self) -> None:
        mail = await renderer()("Titel", "Preview", "Zie [onze website](https://example.com).")

        assert "onze website (https://example.com)" in mail.text

    @pytest.mark.anyio
    async def test_plain_text_omits_a_link_target_that_repeats_its_text(self) -> None:
        mail = await renderer()("Titel", "Preview", "Bel [14 020](tel:14020).")

        assert "Bel 14 020." in mail.text


class TestSmtpMailer:
    def mailer(self, **overrides: object) -> SmtpMailer:
        kwargs: dict[str, object] = {
            "sender": "Gemeente Amsterdam <meldingen@amsterdam.nl>",
            "logo": logo_bytes(),
            "hostname": "mailpit",
            "port": 1025,
            "username": "user",
            "password": "secret",
            "start_tls": False,
            "use_tls": False,
        }
        kwargs.update(overrides)
        return SmtpMailer(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.anyio
    async def test_builds_an_alternative_message_with_an_inline_logo(self) -> None:
        with patch("meldingen.adapters.mail.smtp_mailer.aiosmtplib.send", new_callable=AsyncMock) as send:
            await self.mailer()("melder@example.com", "Onderwerp", RenderedMail(html="<p>Hoi</p>", text="Hoi"))

        message = send.call_args.args[0]
        assert isinstance(message, EmailMessage)
        assert message["From"] == "Gemeente Amsterdam <meldingen@amsterdam.nl>"
        assert message["To"] == "melder@example.com"
        assert message["Subject"] == "Onderwerp"
        assert message.get_content_type() == "multipart/alternative"

        text_part, related_part = parts(message)
        assert text_part.get_content_type() == "text/plain"
        assert related_part.get_content_type() == "multipart/related"

        html_part, logo_part = parts(related_part)
        assert html_part.get_content_type() == "text/html"
        assert logo_part.get_content_type() == "image/png"
        # Attached rather than linked, because mail clients block remote images by default.
        assert logo_part["Content-ID"] == f"<{LOGO_CONTENT_ID}>"
        assert logo_part.get_content_disposition() == "inline"

    @pytest.mark.anyio
    async def test_passes_the_connection_settings(self) -> None:
        with patch("meldingen.adapters.mail.smtp_mailer.aiosmtplib.send", new_callable=AsyncMock) as send:
            await self.mailer(hostname="relay", port=587, start_tls=True)(
                "melder@example.com", "Onderwerp", RenderedMail(html="<p>Hoi</p>", text="Hoi")
            )

        assert send.call_args.kwargs["hostname"] == "relay"
        assert send.call_args.kwargs["port"] == 587
        assert send.call_args.kwargs["start_tls"] is True
        assert send.call_args.kwargs["username"] == "user"
        assert send.call_args.kwargs["password"] == "secret"

    @pytest.mark.anyio
    async def test_treats_blank_credentials_as_absent(self) -> None:
        """An unset Key Vault secret arrives as an empty string, not as None."""
        with patch("meldingen.adapters.mail.smtp_mailer.aiosmtplib.send", new_callable=AsyncMock) as send:
            await self.mailer(username="", password="")(
                "melder@example.com", "Onderwerp", RenderedMail(html="<p>Hoi</p>", text="Hoi")
            )

        assert send.call_args.kwargs["username"] is None
        assert send.call_args.kwargs["password"] is None

    @pytest.mark.anyio
    async def test_wraps_smtp_failures(self) -> None:
        with patch("meldingen.adapters.mail.smtp_mailer.aiosmtplib.send", new_callable=AsyncMock) as send:
            send.side_effect = aiosmtplib.SMTPConnectError("nope")

            with pytest.raises(MailException):
                await self.mailer()("melder@example.com", "Onderwerp", RenderedMail(html="<p>Hoi</p>", text="Hoi"))


class TestSendConfirmationMailTask:
    def task(self, renderer: BaseMailRenderer, mailer: BaseMailer) -> SendConfirmationMailTask:
        return SendConfirmationMailTask(
            renderer,
            mailer,
            "Uw melding",
            "Uw melding: {}",
            "U meldde: {}. Nummer: {}.",
            "Uw melding {}: ontvangen",
        )

    @pytest.mark.anyio
    async def test_renders_and_sends(self) -> None:
        rendered = RenderedMail(html="<p>Hoi</p>", text="Hoi")
        renderer = AsyncMock(BaseMailRenderer, return_value=rendered)
        mailer = AsyncMock(BaseMailer)
        melding = Mock(Melding, email="melder@example.com", public_id="2026-000123", text="Kapotte stoeptegel")

        await self.task(renderer, mailer)(melding)

        renderer.assert_awaited_once_with(
            "Uw melding", "Uw melding: 2026-000123", "U meldde: Kapotte stoeptegel. Nummer: 2026-000123."
        )
        mailer.assert_awaited_once_with("melder@example.com", "Uw melding 2026-000123: ontvangen", rendered)

    @pytest.mark.anyio
    async def test_raises_when_the_melding_has_no_email_address(self) -> None:
        renderer = AsyncMock(BaseMailRenderer)
        mailer = AsyncMock(BaseMailer)
        melding = Mock(Melding, email=None, public_id="2026-000123", text="Kapotte stoeptegel")

        with pytest.raises(EmailAddressMissingException):
            await self.task(renderer, mailer)(melding)

        mailer.assert_not_awaited()


class TestSendCompletedMailTask:
    def task(self, renderer: BaseMailRenderer, mailer: BaseMailer) -> SendCompletedMailTask:
        return SendCompletedMailTask(renderer, mailer, "Afgehandeld", "Uw melding: {}", "Uw melding: {} afgehandeld")

    @pytest.mark.anyio
    async def test_sends_the_body_it_is_given(self) -> None:
        rendered = RenderedMail(html="<p>Hoi</p>", text="Hoi")
        renderer = AsyncMock(BaseMailRenderer, return_value=rendered)
        mailer = AsyncMock(BaseMailer)
        melding = Mock(Melding, email="melder@example.com", public_id="2026-000123", text="Kapotte stoeptegel")

        await self.task(renderer, mailer)(melding, "Wij hebben de tegel vervangen.")

        renderer.assert_awaited_once_with("Afgehandeld", "Uw melding: 2026-000123", "Wij hebben de tegel vervangen.")
        mailer.assert_awaited_once_with("melder@example.com", "Uw melding: 2026-000123 afgehandeld", rendered)

    @pytest.mark.anyio
    async def test_raises_when_the_melding_has_no_email_address(self) -> None:
        renderer = AsyncMock(BaseMailRenderer)
        mailer = AsyncMock(BaseMailer)
        melding = Mock(Melding, email=None, public_id="2026-000123", text="Kapotte stoeptegel")

        with pytest.raises(EmailAddressMissingException):
            await self.task(renderer, mailer)(melding, "Wij hebben de tegel vervangen.")

        mailer.assert_not_awaited()
