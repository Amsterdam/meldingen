from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False, name="static:robots")
def robots():
    data = """User-agent: *\nDisallow: /"""
    return data
