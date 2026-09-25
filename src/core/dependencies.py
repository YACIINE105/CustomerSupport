from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.database import get_db_session
from src.core.exceptions import AuthenticationError, PermissionDeniedError
from src.core.security import decode_access_token
from src.domain.enums import UserRole
from src.models.user import User
from src.repositories.user_repository import UserRepository

SessionDependency = Annotated[AsyncSession, Depends(get_db_session, scope="function")]
bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None:
        raise AuthenticationError()
    user_id = decode_access_token(credentials.credentials, settings)
    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError()
        return user
    return check


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
ManagerUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_HEAD))]
