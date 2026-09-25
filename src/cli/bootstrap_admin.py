"""Create the first administrator: python -m src.cli.bootstrap_admin."""

import asyncio
from getpass import getpass

from pydantic import ValidationError

from src.core.config import get_settings
from src.core.database import async_session_factory, engine
from src.core.exceptions import ApplicationError
from src.domain.enums import UserRole
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository
from src.schemas.auth import UserCreate
from src.services.auth_service import AuthService


async def bootstrap(data: UserCreate) -> None:
    try:
        async with async_session_factory() as session:
            async with session.begin():
                user = await AuthService(
                    UserRepository(session), AgentRepository(session), get_settings(),
                ).bootstrap_admin(data)
            print(f"Administrator created with user ID {user.id}.")
    finally:
        await engine.dispose()


def main() -> None:
    email = input("Administrator email: ").strip()
    password = getpass("Password (12–128 characters): ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    try:
        data = UserCreate(email=email, password=password, role=UserRole.ADMIN)
    except ValidationError:
        raise SystemExit("Provide a valid email and a password of 12–128 characters") from None
    try:
        asyncio.run(bootstrap(data))
    except ApplicationError as exc:
        raise SystemExit(exc.detail) from None


if __name__ == "__main__":
    main()
