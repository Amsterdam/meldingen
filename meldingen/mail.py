import logging
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

from fastapi import BackgroundTasks
from meldingen_core.mail import BaseMeldingCompleteMailer, BaseMeldingConfirmationMailer

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


class SendMailTask:
    _render: BaseMailRenderer
    _send_mail: BaseMailer
    _title: str
    _preview_template: str
    _subject_template: str

    def __init__(
        self,
        renderer: BaseMailRenderer,
        mailer: BaseMailer,
        title: str,
        preview_template: str,
        subject_template: str,
    ) -> None:
        self._render = renderer
        self._send_mail = mailer
        self._title = title
        self._preview_template = preview_template
        self._subject_template = subject_template

    async def _send(self, melding: Melding, body_text: str) -> None:
        if melding.email is None:
            raise EmailAddressMissingException("Email address missing!")

        mail = await self._render(self._title, self._preview_template.format(melding.public_id), body_text)

        try:
            await self._send_mail(melding.email, self._subject_template.format(melding.public_id), mail)
        except MailException:
            # Runs as a background task, so without logging this failure would go unnoticed
            logger.exception("Failed to send mail for melding %s", melding.public_id)
            raise


class SendConfirmationMailTask(SendMailTask):
    _body_template: str

    def __init__(
        self,
        renderer: BaseMailRenderer,
        mailer: BaseMailer,
        title: str,
        preview_template: str,
        body_template: str,
        subject_template: str,
    ) -> None:
        super().__init__(renderer, mailer, title, preview_template, subject_template)
        self._body_template = body_template

    async def __call__(self, melding: Melding) -> None:
        await self._send(melding, self._body_template.format(melding.text, melding.public_id))


class SendCompletedMailTask(SendMailTask):
    async def __call__(self, melding: Melding, body_text: str) -> None:
        await self._send(melding, body_text)


class BackgroundTaskMeldingConfirmationMailer(BaseMeldingConfirmationMailer[Melding]):
    _background_task_manager: BackgroundTasks
    _send_confirmation_mail_task: SendConfirmationMailTask

    def __init__(
        self, background_task_manager: BackgroundTasks, send_confirmation_mail_task: SendConfirmationMailTask
    ) -> None:
        self._background_task_manager = background_task_manager
        self._send_confirmation_mail_task = send_confirmation_mail_task

    async def __call__(self, melding: Melding) -> None:
        self._background_task_manager.add_task(self._send_confirmation_mail_task, melding=melding)


class BackgroundTaskMeldingCompleteMailer(BaseMeldingCompleteMailer[Melding]):
    _background_task_manager: BackgroundTasks
    _send_completed_mail_task: SendCompletedMailTask

    def __init__(
        self, background_task_manager: BackgroundTasks, send_completed_mail_task: SendCompletedMailTask
    ) -> None:
        self._background_task_manager = background_task_manager
        self._send_completed_mail_task = send_completed_mail_task

    async def __call__(self, melding: Melding, mail_text: str) -> None:
        self._background_task_manager.add_task(self._send_completed_mail_task, melding=melding, body_text=mail_text)
