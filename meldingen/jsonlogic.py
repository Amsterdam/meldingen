import json
from typing import Any

from jsonlogic import JSONLogicExpression
from jsonlogic.evaluation import evaluate
from jsonlogic.operators import operator_registry
from jsonlogic.resolving import ReferenceParser


class JSONLogicValidationException(Exception):

    def __init__(self, msg: str, input: dict[str, Any]) -> None:
        self.msg = msg
        self.input = input


class JSONLogicValidator:
    _reference_parser: ReferenceParser

    def __init__(self, reference_parser: ReferenceParser) -> None:
        self._reference_parser = reference_parser

    def __call__(self, tests: str, data: dict[str, Any]) -> None:
        expression = JSONLogicExpression.from_json(json.loads(tests))

        root_operator = expression.as_operator_tree(operator_registry)

        result = evaluate(root_operator, data, data_schema=None, settings={"reference_parser": self._reference_parser})

        if isinstance(result, str):
            raise JSONLogicValidationException(msg=result, input=data)
        if not result:
            raise JSONLogicValidationException(msg="Input is not valid", input=data)
