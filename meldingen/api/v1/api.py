from fastapi import APIRouter

from meldingen.api.v1.endpoints import attachment, classification, form, mail, melding, static_form, user

api_router = APIRouter()
api_router.include_router(attachment.router, prefix="/attachment", tags=["attachment"])
api_router.include_router(classification.router, prefix="/classification", tags=["classification"])
api_router.include_router(mail.router, prefix="/mail", tags=["mail"])
api_router.include_router(melding.router, prefix="/melding", tags=["melding"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(form.router, prefix="/form", tags=["form"])
api_router.include_router(static_form.router, prefix="/static-form", tags=["static-form"])
