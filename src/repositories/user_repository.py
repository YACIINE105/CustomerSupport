from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.schemas.auth import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email.lower()))

    async def list(self, *, offset: int, limit: int) -> list[User]:
        return list((await self.session.scalars(select(User).order_by(User.id).offset(offset).limit(limit))).all())

    async def create(self, data: UserCreate, password_hash: str) -> User:
        user = User(email=str(data.email), password_hash=password_hash, role=data.role)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update(self, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def has_admin(self) -> bool:
        from src.domain.enums import UserRole
        return await self.session.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1)) is not None
