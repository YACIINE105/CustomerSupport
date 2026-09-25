class ApplicationError(Exception):
    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 400,
        code: str = "application_error",
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code


class ResourceNotFoundError(ApplicationError):
    def __init__(self, resource: str, resource_id: object) -> None:
        super().__init__(
            f"{resource} with id {resource_id} was not found",
            status_code=404,
            code="resource_not_found",
        )


class AuthenticationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("Invalid credentials or inactive account", status_code=401, code="unauthorized")


class PermissionDeniedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("You do not have permission for this operation", status_code=403, code="forbidden")


class ConflictError(ApplicationError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409, code="conflict")
