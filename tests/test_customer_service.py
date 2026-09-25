import pytest
from src.core.exceptions import ResourceNotFoundError
from unittest.mock import AsyncMock
from src.repositories.customer_repository import CustomerRepository
from src.services.customer_service import CustomerService






async def test_get_missing_customer_raises_not_found():
    repository = AsyncMock(spec=CustomerRepository)
    repository.get.return_value = None
    service = CustomerService(repository=repository)
    with pytest.raises(ResourceNotFoundError):
        await service.get_customer(42)

    repository.get.assert_awaited_once_with(42)
