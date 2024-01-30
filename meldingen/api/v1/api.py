from fastapi import APIRouter

from meldingen.api.v1.endpoints import melding

api_router = APIRouter()
api_router.include_router(melding.router, prefix="/melding", tags=["melding"])
