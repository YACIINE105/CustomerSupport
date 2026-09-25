from src.core.exceptions import ApplicationError, ResourceNotFoundError
from src.models.customer import Customer
from src.repositories.customer_repository import CustomerRepository
from src.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    def __init__(self, repository: CustomerRepository) -> None:
        self.repository = repository

    async def create_customer(self, data: CustomerCreate) -> Customer:
        return await self.repository.create(data)

    async def list_customers(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Customer]:
        return await self.repository.list(offset=offset, limit=limit)

    async def get_customer(self, customer_id: int) -> Customer:
        customer = await self.repository.get(customer_id)
        if customer is None:
            raise ResourceNotFoundError("Customer", customer_id)
        return customer

    async def update_customer(
        self,
        customer_id: int,
        data: CustomerUpdate,
    ) -> Customer:
        changes = data.model_dump(exclude_unset=True)
        if changes.get("name") is None and "name" in changes:
            raise ApplicationError(
                "Customer name cannot be null",
                status_code=422,
                code="invalid_customer_update",
            )

        customer = await self.get_customer(customer_id)
        return await self.repository.update(customer, data)

    async def delete_customer(self, customer_id: int) -> None:
        customer = await self.get_customer(customer_id)
        await self.repository.delete(customer)
