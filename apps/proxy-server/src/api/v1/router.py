from fastapi import APIRouter
from api.v1.endpoints import session, chat

api_router = APIRouter()

api_router.include_router(session.router, prefix="/session", tags=["session"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])