from unittest.mock import Mock

import pytest
from meldingen_core.models import Classification, Melding

from meldingen.mail_data_templates import MailDataTemplate, MeldingConfirmationMailData
from meldingen.utils import utc_datetime


@pytest.mark.anyio
async def test_melding_template():
    format_mail_data = MailDataTemplate(
        title_template="Titel {foo}",
        preview_template="Preview {_0}",
        body_template="{_0} - {foo}",
        subject_template="{_0} {foo} {_0}",
    )

    mail = format_mail_data("foo_value", foo="bar")

    assert mail.body == "foo_value - bar"
    assert mail.title == "Titel bar"
    assert mail.preview_text == "Preview foo_value"
    assert mail.subject == "foo_value bar foo_value"


@pytest.mark.anyio
async def test_melding_confirmation_mail_data_template():
    body_template = "{melding_id} - {melding_categorie_service_belofte_dagen} - {melding_categorie_service_belofte_dag_type} - {melding_categorie_service_belofte_tekst} - {melding_tekst} - {melding_id} - {melding_datum_tijd} - {melding_plaats} - {melding_id}"
    format_mail_data = MeldingConfirmationMailData(
        title_template="Titel",
        preview_template="Preview {melding_id}",
        body_template=body_template,
        subject_template="Onderwerp {melding_id}",
    )

    melding = Mock(
        Melding,
        email="melder@example.com",
        public_id="ABC123",
        text="Kapotte stoeptegel",
        created_at=utc_datetime(2026, 10, 1, 21, 35),
        city="Amsterdam",
        street="Amstel",
        house_number=1,
        house_number_addition="A",
        postal_code="1017 AB",
        classification=Classification(
            name="Categorie Naam",
            service_level_objective_days=3,
            service_level_objective_day_type="working_days",
            service_level_objective_text="Wij lossen uw probleem binnen {melding_categorie_service_belofte_dagen} {melding_categorie_service_belofte_dag_type} op.",
        ),
    )

    mail = format_mail_data(melding)

    assert mail.title == "Titel"
    assert mail.preview_text == "Preview ABC123"
    assert (
        mail.body
        == "ABC123 - 3 - werkdagen - Wij lossen uw probleem binnen 3 werkdagen op. - Kapotte stoeptegel - ABC123 - 1 oktober 2026 om 21:35 uur - Amstel 1-A, 1017 AB Amsterdam - ABC123"
    )
    assert mail.subject == "Onderwerp ABC123"


@pytest.mark.anyio
async def test_melding_completed_mail_data_template():
    pass


@pytest.mark.anyio
async def test_melding_template_missing_template_keys():
    pass


@pytest.mark.anyio
async def test_melding_template_missing_address():
    pass
