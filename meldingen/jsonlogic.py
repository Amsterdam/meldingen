import json
from typing import Any

from jsonlogic.core import JSONLogicExpression
from jsonlogic.evaluation import evaluate
from jsonlogic.json_schema.types import BooleanType
from jsonlogic.operators import operator_registry
from jsonlogic.typechecking import typecheck


class JSONLogicValidationException(Exception): ...


class JSONLogicValidator:
    def __call__(self, tests: str, data: dict[str, Any]) -> None:
        expression = JSONLogicExpression.from_json(json.loads(tests))
        operator_tree = expression.as_operator_tree(operator_registry)
        root_type, _ = typecheck(operator_tree, data_schema={})

        if root_type != BooleanType():
            raise JSONLogicValidationException("Root type is not boolean")

        if not evaluate(operator_tree, data, data_schema=None):
            raise JSONLogicValidationException("Input is not valid")
