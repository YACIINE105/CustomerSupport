from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.controllers.auth_controller import AuthController
from src.core.config import Settings, get_settings
from src.core.dependencies import AdminUser, CurrentUser, ManagerUser, SessionDependency
from src.models.user import User
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository
from src.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse, UserUpdate
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])
users_router = APIRouter(prefix="/users", tags=["users"])


def get_auth_controller(session: SessionDependency, settings: Annotated[Settings, Depends(get_settings)]) -> AuthController:
    return AuthController(AuthService(UserRepository(session), AgentRepository(session), settings))


Controller = Annotated[AuthController, Depends(get_auth_controller)]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, actor: AdminUser, controller: Controller) -> User:
    return await controller.register(data, actor)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, controller: Controller) -> TokenResponse:
    return await controller.login(data)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> User:
    return user


@users_router.get("", response_model=list[UserResponse])
async def list_users(
    actor: ManagerUser, controller: Controller,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[User]:
    return await controller.list_users(offset=offset, limit=limit)


@users_router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, data: UserUpdate, actor: AdminUser, controller: Controller) -> User:
    return await controller.update_user(user_id, data, actor)
