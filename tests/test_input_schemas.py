import pytest
from pydantic import ValidationError

from meldingen.models import AnswerTypeEnum
from meldingen.schemas.input import NoteInput, TimeAnswerInput


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
