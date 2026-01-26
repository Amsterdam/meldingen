from typing import Any

from meldingen.jsonlogic import JSONLogicValidator, JSONLogicValidationException

from meldingen.schemas.input import AnswerInputUnion, ValueLabelAnswerInput, TextAnswerInput

from meldingen.models import Melding, FormIoQuestionComponent, BaseFormIoValuesComponent, FormIoComponentTypeEnum, \
    FormIoSelectComponent
from meldingen.repositories import MeldingRepository

class InvalidAnswerException(Exception):
    def __init__(self, msg: str, input: dict[str, Any]) -> None:
        self.msg = msg
        self.input = input

class AnswerPurger:
    _repository: MeldingRepository

    def __init__(self, repository: MeldingRepository) -> None:
        self._repository = repository

    async def __call__(self, melding: Melding) -> None:
        answers = await melding.awaitable_attrs.answers

        answers.clear()
        await self._repository.save(melding)


class FormIOValuesComponentValidator:
    """
    Validator that checks if the provided answer matches one of the answer options of a FormIOValues component, namely a Radio- or Checkbox question.
    """
    async def __call__(self, question_component: BaseFormIoValuesComponent, answer: ValueLabelAnswerInput) -> None:
        values = await question_component.awaitable_attrs.values
        valid_pairs = set((option.value, option.label) for option in values)

        for answer_object in answer.values_and_labels:
            pair = (answer_object.value, answer_object.label)
            if pair not in valid_pairs:
                raise InvalidAnswerException(
                    msg=f"Given answer is not an option for component with key '{question_component.key}'.",
                    input={"value": answer_object.value, "label": answer_object.label}
                )


class SelectComponentAnswerValidator:
    """
    Validator that checks if the provided answer matches one of the answer options of a FormIO Select component.
    """

    async def  __call__(self, question_component: FormIoSelectComponent, answer: ValueLabelAnswerInput) -> None:
        values = await question_component.awaitable_attrs.data.awaitiable_attrs.values # TODO kan evt gelazy joined
        valid_pairs = set((option.value, option.label) for option in values)

        for answer_object in answer.values_and_labels:
            pair = (answer_object.value, answer_object.label)
            if pair not in valid_pairs:
                raise InvalidAnswerException(
                    msg=f"Given answer is not an option for component with key '{question_component.key}'.",
                    input={"value": answer_object.value, "label": answer_object.label}
                )


class TextComponentAnswerValidator:
    """
    Validate text answers against JSONLogic rules defined in the question component.
    """
    _validate_json_logic: JSONLogicValidator

    def __init__(self, json_logic_validator: JSONLogicValidator) -> None:
        self._validate_json_logic = json_logic_validator

    def __call__(self, question_component: FormIoQuestionComponent, answer_input: TextAnswerInput) -> None:
        if question_component.jsonlogic is not None:
            try:
                self._validate_json_logic(question_component.jsonlogic, {"text": answer_input.text})
            except JSONLogicValidationException as e:
                raise InvalidAnswerException(e.msg, e.input) from e

class AnswerValidator:
    _validate_values_component_answer: FormIOValuesComponentValidator
    _validate_select_component_answer: SelectComponentAnswerValidator
    _validate_text_component_answer: TextComponentAnswerValidator

    def __init__(self, form_io_values_component_validator: FormIOValuesComponentValidator, select_component_answer_validator: SelectComponentAnswerValidator, text_component_answer_validator: TextComponentAnswerValidator) -> None:
        self._validate_values_component_answer = form_io_values_component_validator
        self._validate_select_component_answer = select_component_answer_validator
        self._validate_text_component_answer = text_component_answer_validator

    async def __call__(self, question_component: FormIoQuestionComponent, answer: AnswerInputUnion) -> None:
        match question_component.type:

            case FormIoComponentTypeEnum.checkbox | FormIoComponentTypeEnum.radio:
                assert(isinstance(answer, ValueLabelAnswerInput))
                assert(isinstance(question_component, BaseFormIoValuesComponent))
                await self._validate_values_component_answer(question_component, answer)

            case FormIoComponentTypeEnum.select:
                assert(isinstance(answer, ValueLabelAnswerInput))
                assert(isinstance(question_component, FormIoSelectComponent))
                await self._validate_select_component_answer(question_component, answer)

            case FormIoComponentTypeEnum.text_field | FormIoComponentTypeEnum.text_area:
                assert(isinstance(answer, TextAnswerInput))
                self._validate_text_component_answer(question_component, answer)

            case _:
                pass
