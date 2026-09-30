import logging
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Concatenate

from fastapi import BackgroundTasks
from meldingen_core.mail import BaseMeldingCompleteMailer, BaseMeldingConfirmationMailer

from meldingen.mail_data_templates import MailDataTemplate, MailFormatted
from meldingen.models import Melding

logger = logging.getLogger(__name__)


class MailException(Exception): ...


class EmailAddressMissingException(MailException): ...


@dataclass(frozen=True)
class RenderedMail:
    html: str
    text: str


class BaseMailRenderer(metaclass=ABCMeta):
    @abstractmethod
    async def __call__(self, title: str, preview_text: str, body_text: str) -> RenderedMail: ...


class BaseMailer(metaclass=ABCMeta):
    @abstractmethod
    async def __call__(self, to: str, subject: str, mail: RenderedMail) -> None: ...


class SendMailTask[T: Melding, **P]:
    _render: BaseMailRenderer
    _send_mail: BaseMailer
    _format_mail_data: MailDataTemplate[Concatenate[T, P]]

    def __init__(
        self, renderer: BaseMailRenderer, mailer: BaseMailer, mail_data_template: MailDataTemplate[Concatenate[T, P]]
    ) -> None:
        self._render = renderer
        self._send_mail = mailer
        self._format_mail_data = mail_data_template

    async def _send(self, melding: T, email: MailFormatted) -> None:
        if melding.email is None:
            raise EmailAddressMissingException("Email address missing!")

        mail = await self._render(email.title, email.preview_text, email.body)

        try:
            await self._send_mail(melding.email, email.subject, mail)
        except MailException:
            # Runs as a background task, so without logging this failure would go unnoticed
            logger.exception("Failed to send mail for melding %s", melding.public_id)
            raise

    async def __call__(self, melding: T, *args: P.args, **kwargs: P.kwargs) -> None:
        await self._send(melding, self._format_mail_data(melding, *args, **kwargs))


class SendConfirmationMailTask(SendMailTask[Melding, []]):
    async def __call__(self, melding: Melding) -> None:
        await self._send(melding, self._format_mail_data(melding))


class SendCompletedMailTask(SendMailTask[Melding, [str]]):
    async def __call__(self, melding: Melding, body_text: str) -> None:
        await super().__call__(melding, body_text)


class BackgroundTaskMeldingMailer[T: Melding, **P]:
    _background_task_manager: BackgroundTasks
    _send_mail_task: SendMailTask[T, P]

    def __init__(self, background_task_manager: BackgroundTasks, send_mail_task: SendMailTask[T, P]) -> None:
        self._background_task_manager = background_task_manager
        self._send_mail_task = send_mail_task


class BackgroundTaskMeldingConfirmationMailer(
    BackgroundTaskMeldingMailer[Melding, []], BaseMeldingConfirmationMailer[Melding]
):
    async def __call__(self, melding: Melding) -> None:
        self._background_task_manager.add_task(self._send_mail_task, melding)


class BackgroundTaskMeldingCompleteMailer(
    BackgroundTaskMeldingMailer[Melding, [str]], BaseMeldingCompleteMailer[Melding]
):
    async def __call__(self, melding: Melding, body_text: str) -> None:
        self._background_task_manager.add_task(self._send_mail_task, melding, body_text)
