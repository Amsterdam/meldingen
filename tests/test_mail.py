import pytest

from meldingen.mail import BaseMailer, EmailAddressMissingException, SendConfirmationMailTask
from meldingen.models import Melding

BODY_TEMPLATE = """U heeft ons het volgende laten weten:

*{}*

Bel met het telefoonnummer [14 020](tel:14020) en geef het nummer van uw melding door: {}."""


class MailerSpy(BaseMailer):
    body_text: str

    async def __call__(self, title: str, preview_text: str, body_text: str, _from: str, to: str, subject: str) -> None:
        self.body_text = body_text


def create_task(mailer: BaseMailer) -> SendConfirmationMailTask:
    return SendConfirmationMailTask(
        mailer,
        title_template="Uw melding",
        preview_template="Uw melding: {}",
        body_template=BODY_TEMPLATE,
        _from="meldingen@example.com",
        subject_template="Uw melding {}: melding ontvangen",
    )


@pytest.mark.anyio
async def test_confirmation_mail_does_not_let_the_reporter_add_a_link() -> None:
    mailer = MailerSpy()
    melding = Melding("Bel mij op [dit nummer](tel:0900-1234), <javascript:alert(1)>")
    melding.email = "melder@example.com"

    await create_task(mailer)(melding)

    # The reporter's text is quoted back in full, but none of it is markup any more...
    assert "Bel mij op \\[dit nummer\\](tel:0900-1234), &lt;javascript:alert(1)&gt;" in mailer.body_text
    # ...while the links the template itself provides are untouched.
    assert "[14 020](tel:14020)" in mailer.body_text


@pytest.mark.anyio
async def test_confirmation_mail_requires_an_email_address() -> None:
    melding = Melding("Er ligt afval op de stoep.")

    with pytest.raises(EmailAddressMissingException):
        await create_task(MailerSpy())(melding)
