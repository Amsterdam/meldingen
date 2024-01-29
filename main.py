from fastapi import FastAPI

from meldingen.config import settings

app = FastAPI(
    debug=settings.debug,
    title=settings.project_name,
    prefix=settings.url_prefix,
)
