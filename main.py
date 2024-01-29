from fastapi import FastAPI
from sqlmodel import create_engine, SQLModel

from meldingen.config import settings

app = FastAPI(
    debug=settings.debug,
    title=settings.project_name,
    prefix=settings.url_prefix,
)

engine = create_engine(str(settings.database_dsn), echo=True)
