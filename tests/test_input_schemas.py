from typing import ClassVar

import pytest
from pydantic import ValidationError

from meldingen.models import AnswerTypeEnum
from meldingen.schemas.input import (
    ClassificationUpdateInput,
    NoteInput,
    RejectExplicitNullsUpdateInput,
    TimeAnswerInput,
    _markdown_to_plain_text,
)


class _AllFieldsNullRejectUpdateInput(RejectExplicitNullsUpdateInput):
    name: str | None = None
    count: int | None = None


class _ScopedNullRejectUpdateInput(RejectExplicitNullsUpdateInput):
    reject_explicit_null_fields: ClassVar[set[str]] = {"name"}
    name: str | None = None
    count: int | None = None


def test_note_input_strips_whitespace() -> None:
    assert NoteInput(text="  hello  ").text == "hello"


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_note_input_rejects_empty_text(text: str) -> None:
    with pytest.raises(ValidationError):
        NoteInput(text=text)


def test_note_input_rejects_plain_text_over_limit() -> None:
    with pytest.raises(ValidationError):
        NoteInput(text="a" * 1001)


def test_note_input_accepts_markdown_over_limit_with_plain_text_under_limit() -> None:
    # The raw markdown exceeds 1000 characters, but the rendered plain text does not.
    text = "**" + ("a" * 999) + "**"
    assert len(text) > 1000

    assert NoteInput(text=text).text == text


def test_note_input_does_not_count_paragraph_breaks_towards_the_limit() -> None:
    # A real note pasted by a user: 12 paragraphs whose combined visible content is 995 characters.
    # Rendered to plain text it becomes 1006 characters (995 + 11 single newlines between the
    # paragraphs), but those paragraph breaks must not count towards the limit, so the note is valid.
    paragraphs = [
        "Nieuwe test",
        "Bug: Als je wordt uitgelogd kom je niet automatisch terug op de pagina waar je was",
        "Bug: Wanneer was het? in back office werkt nog niet",
        "Bug: /locatie laat maar 4 assets zien als je er 5 kiest. Reproduceren, klokken?",
        "Bug: leeggooien aanvullende tekstvraag werkt niet",
        (
            "Bug: als je in back office melding aanmaakt met aanvullende vragen, dan in summary naar "
            "primary form gaan, dan aanpast naar cat zonder aanvullende vragen, dan krijg je state "
            "transition error?"
        ),
        (
            "Bug: vanuit back office begin je wat makkelijker een nieuwe melding dan in MF. Gebeurt dan "
            "iets sneller dat je een nieuwe melding hebt, maar address cookie nog gevuld is van een "
            "niet-afgemaakte melding"
        ),
        "Bug: Als je wordt uitgelogd kom je niet automatisch terug op de pagina waar je was",
        "Bug: Wanneer was het? in back office werkt nog niet",
        "Bug: /locatie laat maar 4 assets zien als je er 5 kiest. Reproduceren, klokken?",
        "Bug: leeggooien aanvullende tekstvraag werkt niet",
        "Bug: als je in back office melding aanmaakt met aanvullende vragalalal",
    ]
    text = "\n\n".join(paragraphs)
    # The user's visible content is under the limit...
    assert len("".join(paragraphs)) == 995
    # ...even though counting the paragraph breaks would push the rendered plain text over it.
    assert len(_markdown_to_plain_text(text)) > 1000

    assert NoteInput(text=text).text == text


def test_reject_explicit_nulls_update_input_rejects_null_on_any_field_by_default() -> None:
    with pytest.raises(ValidationError):
        _AllFieldsNullRejectUpdateInput(name=None)


def test_reject_explicit_nulls_update_input_allows_omitted_fields() -> None:
    obj = _AllFieldsNullRejectUpdateInput()
    assert obj.model_dump(exclude_unset=True) == {}


def test_reject_explicit_null_fields_raises_for_configured_null_field() -> None:
    with pytest.raises(ValidationError, match=r"Value error, Null is not allowed for update fields name"):
        _ScopedNullRejectUpdateInput(name=None, count=None)


def test_classification_update_input_rejects_null_on_scoped_fields() -> None:
    with pytest.raises(ValidationError):
        ClassificationUpdateInput(name=None)


def test_classification_update_input_allows_null_on_unscoped_fields() -> None:
    obj = ClassificationUpdateInput(instructions=None, asset_type=None)
    assert obj.instructions is None
    assert obj.asset_type is None


def test_note_input_rejects_visible_text_over_limit_even_with_line_breaks() -> None:
    # 1001 visible characters split across two paragraphs is genuinely too long, regardless of the
    # line break between them.
    text = ("a" * 500) + "\n\n" + ("a" * 501)
    with pytest.raises(ValidationError):
        NoteInput(text=text)


@pytest.mark.parametrize(
    "time_str",
    [
        "00:00",
        "01:23",
        "09:59",
        "10:00",
        "12:34",
        "15:45",
        "20:15",
        "23:59",
        "02:02",
        "19:00",
        "22:10",
        "05:59",
        "00:01",
        "11:11",
        "13:37",
        "17:00",
        "21:30",
    ],
)
def test_time_answer_input_valid(time_str: str) -> None:
    obj = TimeAnswerInput(time=time_str, type=AnswerTypeEnum.time)
    assert obj.time == time_str
    assert obj.type == AnswerTypeEnum.time


@pytest.mark.parametrize(
    "time_str",
    [
        "24:00",
        "23:60",
        "12:99",
        "-01:00",
        "00:60",
        "25:00",
        "2:00",
        "12:5",
        "1234",
        "12-34",
        "12:345",
        "",
        " 12:34",
        "12:34 ",
        "12:34:00",
        "99:99",
        "0:00",
        "00:0",
        "0000",
        "::",
        "abcd",
        "12:3a",
        "a2:34",
    ],
)
def test_time_answer_input_invalid(time_str: str) -> None:
    with pytest.raises(ValidationError):
        TimeAnswerInput(time=time_str, type=AnswerTypeEnum.time)
