import enum
from typing import Any, Required, cast

from meldingen.config import settings
from meldingen.models import Melding, ServiceLevelObjectiveDayType, ServiceLevelObjectiveDayTypeReadable
from meldingen.utils import format_melding_address, format_readable_date_time

LOCATION_NOT_SPECIFIED = "Locatie is gepind op de kaart"


class MailFormatted:
    title: str
    preview_text: str
    body: str
    subject: str


MailDataTemplateVars = dict[str, Any]


class MailDataTemplate[**P]:
    title_template: Required[str] = ""
    preview_template: Required[str] = ""
    body_template: Required[str] = ""
    subject_template: Required[str] = ""

    @staticmethod
    def format_template(template: str, template_vars: MailDataTemplateVars) -> str:
        return template.format(**template_vars)

    def format(self, template_vars: MailDataTemplateVars) -> MailFormatted:
        formatted_mail = MailFormatted()
        formatted_mail.title = self.format_template(self.title_template, template_vars)
        formatted_mail.preview_text = self.format_template(self.preview_template, template_vars)
        formatted_mail.subject = self.format_template(self.subject_template, template_vars)
        formatted_mail.body = self.format_template(self.body_template, template_vars)
        return formatted_mail

    def __init__(
        self,
        title_template: str | None = None,
        preview_template: str | None = None,
        body_template: str | None = None,
        subject_template: str | None = None,
    ) -> None:
        self.title_template = title_template or self.title_template
        self.preview_template = preview_template or self.preview_template
        self.body_template = body_template or self.body_template
        self.subject_template = subject_template or self.subject_template

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MailFormatted:
        args_dict = {str(f"_{i}"): arg for i, arg in enumerate(args)}
        template_vars = dict(**args_dict, **kwargs)
        return self.format(template_vars)


class MeldingMailDataTemplate[**P](MailDataTemplate[P]):
    title_template = "Uw melding"
    subject_template = "Uw melding met nummer: {melding_id}"
    preview_template = "Uw melding met nummer: {melding_id}"
    body_template = "Uw melding met nummer: {melding_id} gedaan op {melding_datum_tijd}"

    def get_melding_template_vars(
        self, melding: Melding, extra_template_vars: MailDataTemplateVars | None = None
    ) -> MailDataTemplateVars:
        melding_template_vars = {
            "melding_id": melding.public_id,
            "melding_datum_tijd": format_readable_date_time(melding.created_at),
        }

        template_vars = {**melding_template_vars, **(extra_template_vars or {})}

        return cast(MailDataTemplateVars, template_vars)


class MailDataTemplateWithLocation[**P](MeldingMailDataTemplate[P]):
    def get_location(self, melding: Melding) -> str:
        address = format_melding_address(melding)

        return address or LOCATION_NOT_SPECIFIED


class MeldingConfirmationMailData(MailDataTemplateWithLocation[[Melding]]):
    title_template = settings.mail_melding_confirmation_title
    preview_template = settings.mail_melding_confirmation_preview_text
    body_template = settings.mail_melding_confirmation_body_text
    subject_template = settings.mail_melding_confirmation_subject

    def get_service_level_objective_day_type(self, melding: Melding) -> str | None:
        day_type = cast(
            ServiceLevelObjectiveDayType,
            getattr(melding.classification, "service_level_objective_day_type", None),
        )
        return ServiceLevelObjectiveDayTypeReadable.get(day_type)

    def get_service_level_objective_text(self, melding: Melding) -> str | None:
        text = getattr(melding.classification, "service_level_objective_text", None)
        return (
            text.format(
                melding_categorie_service_belofte_dag_type=self.get_service_level_objective_day_type(melding),
                melding_categorie_service_belofte_dagen=getattr(
                    melding.classification, "service_level_objective_days", None
                ),
            )
            if text
            else None
        )

    def __call__(self, melding: Melding) -> MailFormatted:
        template_vars = {
            "melding_tekst": melding.text,
            "melding_plaats": self.get_location(melding),
            "melding_categorie_service_belofte_tekst": self.get_service_level_objective_text(melding),
            "melding_categorie_service_belofte_dag_type": self.get_service_level_objective_day_type(melding),
            "melding_categorie_service_belofte_dagen": getattr(
                melding.classification, "service_level_objective_days", None
            ),
        }
        return self.format(self.get_melding_template_vars(melding, template_vars))


class MeldingCompleteMailData(MeldingMailDataTemplate[[Melding, str]]):
    title_template = settings.mail_melding_completed_title
    preview_template = settings.mail_melding_completed_preview_text
    body_template = "{user_supplied_body_text}"
    subject_template = settings.mail_melding_completed_subject

    def __call__(self, melding: Melding, user_supplied_body_text: str) -> MailFormatted:
        template_vars: MailDataTemplateVars = {
            "user_supplied_body_text": user_supplied_body_text,
        }
        return self.format(self.get_melding_template_vars(melding, template_vars))


class TemplateID(enum.StrEnum):
    melding_confirmation = "melding_confirmation"
    melding_complete = "melding_complete"


mail_data_templates: dict[TemplateID, type[MailDataTemplate[...]]] = {
    TemplateID.melding_confirmation: MeldingConfirmationMailData,
    TemplateID.melding_complete: MeldingCompleteMailData,
}


# Function to retrieve the mail template class based on the template ID
# Will be an actual asynchronous function to retrieve the mail template from the database.
async def get_mail_data_template(name: TemplateID) -> type[MailDataTemplate[...]] | None:
    return mail_data_templates.get(name)
