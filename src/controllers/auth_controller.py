from src.models.user import User
from src.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserUpdate
from src.services.auth_service import AuthService


class AuthController:
    def __init__(self, service: AuthService) -> None:
        self.service = service

    async def register(self, data: UserCreate, actor: User) -> User:
        return await self.service.register(data, actor)

    async def login(self, data: LoginRequest) -> TokenResponse:
        return await self.service.login(data)

    async def list_users(self, *, offset: int, limit: int) -> list[User]:
        return await self.service.list_users(offset=offset, limit=limit)

    async def update_user(self, user_id: int, data: UserUpdate, actor: User) -> User:
        return await self.service.update_user(user_id, data, actor)
