from email.message import EmailMessage
from typing import cast

import aiosmtplib

from meldingen.mail import BaseMailer, MailException, RenderedMail

LOGO_CONTENT_ID = "logo@amsterdam.nl"
LOGO_SRC = f"cid:{LOGO_CONTENT_ID}"


class SmtpMailer(BaseMailer):
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
        # Unset secrets come in as empty strings
        self._username = username or None
        self._password = password or None
        self._start_tls = start_tls
        self._use_tls = use_tls
        self._timeout = timeout

    async def __call__(self, to: str, subject: str, mail: RenderedMail) -> None:
        try:
            await aiosmtplib.send(
                self._build_message(to, subject, mail),
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

        # The logo has to be related to the html part, not to the whole message
        html_part = cast(EmailMessage, message.get_payload(-1))
        html_part.add_related(
            self._logo,
            maintype="image",
            subtype="png",
            cid=f"<{LOGO_CONTENT_ID}>",
            filename="amsterdam-logo.png",
            disposition="inline",  # otherwise it shows up as an attachment
        )

        return message
