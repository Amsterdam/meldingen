from meldingen_core.statemachine import MeldingStates

from meldingen.factories import AnswerFactory, AttachmentFactory, NoteFactory
from meldingen.models import Attachment, Melding, Note, Question, TextAnswer, User
from meldingen.schemas.input import TextAnswerInput


def test_attachment_factory() -> None:
    factory = AttachmentFactory()
    attachment = factory("original_filename.txt", Melding("melding text"), "image/png")

    assert isinstance(attachment, Attachment)


def test_note_factory() -> None:
    factory = NoteFactory()
    melding = Melding("melding text")
    user = User(username="behandelaar", email="behandelaar@example.com")

    note = factory("a note", melding, user)

    assert isinstance(note, Note)
    assert note.text == "a note"
    assert note.melding is melding
    assert note.user is user


def test_answer_factory_populates_snapshot_fields() -> None:
    factory = AnswerFactory()
    melding = Melding(text="t", state=MeldingStates.CLASSIFIED)
    question = Question(text="What is your name?")
    answer_input = TextAnswerInput(type="text", text="Alice")

    answer = factory(
        answer_input=answer_input,
        melding=melding,
        question=question,
        component_position=2,
        panel_position=1,
    )

    assert isinstance(answer, TextAnswer)
    assert answer.original_question_text == "What is your name?"
    assert answer.component_position == 2
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
        component_position=1,
        panel_position=None,
    )

    assert answer.panel_position is None
