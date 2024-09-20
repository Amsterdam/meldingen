import json
from typing import Any

from json_logic import jsonLogic


class JSONLogicValidationException(Exception): ...


class JSONLogicValidator:
    def __call__(self, tests: str, data: dict[str, Any]) -> None:
        if not jsonLogic(json.loads(tests), data):
            raise JSONLogicValidationException("Input is not valid")
