import logging
from email.message import EmailMessage
from typing import Final, cast

import aiosmtplib

from meldingen.mail import BaseMailer, MailException, RenderedMail

logger = logging.getLogger(__name__)

LOGO_CONTENT_ID: Final[str] = "logo@amsterdam.nl"
LOGO_SRC: Final[str] = f"cid:{LOGO_CONTENT_ID}"


class SmtpMailer(BaseMailer):
    """Sends an already rendered mail over SMTP.

    The logo travels with the message as a related part rather than as a link, because mail
    clients block remote images by default and the recipient would see a gap where the logo
    should be.
    """

    _sender: str
    _logo: bytes
    _hostname: str
    _port: int
    _username: str | None
    _password: str | None
    _start_tls: bool
    _use_tls: bool
    _timeout: float

    def __init__(
        self,
        sender: str,
        logo: bytes,
        hostname: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        start_tls: bool = True,
        use_tls: bool = False,
        timeout: float = 10.0,
    ) -> None:
        self._sender = sender
        self._logo = logo
        self._hostname = hostname
        self._port = port
        # An unset secret arrives as an empty string rather than as None, and an empty username
        # would make us attempt AUTH against a relay that does not want it.
        self._username = username or None
        self._password = password or None
        self._start_tls = start_tls
        self._use_tls = use_tls
        self._timeout = timeout

    async def __call__(self, to: str, subject: str, mail: RenderedMail) -> None:
        message = self._build_message(to, subject, mail)

        try:
            await aiosmtplib.send(
                message,
                hostname=self._hostname,
                port=self._port,
                username=self._username,
                password=self._password,
                start_tls=self._start_tls,
                use_tls=self._use_tls,
                timeout=self._timeout,
            )
        except (aiosmtplib.SMTPException, OSError) as e:
            raise MailException("Failed to send mail!") from e

    def _build_message(self, to: str, subject: str, mail: RenderedMail) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = to
        message["Subject"] = subject

        message.set_content(mail.text)
        message.add_alternative(mail.html, subtype="html")

        # add_related has to land on the html part, not on the message, or the alternative
        # structure collapses and clients stop offering the plain text version.
        # The cast is because typeshed types get_payload as a broad union.
        html_part = cast(EmailMessage, message.get_payload(-1))
        html_part.add_related(
            self._logo,
            maintype="image",
            subtype="png",
            cid=f"<{LOGO_CONTENT_ID}>",
            filename="amsterdam-logo.png",
            # Without this the filename alone makes it "Content-Disposition: attachment", and the
            # logo shows up as a paperclip next to the mail instead of inside it.
            disposition="inline",
        )

        return message
