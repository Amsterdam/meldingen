from typing import Any, Final

from pydantic import BaseModel
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_413_CONTENT_TOO_LARGE,
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
forbidden_response: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_403_FORBIDDEN: {
        "description": "Forbidden, the authenticated user is not allowed to perform this action.",
        "content": {
            "application/json": {
                "example": {"detail": "Forbidden"},
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
attachment_upload_bad_request_response: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_400_BAD_REQUEST: {
        "description": "",
        "content": {
            "application/json": {
                "examples": {
                    "Uploading attachment with media type that is not allowed.": {
                        "value": {"detail": "Attachment not allowed"}
                    },
                    "Media type of data does not match the media type in the Content-Type header": {
                        "value": {"detail": "Media type of data does not match provided media type"}
                    },
                },
            },
        },
    }
}
attachment_upload_too_large_response: Final[dict[str | int, dict[str, Any]]] = {
    HTTP_413_CONTENT_TOO_LARGE: {
        "description": "Uploading attachment that is too large.",
        "content": {
            "application/json": {
                "examples": {"Allowed content size exceeded": {"value": {"detail": "Allowed content size exceeded"}}}
            }
        },
    },
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
