import pytest
from jsonlogic import JSONLogicSyntaxError
from jsonlogic.registry import UnkownOperator as UnknownOperator
from jsonlogic.resolving import DotReferenceParser

from meldingen.jsonlogic import JSONLogicValidationException, JSONLogicValidator


@pytest.fixture
def jsonlogic_validator() -> JSONLogicValidator:
    return JSONLogicValidator(DotReferenceParser())


def test_validation_fails_when_jsonlogic_evaluation_fails(jsonlogic_validator: JSONLogicValidator) -> None:
    with pytest.raises(JSONLogicValidationException) as exception_info:
        jsonlogic_validator('{">=":[1, 10]}', {})

        assert exception_info.value.msg == "Input is not valid"


def test_validation_succeeds_for_if_statement(jsonlogic_validator: JSONLogicValidator) -> None:
    logic = '{"if": [{"==": [{"var": ["text"]},"Water"]}, true, "You must type \'Water\'!"]}'
    jsonlogic_validator(logic, {"text": "Water"})


@pytest.mark.parametrize(
    "logic, error_msg, data",
    [
        (
            '{"if": [{"==": [{"var": ["text"]},"Water"]}, true, "You must type \'Water\'!"]}',
            "You must type 'Water'!",
            {"text": "Fire"},
        ),
        (
            '{"if": [{"!=": [{"var": "text"},"Fire"]}, true, "You must not type \'Fire\'!"]}',
            "You must not type 'Fire'!",
            {"text": "Fire"},
        ),
    ],
)
def test_validation_fails_with_custom_message_for_if_statement(
    jsonlogic_validator: JSONLogicValidator, logic: str, error_msg: str, data: dict[str, str]
) -> None:
    with pytest.raises(JSONLogicValidationException) as exception_info:
        jsonlogic_validator(logic, data)

        assert exception_info.value.msg == error_msg


@pytest.mark.parametrize(
    "logic, error_msg, data",
    [
        (
            '{"if": [{"non_existing_operator": [{"var": ["text"]},"Water"]}, true, "You must type \'Water\'!"]}',
            "You must type 'Water'!",
            {"text": "Fire"},
        ),
    ],
)
def test_validation_fails_with_custom_message_for_if_statement(
    jsonlogic_validator: JSONLogicValidator, logic: str, error_msg: str, data: dict[str, str]
) -> None:
    with pytest.raises(UnknownOperator) as exception_info:
        jsonlogic_validator(logic, data)

        assert exception_info.value.msg == error_msg



def test_jsonlogic_validation_succeeds(jsonlogic_validator: JSONLogicValidator) -> None:
    jsonlogic_validator('{">=":[10, 10]}', {})


def test_jsonlogic_validation_succeeds_when_using_data(jsonlogic_validator: JSONLogicValidator) -> None:
    jsonlogic_validator('{"==": [{"var": ["text"]}, "This is test data"]}', {"text": "This is test data"})


@pytest.mark.parametrize(
    "logic, error_msg, data",
    [
        (
            '{"if": [{"<":[{"length": {"var": ["text"]}},3]},true,"Too long"]}',
            "Too long",
            {"text": "Longerthan3"},
        ),
        (
            '{"if": [{"<":[{"length": {"var": ["text"]}},3]},true,"Too long"]}',
            "Too long",
            {"text": "abc"},
        ),
        (
            '{"if": [{"<=":[{"length": {"var": ["text"]}},5]},true,"Too long, too bad"]}',
            "Too long, too bad",
            {"text": "123456"},
        ),
    ],
)
def test_length_operator_negative(
    jsonlogic_validator: JSONLogicValidator, logic: str, error_msg: str | bool, data: dict[str, str]
) -> None:
    with pytest.raises(JSONLogicValidationException) as exception_info:
        jsonlogic_validator(logic, data)

    assert exception_info.value.msg == error_msg


def test_length_operator_positive(jsonlogic_validator: JSONLogicValidator) -> None:
    jsonlogic_validator('{"if": [{"<=":[{"length": {"var": ["text"]}},3]},true,"Too long"]}', {"text": "ABC"})


def test_length_operator_too_many_arguments(jsonlogic_validator: JSONLogicValidator) -> None:
    with pytest.raises(JSONLogicSyntaxError):
        jsonlogic_validator('{"if": [{"<=":[{"length": {"var": ["text"]}},3,5]},true,"Too long"]}', {"text": "ABC"})
