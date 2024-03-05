from starlette.status import HTTP_404_NOT_FOUND

not_found_response = {
    HTTP_404_NOT_FOUND: {
        "description": "Not Found",
        "content": {"application/json": {"example": {"detail": "Not Found"}}},
    }
}
