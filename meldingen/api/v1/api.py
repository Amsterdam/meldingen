from fastapi import APIRouter

from meldingen.api.v1.endpoints import classification, form, melding, primary_form, user

api_router = APIRouter()
api_router.include_router(classification.router, prefix="/classification", tags=["classification"])
api_router.include_router(melding.router, prefix="/melding", tags=["melding"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(primary_form.router, prefix="/form/primary", tags=["primary form"])
api_router.include_router(form.router, prefix="/form", tags=["form"])
