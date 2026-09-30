from email.message import EmailMessage
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import aiosmtplib
import pytest

from meldingen.adapters.mail.jinja_renderer import JinjaMailRenderer
from meldingen.adapters.mail.smtp_mailer import LOGO_CONTENT_ID, LOGO_SRC, SmtpMailer
from meldingen.config import settings
from meldingen.mail import (
    BaseMailer,
    BaseMailRenderer,
    EmailAddressMissingException,
    MailException,
    RenderedMail,
    SendCompletedMailTask,
    SendConfirmationMailTask,
)
from meldingen.models import Classification, Melding

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
    melding = Mock(
        Melding,
        email="melder@example.com",
        public_id="ABC123",
        text="Kapotte stoeptegel",
        classification=None,
    )

    task = SendConfirmationMailTask(
        renderer,
        mailer,
        title="Titel",
        preview_template="Preview {melding_id}",
        # Service level objective properties can also be used in the body template
        body_template="Tekst {melding_tekst} {melding_id}",
        subject_template="Onderwerp {melding_id}",
    )
    await task(melding)

    renderer.assert_awaited_once_with("Titel", "Preview ABC123", "Tekst Kapotte stoeptegel ABC123")
    mailer.assert_awaited_once_with("melder@example.com", "Onderwerp ABC123", RENDERED_MAIL)


