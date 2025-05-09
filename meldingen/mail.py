from abc import ABCMeta, abstractmethod

from amsterdam_mail_service_client.api.default_api import DefaultApi
from amsterdam_mail_service_client.exceptions import ApiException
from amsterdam_mail_service_client.models.send_request import SendRequest
from meldingen_core.mail import BaseMeldingConfirmationMailer

from meldingen.models import Melding


class MailException(Exception): ...


class EmailAddressMissingException(MailException): ...


class BaseMailer(metaclass=ABCMeta):
    @abstractmethod
    async def __call__(
        self, title: str, preview_text: str, body_text: str, _from: str, to: str, subject: str
    ) -> None: ...


class AmsterdamMailServiceMailer(BaseMailer):
    _api: DefaultApi

    def __init__(self, api: DefaultApi):
        self._api = api

    async def __call__(self, title: str, preview_text: str, body_text: str, _from: str, to: str, subject: str) -> None:
        request = SendRequest(
            title=title,
            preview_text=preview_text,
            body_text=body_text,
            var_from=_from,
            to=to,
            subject=subject,
        )

        try:
            await self._api.send(request)
        except ApiException as e:
            raise MailException("Failed to send mail!") from e


class AmsterdamMailServiceMeldingConfirmationMailer(BaseMeldingConfirmationMailer[Melding]):
    _send_mail: BaseMailer
    _title_template: str
    _preview_template: str
    _body_template: str
    _from: str
    _subject_template: str

    def __init__(
        self,
        mailer: BaseMailer,
        title_template: str,
        preview_template: str,
        body_template: str,
        _from: str,
        subject_template: str,
    ) -> None:
        self._send_mail = mailer
        self._title_template = title_template
        self._preview_template = preview_template
        self._body_template = body_template
        self._from = _from
        self._subject_template = subject_template

    async def __call__(self, melding: Melding) -> None:
        if melding.email is None:
            raise EmailAddressMissingException("Email address missing!")

        title = self._title_template
        preview_text = self._preview_template.format(melding.public_id)
        body_text = self._body_template.format(melding.text, melding.public_id)
        subject = self._subject_template.format(melding.public_id)

        await self._send_mail(title, preview_text, body_text, self._from, melding.email, subject)
