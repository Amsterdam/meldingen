import json
from typing import Any

from json_logic import jsonLogic


class JSONLogicValidationException(Exception):

    def __init__(self, msg: str, input: dict) -> None:
        self.msg = msg
        self.input = input


class JSONLogicValidator:
    def __call__(self, tests: str, data: dict[str, Any]) -> None:
        validation = json.loads(tests)
        result = jsonLogic(validation, data)

        if isinstance(result, str):
            raise JSONLogicValidationException(msg=result, input=data)
        if not result:
            raise JSONLogicValidationException(msg="Input is not valid", input=data)
