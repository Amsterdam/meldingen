from starlette.status import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

not_found_response = {
    HTTP_404_NOT_FOUND: {
        "description": "Not Found",
        "content": {"application/json": {"example": {"detail": "Not Found"}}},
    }
}
default_response = {"default": {"description": "Unexpected error"}}
conflict_response = {
    HTTP_409_CONFLICT: {
        "description": "Conflict, a uniqueness error occurred",
        "content": {
            "application/json": {
                "example": {
                    "detail": "The requested operation could not be completed due to a conflict with existing data."
                }
            }
        },
    }
}
