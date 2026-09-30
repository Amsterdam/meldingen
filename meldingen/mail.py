import logging
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

from fastapi import BackgroundTasks
from meldingen_core.mail import BaseMeldingCompleteMailer, BaseMeldingConfirmationMailer

from meldingen.config import settings
from meldingen.models import (
    SERVICE_LEVEL_OBJECTIVE_DAY_TYPE_DEFAULT,
    SERVICE_LEVEL_OBJECTIVE_DAYS_DEFAULT,
    SERVICE_LEVEL_OBJECTIVE_TEXT_DEFAULT,
    Melding,
    ServiceLevelObjectiveDayTypeReadable,
)
from meldingen.utils import format_safe

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

        mail = await self._render(
            format_safe(self._title, {"melding_id": melding.public_id}),
            format_safe(self._preview_template, {"melding_id": melding.public_id}),
            body_text,
        )

        try:
            await self._send_mail(
                melding.email, format_safe(self._subject_template, {"melding_id": melding.public_id}), mail
            )
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

    def _get_service_level_objective_props(self, melding: Melding):
        service_level_objective_text = (
            melding.classification.service_level_objective_text
            if melding.classification
            and melding.classification.service_level_objective_text != SERVICE_LEVEL_OBJECTIVE_TEXT_DEFAULT
            else settings.mail_melding_confirmation_service_belofte_default
        )
        service_level_objective_days = (
            melding.classification.service_level_objective_days
            if melding.classification
            else SERVICE_LEVEL_OBJECTIVE_DAYS_DEFAULT
        )
        service_level_objective_day_type = (
            ServiceLevelObjectiveDayTypeReadable[melding.classification.service_level_objective_day_type]
            if melding.classification
            else ServiceLevelObjectiveDayTypeReadable[SERVICE_LEVEL_OBJECTIVE_DAY_TYPE_DEFAULT]
        )
        return service_level_objective_text, service_level_objective_days, service_level_objective_day_type

    async def __call__(self, melding: Melding) -> None:
        service_level_objective_text, service_level_objective_days, service_level_objective_day_type = (
            self._get_service_level_objective_props(melding)
        )
        classification_service_objective_text_formatted = service_level_objective_text.format(
            melding_categorie_service_belofte_dagen=service_level_objective_days,
            melding_categorie_service_belofte_dag_type=service_level_objective_day_type,
        )
        await self._send(
            melding,
            format_safe(
                self._body_template,
                {
                    "melding_tekst": melding.text,
                    "melding_id": melding.public_id,
                    "melding_categorie_service_belofte_dagen": service_level_objective_days,
                    "melding_categorie_service_belofte_dag_type": service_level_objective_day_type,
                    "melding_categorie_service_belofte_tekst": classification_service_objective_text_formatted,
                },
            ).strip(),
        )


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
