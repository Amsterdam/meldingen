from fastapi import FastAPI
from meldingen.api.v1.api import api_router

from meldingen.config import Settings
from meldingen.containers import Container

container = Container()
# TODO: We are currently unable to use `from_pydantic()`, because the `dependency-injector`
# lacks support for pydantic v2.
# https://python-dependency-injector.ets-labs.org/providers/configuration.html#loading-from-a-pydantic-settings
container.settings.from_dict(Settings().model_dump())

app = FastAPI(
    debug=container.settings.get("debug"),
    title=container.settings.get("project_name"),
    prefix=container.settings.get("url_prefix"),
)
app.include_router(api_router)
