from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.customer_controller import CustomerController
from src.core.database import get_db_session
from src.models.customer import Customer
from src.repositories.customer_repository import CustomerRepository
from src.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from src.services.customer_service import CustomerService


router = APIRouter(prefix="/customers", tags=["customers"])


def get_customer_controller(session: Annotated[AsyncSession,
                            Depends(get_db_session, scope="function")],) -> CustomerController:

    repository = CustomerRepository(session)
    service = CustomerService(repository)
    return CustomerController(service)


ControllerDependency = Annotated[
    CustomerController,
    Depends(get_customer_controller),
]


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer(
    data: CustomerCreate,
    controller: ControllerDependency,
) -> Customer:
    return await controller.create(data)


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    controller: ControllerDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Customer]:
    return await controller.list(offset=offset, limit=limit)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    controller: ControllerDependency,
) -> Customer:
    return await controller.get(customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    controller: ControllerDependency,
) -> Customer:
    return await controller.update(customer_id, data)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    controller: ControllerDependency,
) -> Response:
    await controller.delete(customer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
