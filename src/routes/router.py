from fastapi import APIRouter, Depends

from src.core.dependencies import get_current_user
from src.routes.auth import router as auth_router, users_router
from src.routes.agents import router as agents_router
from src.routes.customers import router as customers_router
from src.routes.conversations import router as conversation_router
from src.routes.messages import router as messages_router

from src.routes.escalations import router as escalations_router

api_router = APIRouter()
api_router.include_router(escalations_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(agents_router)
for router in (customers_router, conversation_router, messages_router):
    api_router.include_router(router, dependencies=[Depends(get_current_user)])
