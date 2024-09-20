import pytest

from meldingen.jsonlogic import JSONLogicValidationException, JSONLogicValidator


@pytest.fixture
def jsonlogic_validator() -> JSONLogicValidator:
    return JSONLogicValidator()


def test_validation_fails_when_jsonlogic_evaluation_fails(jsonlogic_validator: JSONLogicValidator) -> None:
    with pytest.raises(JSONLogicValidationException) as exception_info:
        jsonlogic_validator('{">=":[1, 10]}', {})

    assert str(exception_info.value) == "Input is not valid"


def test_jsonlogic_validation_succeeds(jsonlogic_validator: JSONLogicValidator) -> None:
    jsonlogic_validator('{">=":[10, 10]}', {})


def test_jsonlogic_validation_succeeds_when_using_data(jsonlogic_validator: JSONLogicValidator) -> None:
    jsonlogic_validator('{"==": [{"var": ["text"]}, "This is test data"]}', {"text": "This is test data"})
