from fastapi import APIRouter

from src.routes.customers import router as customers_router
from src.routes.conversations import router as conversation_router


api_router = APIRouter()
api_router.include_router(customers_router)
api_router.include_router(conversation_router)
