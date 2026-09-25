from src.models.customer import Customer
from src.schemas.customer import CustomerCreate, CustomerUpdate
from src.services.customer_service import CustomerService


class CustomerController:
    def __init__(self, service: CustomerService) -> None:
        self.service = service


    async def create(self, data: CustomerCreate) -> Customer:
        return await self.service.create_customer(data)


    async def list(self, *, offset: int, limit: int) -> list[Customer]:
        return await self.service.list_customers(offset=offset, limit=limit)


    async def get(self, customer_id: int) -> Customer:
        return await self.service.get_customer(customer_id)


    async def update(self,customer_id: int,data: CustomerUpdate,) -> Customer:
        return await self.service.update_customer(customer_id, data)


    async def delete(self, customer_id: int) -> None:
        await self.service.delete_customer(customer_id)
