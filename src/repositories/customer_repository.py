from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.customer import Customer
from src.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: CustomerCreate) -> Customer:
        customer = Customer(**data.model_dump())
        self.session.add(customer)
        await self.session.flush()
        await self.session.refresh(customer)
        return customer

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[Customer]:
        result = await self.session.scalars(
            select(Customer).order_by(Customer.id).offset(offset).limit(limit)
        )
        return list(result.all())

    async def get(self, customer_id: int) -> Customer | None:
        return await self.session.get(Customer, customer_id)

    async def update(
        self,
        customer: Customer,
        data: CustomerUpdate,
    ) -> Customer:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        await self.session.flush()
        await self.session.refresh(customer)
        return customer

    async def delete(self, customer: Customer) -> None:
        await self.session.delete(customer)
        await self.session.flush()
