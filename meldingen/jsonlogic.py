import json
from dataclasses import dataclass
from typing import Any, Self

from jsonlogic import JSONLogicExpression, JSONLogicSyntaxError, Operator
from jsonlogic.evaluation import EvaluationContext, evaluate, get_value
from jsonlogic.operators import operator_registry
from jsonlogic.registry import UnkownOperator as UnknownOperator
from jsonlogic.resolving import ReferenceParser
from jsonlogic.typing import OperatorArgument


class JSONLogicValidationException(Exception):

    def __init__(self, msg: str, input: dict[str, Any]) -> None:
        self.msg = msg
        self.input = input


class JSONLogicValidator:
    _reference_parser: ReferenceParser

    def __init__(self, reference_parser: ReferenceParser) -> None:
        self._reference_parser = reference_parser
        try:
            operator_registry.get("length")
        except UnknownOperator:
            operator_registry.register("length", LengthOperator)

    def __call__(self, tests: str, data: dict[str, Any]) -> None:
        expression = JSONLogicExpression.from_json(json.loads(tests))

        root_operator = expression.as_operator_tree(operator_registry)

        result = evaluate(root_operator, data, data_schema=None, settings={"reference_parser": self._reference_parser})

        if isinstance(result, str):
            raise JSONLogicValidationException(msg=result, input=data)
        if not result:
            raise JSONLogicValidationException(msg="Input is not valid", input=data)


@dataclass
class LengthOperator(Operator):
    _string: OperatorArgument

    @classmethod
    def from_expression(cls, operator: str, arguments: list[OperatorArgument]) -> Self:
        arguments_length = len(arguments)
        if arguments_length != 1:
            raise JSONLogicSyntaxError(f"Expected 1 argument, got {arguments_length}")

        return cls(operator=operator, _string=arguments[0])

    def evaluate(self, context: EvaluationContext) -> int:
        string_value = get_value(self._string, context)
        return len(string_value)
