from fastapi import FastAPI

from meldingen.api.v1.api import api_router
from meldingen.config import Settings
from meldingen.containers import Container


def get_application() -> FastAPI:
    container = Container()
    # TODO: We are currently unable to use `from_pydantic()`, because the `dependency-injector`
    # lacks support for pydantic v2.
    # https://python-dependency-injector.ets-labs.org/providers/configuration.html#loading-from-a-pydantic-settings
    container.settings.from_dict(Settings().model_dump())

    application = FastAPI(
        debug=container.settings.get("debug"),
        title=container.settings.get("project_name"),
        prefix=container.settings.get("url_prefix"),
    )
    application.include_router(api_router)

    return application


app = get_application()
