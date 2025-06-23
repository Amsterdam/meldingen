import pytest

from meldingen.jsonlogic import JSONLogicValidationException, JSONLogicValidator


@pytest.fixture
def jsonlogic_validator() -> JSONLogicValidator:
    return JSONLogicValidator()


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
            '{"if": [{">=": [{"var": "value.length"},3]}, true, "More than 2 characters needed"]}',
            "More than 2 characters needed",
            {"text": "AB"},
        ),
    ],
)
def test_validation_fails_with_custom_message_for_if_statement(
    jsonlogic_validator: JSONLogicValidator, logic: str, error_msg: str, data: dict[str, str]
) -> None:
    with pytest.raises(JSONLogicValidationException) as exception_info:
        jsonlogic_validator(logic, data)

        assert exception_info.value.msg == error_msg


def test_jsonlogic_validation_succeeds(jsonlogic_validator: JSONLogicValidator) -> None:
    jsonlogic_validator('{">=":[10, 10]}', {})


def test_jsonlogic_validation_succeeds_when_using_data(jsonlogic_validator: JSONLogicValidator) -> None:
    jsonlogic_validator('{"==": [{"var": ["text"]}, "This is test data"]}', {"text": "This is test data"})
