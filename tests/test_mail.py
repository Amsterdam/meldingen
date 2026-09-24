from email.message import EmailMessage
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import aiosmtplib
import pytest

from meldingen.adapters.mail.jinja_renderer import JinjaMailRenderer
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

RENDERED_MAIL = RenderedMail(html="<p>Hoi</p>", text="Hoi")


@pytest.mark.anyio
async def test_jinja_mail_renderer() -> None:
    render = JinjaMailRenderer("data:image/png;base64,AAAA", "Disclaimer")

    mail = await render("Titel", "Preview", "### Kopje\n\nEen alinea met [een link](https://example.com).")

    assert "<title>Titel</title>" in mail.html
    assert "Preview" in mail.html
    assert "Disclaimer" in mail.html
    assert 'src="data:image/png;base64,AAAA"' in mail.html
    assert "<h3 style=" in mail.html
    assert "<p style=" in mail.html
    assert '<a href="https://example.com" style=' in mail.html
    assert mail.text == "### Kopje\n\nEen alinea met [een link](https://example.com)."


@pytest.mark.anyio
async def test_jinja_mail_renderer_escapes_html() -> None:
    render = JinjaMailRenderer(LOGO_SRC, "Disclaimer")

    mail = await render("<b>Titel</b>", "Preview", "<script>alert(1)</script> [klik](javascript:alert(1))")

    assert "<script>" not in mail.html
    assert "<b>Titel</b>" not in mail.html
    assert 'href="javascript:' not in mail.html


@pytest.mark.anyio
async def test_smtp_mailer() -> None:
    mailer = SmtpMailer("meldingen@example.com", b"logo", "relay", 587, "user", "secret")

    with patch("meldingen.adapters.mail.smtp_mailer.aiosmtplib.send", new_callable=AsyncMock) as send:
        await mailer("melder@example.com", "Onderwerp", RENDERED_MAIL)

    message = send.call_args.args[0]
    assert message["From"] == "meldingen@example.com"
    assert message["To"] == "melder@example.com"
    assert message["Subject"] == "Onderwerp"
    assert send.call_args.kwargs["hostname"] == "relay"
    assert send.call_args.kwargs["port"] == 587
    assert send.call_args.kwargs["username"] == "user"
    assert send.call_args.kwargs["password"] == "secret"

    text_part, related_part = cast(list[EmailMessage], message.get_payload())
    assert text_part.get_content_type() == "text/plain"
    assert related_part.get_content_type() == "multipart/related"

    html_part, logo_part = cast(list[EmailMessage], related_part.get_payload())
    assert html_part.get_content_type() == "text/html"
    assert logo_part["Content-ID"] == f"<{LOGO_CONTENT_ID}>"
    assert logo_part.get_content_disposition() == "inline"


@pytest.mark.anyio
async def test_smtp_mailer_empty_credentials() -> None:
    mailer = SmtpMailer("meldingen@example.com", b"logo", "mailpit", 1025, "", "")

    with patch("meldingen.adapters.mail.smtp_mailer.aiosmtplib.send", new_callable=AsyncMock) as send:
        await mailer("melder@example.com", "Onderwerp", RENDERED_MAIL)

    assert send.call_args.kwargs["username"] is None
    assert send.call_args.kwargs["password"] is None


@pytest.mark.anyio
async def test_smtp_mailer_send_fails() -> None:
    mailer = SmtpMailer("meldingen@example.com", b"logo", "mailpit", 1025)

    with patch("meldingen.adapters.mail.smtp_mailer.aiosmtplib.send", new_callable=AsyncMock) as send:
        send.side_effect = aiosmtplib.SMTPConnectError("nope")

        with pytest.raises(MailException):
            await mailer("melder@example.com", "Onderwerp", RENDERED_MAIL)


@pytest.mark.anyio
async def test_send_confirmation_mail_task() -> None:
    renderer = AsyncMock(BaseMailRenderer, return_value=RENDERED_MAIL)
    mailer = AsyncMock(BaseMailer)
    melding = Mock(Melding, email="melder@example.com", public_id="ABC123", text="Kapotte stoeptegel")

    task = SendConfirmationMailTask(renderer, mailer, "Titel", "Preview {}", "Tekst {} {}", "Onderwerp {}")
    await task(melding)

    renderer.assert_awaited_once_with("Titel", "Preview ABC123", "Tekst Kapotte stoeptegel ABC123")
    mailer.assert_awaited_once_with("melder@example.com", "Onderwerp ABC123", RENDERED_MAIL)


@pytest.mark.anyio
async def test_send_confirmation_mail_task_without_email() -> None:
    mailer = AsyncMock(BaseMailer)
    melding = Mock(Melding, email=None, public_id="ABC123", text="Kapotte stoeptegel")

    task = SendConfirmationMailTask(AsyncMock(BaseMailRenderer), mailer, "Titel", "Preview", "Tekst", "Onderwerp")

    with pytest.raises(EmailAddressMissingException):
        await task(melding)

    mailer.assert_not_awaited()


@pytest.mark.anyio
async def test_send_confirmation_mail_task_send_fails() -> None:
    renderer = AsyncMock(BaseMailRenderer, return_value=RENDERED_MAIL)
    mailer = AsyncMock(BaseMailer, side_effect=MailException)
    melding = Mock(Melding, email="melder@example.com", public_id="ABC123", text="Kapotte stoeptegel")

    task = SendConfirmationMailTask(renderer, mailer, "Titel", "Preview", "Tekst", "Onderwerp")

    with pytest.raises(MailException):
        await task(melding)


@pytest.mark.anyio
async def test_send_completed_mail_task() -> None:
    renderer = AsyncMock(BaseMailRenderer, return_value=RENDERED_MAIL)
    mailer = AsyncMock(BaseMailer)
    melding = Mock(Melding, email="melder@example.com", public_id="ABC123")

    task = SendCompletedMailTask(renderer, mailer, "Titel", "Preview {}", "Onderwerp {}")
    await task(melding, "Wij hebben de tegel vervangen.")

    renderer.assert_awaited_once_with("Titel", "Preview ABC123", "Wij hebben de tegel vervangen.")
    mailer.assert_awaited_once_with("melder@example.com", "Onderwerp ABC123", RENDERED_MAIL)
