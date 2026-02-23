import pytest
from pydantic import ValidationError

from meldingen.models import AnswerTypeEnum
from meldingen.schemas.input import TimeAnswerInput


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
        None,
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
