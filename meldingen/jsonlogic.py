import json
from typing import Any

from json_logic import jsonLogic


class JSONLogicValidationException(Exception):

    def __init__(self, message: str, input: dict) -> None:
        self.message = message
        self.input = input


class JSONLogicValidator:
    def __call__(self, tests: str, data: dict[str, Any]) -> None:
        validation = json.loads(tests)
        result = jsonLogic(validation, data)
        if not result:

            # TODO how to do this pretty?
            error_message = next(iter(validation.values()))[3]
            if isinstance(error_message, str):
                raise JSONLogicValidationException(message=error_message, input=data)

            raise JSONLogicValidationException(message="Input is not valid", input=data)


# {"and" : [
#     {">=": [{ "var": "value.length" }, 3]},
#      {"<=": [{ "var": "value.length" }, 100]}
#   ],
#   true,
#   "above two under 100"
#   }
