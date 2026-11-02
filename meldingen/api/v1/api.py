from enum import Enum

from fastapi import APIRouter, Depends

from meldingen import static
from meldingen.api.v1 import not_found_response
from meldingen.api.v1.endpoints import (
    asset_type,
    attachment,
    docs,
    form,
    label,
    llm_eval,
    mail,
    melding,
    source,
    static_form,
    user,
)
from meldingen.api.v1.endpoints.classification import (
    classification_router_backoffice,
    classification_router_public,
)
from meldingen.authentication import authenticate_user

api_router = APIRouter(responses={**not_found_response})
api_router_backoffice = APIRouter()
api_router_public = APIRouter()

api_router.include_router(api_router_backoffice, dependencies=[Depends(authenticate_user)])
api_router.include_router(api_router_public, prefix="/public")

routers_by_type = {
    "backoffice": api_router_backoffice,
    "public": api_router_public,
}


def attach_routers(prefix: str, routers: dict[str, APIRouter], tags: list[str | Enum] | None = None):
    for router_type, router in routers.items():
        routers_by_type[router_type].include_router(router, prefix=prefix, tags=tags)


attach_routers(
    prefix="/classification",
    routers={"backoffice": classification_router_backoffice, "public": classification_router_public},
    tags=["classification"],
)


# Mixed routes that may or may not require authentication
api_router.include_router(attachment.router, prefix="/attachment", tags=["attachment"])
api_router.include_router(mail.router, prefix="/mail", tags=["mail"])
api_router.include_router(melding.router, prefix="/melding", tags=["melding"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(form.router, prefix="/form", tags=["form"])
api_router.include_router(static_form.router, prefix="/static-form", tags=["static-form"])
api_router.include_router(asset_type.router, prefix="/asset-type", tags=["asset-type"])
api_router.include_router(label.router, prefix="/label", tags=["label"])
api_router.include_router(source.router, prefix="/source", tags=["source"])
api_router.include_router(docs.router, prefix="/docs", tags=["docs"])
api_router.include_router(llm_eval.router, prefix="/llm-eval", tags=["llm-eval"])
api_router.include_router(static.router, prefix="", tags=["static"])