@pytest.mark.anyio
class TestMailFormatting:
    def get_melding_with_service_belofte(
        self, service_belofte_text: str = "-", service_belofte_days: int = 5, service_belofte_type: str = "working_days"
    ) -> Melding:
        melding = Mock(
            Melding,
            email="melder@example.com",
            public_id="ABC123",
            text="Kapotte stoeptegel",
            classification=Mock(
                Classification,
                service_level_objective_text=service_belofte_text,
                service_level_objective_days=service_belofte_days,
                service_level_objective_day_type=service_belofte_type,
            ),
        )
        return melding

    def send_mail_task(
        self,
        body_template: str,
        subject_template: str = "Onderwerp {melding_id}",
        preview_template: str = "Preview {melding_id}",
        titel: str = "Titel",
    ) -> tuple[AsyncMock, SendConfirmationMailTask, AsyncMock]:
        renderer = AsyncMock(BaseMailRenderer, return_value=RENDERED_MAIL)
        mailer = AsyncMock(BaseMailer)
        task = SendConfirmationMailTask(
            renderer,
            mailer,
            title=titel,
            preview_template=preview_template,
            body_template=body_template,
            subject_template=subject_template,
        )
        return renderer, task, mailer

    async def test_send_mail_formatting_handles_unmatched_placeholders(self) -> None:
        renderer, task, mailer = self.send_mail_task(
            body_template="Tekst {melding_tekst} {melding_id} {unknown_tag}",
            subject_template="Onderwerp {unknown_tag}",
            preview_template="Preview {unknown_tag}",
            titel="Titel {unknown_tag}",
        )

        await task(self.get_melding_with_service_belofte())
        renderer.assert_awaited_once_with(
            "Titel {unknown_tag}",
            "Preview {unknown_tag}",
            "Tekst Kapotte stoeptegel ABC123 {unknown_tag}",
        )

        mailer.assert_awaited_once_with("melder@example.com", "Onderwerp {unknown_tag}", RENDERED_MAIL)

    async def test_send_mail_service_belofte_default(self) -> None:
        renderer, task, _mailer = self.send_mail_task(
            "Tekst {melding_tekst} {melding_id} {melding_categorie_service_belofte_tekst}"
        )

        await task(self.get_melding_with_service_belofte())
        renderer.assert_awaited_once_with(
            "Titel",
            "Preview ABC123",
            "Tekst Kapotte stoeptegel ABC123 We laten u binnen 5 werkdagen weten wat we hebben gedaan. En anders hoort u wanneer wij uw melding kunnen oppakken",
        )

    async def test_send_mail_service_belofte_all_props(self) -> None:
        renderer, task, _mailer = self.send_mail_task(
            "Tekst {melding_tekst} {melding_id} 1. Wij nemen binnen {melding_categorie_service_belofte_dagen} {melding_categorie_service_belofte_dag_type} contact met u op. 2. {melding_categorie_service_belofte_tekst}"
        )

        await task(self.get_melding_with_service_belofte(service_belofte_days=4, service_belofte_type="working_days"))
        renderer.assert_awaited_once_with(
            "Titel",
            "Preview ABC123",
            "Tekst Kapotte stoeptegel ABC123 1. Wij nemen binnen 4 werkdagen contact met u op. 2. We laten u binnen 4 werkdagen weten wat we hebben gedaan. En anders hoort u wanneer wij uw melding kunnen oppakken",
        )

    async def test_send_mail_service_belofte_custom(self) -> None:
        renderer, task, _mailer = self.send_mail_task(
            "Tekst {melding_tekst} {melding_id} Wij nemen binnen {melding_categorie_service_belofte_dagen} {melding_categorie_service_belofte_dag_type} contact met u op."
        )

        await task(self.get_melding_with_service_belofte(service_belofte_days=4, service_belofte_type="working_days"))
        renderer.assert_awaited_once_with(
            "Titel",
            "Preview ABC123",
            "Tekst Kapotte stoeptegel ABC123 Wij nemen binnen 4 werkdagen contact met u op.",
        )

    async def test_send_mail_service_belofte_default_with_custom_days_and_type(self) -> None:
        renderer, task, _mailer = self.send_mail_task(
            "Tekst {melding_tekst} {melding_id} {melding_categorie_service_belofte_tekst}"
        )

        await task(self.get_melding_with_service_belofte(service_belofte_days=10, service_belofte_type="calendar_days"))
        renderer.assert_awaited_once_with(
            "Titel",
            "Preview ABC123",
            "Tekst Kapotte stoeptegel ABC123 We laten u binnen 10 dagen weten wat we hebben gedaan. En anders hoort u wanneer wij uw melding kunnen oppakken",
        )

    async def test_send_mail_service_belofte_custom_ignoring_days_and_type_settings(self) -> None:
        renderer, task, _mailer = self.send_mail_task(
            "Tekst {melding_tekst} {melding_id} {melding_categorie_service_belofte_tekst}"
        )

        await task(self.get_melding_with_service_belofte(service_belofte_text="We houden u op de hoogte via e-mail."))
        renderer.assert_awaited_once_with(
            "Titel",
            "Preview ABC123",
            "Tekst Kapotte stoeptegel ABC123 We houden u op de hoogte via e-mail.",
        )

    async def test_send_mail_without_service_belofte(self) -> None:
        renderer, task, _mailer = self.send_mail_task("Tekst {melding_tekst} {melding_id}")

        await task(self.get_melding_with_service_belofte(service_belofte_text="We houden u op de hoogte via e-mail."))
        renderer.assert_awaited_once_with(
            "Titel",
            "Preview ABC123",
            "Tekst Kapotte stoeptegel ABC123",
        )

    async def test_send_mail_with_empty_service_belofte(self) -> None:
        renderer, task, _mailer = self.send_mail_task(
            "Tekst {melding_tekst} {melding_id} {melding_categorie_service_belofte_tekst}"
        )

        await task(self.get_melding_with_service_belofte(service_belofte_text=""))
        renderer.assert_awaited_once_with(
            "Titel",
            "Preview ABC123",
            "Tekst Kapotte stoeptegel ABC123",
        )

    async def test_send_mail_with_default_confirmation_mail_without_markdown_parsing(self) -> None:
        renderer, task, _mailer = self.send_mail_task(settings.mail_melding_confirmation_body_text)

        await task(self.get_melding_with_service_belofte())
        renderer.assert_awaited_once_with(
            "Titel",
            "Preview ABC123",
            "U heeft ons het volgende laten weten:\n\n*Kapotte stoeptegel*\n\n### Wat we doen met uw melding\nWe onderzoeken uw melding en kijken wat we kunnen oppakken. We laten u binnen 5 werkdagen weten wat we hebben gedaan. En anders hoort u wanneer wij uw melding kunnen oppakken We houden u op de hoogte via e-mail.\n\n### Meer weten?\nHeeft u nog een vraag over uw melding? Bel met het telefoonnummer [14 020](tel:14020), maandag tot en met vrijdag\nvan 08.00 tot 18.00. Geef dan ook het nummer van uw melding door: ABC123.\n\nMet vriendelijke groet,\n\nGemeente Amsterdam\n\n*Dit bericht is automatisch gemaakt met de informatie uit uw melding.*",
        )


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

    task = SendCompletedMailTask(renderer, mailer, "Titel", "Preview {melding_id}", "Onderwerp {melding_id}")
    await task(melding, "Wij hebben de tegel vervangen.")

    renderer.assert_awaited_once_with("Titel", "Preview ABC123", "Wij hebben de tegel vervangen.")
    mailer.assert_awaited_once_with("melder@example.com", "Onderwerp ABC123", RENDERED_MAIL)
