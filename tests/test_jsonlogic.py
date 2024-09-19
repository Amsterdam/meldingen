import pytest

from meldingen.jsonlogic import JSONLogicValidationException, JSONLogicValidator


@pytest.fixture
def jsonlogic_validator() -> JSONLogicValidator:
    return JSONLogicValidator()


def test_jsonlogic_can_not_be_validated_when_root_type_is_not_boolean(jsonlogic_validator: JSONLogicValidator) -> None:
    with pytest.raises(JSONLogicValidationException) as exception_info:
        jsonlogic_validator('{"var": "i"}', {})

    assert str(exception_info.value) == "Root type is not boolean"


def test_validation_fails_when_jsonlogic_evaluation_fails(jsonlogic_validator: JSONLogicValidator) -> None:
    with pytest.raises(JSONLogicValidationException) as exception_info:
        jsonlogic_validator('{">=":[1, 10]}', {})

    assert str(exception_info.value) == "Input is not valid"


def test_jsonlogic_validation_succeeds(jsonlogic_validator: JSONLogicValidator) -> None:
    jsonlogic_validator('{">=":[10, 10]}', {})
