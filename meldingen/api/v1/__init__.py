from typing import Any, Final

from pydantic import BaseModel
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class ResponseWithDetail(BaseModel):
    detail: str


not_found_response: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_404_NOT_FOUND: {
        "description": "Not Found",
        "content": {
            "application/json": {"example": {"detail": "Not Found"}, "schema": ResponseWithDetail.model_json_schema()}
        },
    }
}
default_response: Final[dict[str | int, dict[str, Any]]] = {"default": {"description": "Unexpected error"}}
conflict_response: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_409_CONFLICT: {
        "description": "Conflict, a uniqueness error occurred",
        "content": {
            "application/json": {
                "example": {
                    "detail": "The requested operation could not be completed due to a conflict with existing data."
                },
                "schema": ResponseWithDetail.model_json_schema(),
            }
        },
    }
}
unauthorized_response: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_401_UNAUTHORIZED: {
        "description": "Unauthorized, perhaps the token was invalid or expired, or the user could not be found.",
        "content": {
            "application/json": {
                "example": {"detail": "Token expired"},
                "schema": ResponseWithDetail.model_json_schema(),
            }
        },
    }
}
list_response: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_200_OK: {
        "headers": {
            "Content-Range": {
                "schema": {"type": "string"},
                "description": "Range and total number of results for pagination.",
            }
        }
    }
}
transition_not_allowed: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_400_BAD_REQUEST: {
        "description": "Transition not allowed from current state",
        "content": {
            "application/json": {
                "example": {"detail": "Transition not allowed from current state"},
                "schema": ResponseWithDetail.model_json_schema(),
            }
        },
    }
}
image_data_response: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_200_OK: {
        "description": "The binary image data",
        "content": {
            "image/*": {
                "schema": {
                    "type": "string",
                    "format": "binary",
                },
            }
        },
    }
}
