from meldingen_core.statemachine import MeldingStates

from meldingen.factories import AnswerFactory, AttachmentFactory
from meldingen.models import Attachment, Melding, Question, TextAnswer
from meldingen.schemas.input import TextAnswerInput


def test_attachment_factory() -> None:
    factory = AttachmentFactory()
    attachment = factory("original_filename.txt", Melding("melding text"), "image/png")

    assert isinstance(attachment, Attachment)


def test_answer_factory_populates_snapshot_fields() -> None:
    factory = AnswerFactory()
    melding = Melding(text="t", state=MeldingStates.CLASSIFIED)
    question = Question(text="What is your name?")
    answer_input = TextAnswerInput(type="text", text="Alice")

    answer = factory(
        answer_input=answer_input,
        melding=melding,
        question=question,
        component_key="firstName",
        component_position=2,
        panel_id=17,
        panel_position=1,
    )

    assert isinstance(answer, TextAnswer)
    assert answer.original_question_text == "What is your name?"
    assert answer.component_key == "firstName"
    assert answer.component_position == 2
    assert answer.panel_id == 17
    assert answer.panel_position == 1


def test_answer_factory_accepts_null_panel() -> None:
    factory = AnswerFactory()
    melding = Melding(text="t", state=MeldingStates.CLASSIFIED)
    question = Question(text="Q")
    answer_input = TextAnswerInput(type="text", text="x")

    answer = factory(
        answer_input=answer_input,
        melding=melding,
        question=question,
        component_key="topLevel",
        component_position=1,
        panel_id=None,
        panel_position=None,
    )

    assert answer.panel_id is None
    assert answer.panel_position is None
