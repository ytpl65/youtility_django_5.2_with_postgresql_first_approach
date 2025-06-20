from http import HTTPStatus
from typing import Any, Dict, Optional

from django.utils.translation import gettext_lazy as _

class Error(Exception):
    pass

class BaseError(Exception):
    """Base exception for all custom exceptions"""

    def __init__(
        self,
        message: str,
        error_code: str,
        http_status: int = HTTPStatus.BAD_REQUEST,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.extra = extra or {}
        super().__init__(message)

class NoRecordsFound(Error):
    pass

# Authentication Errors
class AuthenticationError(BaseError):
    def __init__(self, message: str = _("Authentication failed")):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            http_status=HTTPStatus.UNAUTHORIZED,
        )


class NoClientPeopleError(BaseError):
    def __init__(
        self,
        message: str = _(
            "Unable to find client or People or User/Client are not verified"
        ),
    ):
        super().__init__(
            message=message,
            error_code="NO_CLIENT_PEOPLE",
            http_status=HTTPStatus.UNAUTHORIZED,
        )


class MultiDevicesError(BaseError):
    def __init__(self, message: str = _("Cannot login on multiple devices")):
        super().__init__(
            message=message,
            error_code="MULTI_DEVICES",
            http_status=HTTPStatus.UNAUTHORIZED,
        )


class NotRegisteredError(BaseError):
    def __init__(self, message: str = _("Device not registered")):
        super().__init__(
            message=message,
            error_code="NOT_REGISTERED",
            http_status=HTTPStatus.UNAUTHORIZED,
        )


class WrongCredsError(BaseError):
    def __init__(self, message: str = _("Invalid credentials")):
        super().__init__(
            message=message,
            error_code="WRONG_CREDENTIALS",
            http_status=HTTPStatus.UNAUTHORIZED,
        )


class NoSiteError(BaseError):
    def __init__(self, message: str = _("Site not found")):
        super().__init__(
            message=message, error_code="NO_SITE", http_status=HTTPStatus.NOT_FOUND
        )


class NotBelongsToClientError(BaseError):
    def __init__(self, message: str = _("User does not belong to this client")):
        super().__init__(
            message=message,
            error_code="NOT_BELONGS_TO_CLIENT",
            http_status=HTTPStatus.FORBIDDEN,
        )


class PermissionDeniedError(BaseError):
    def __init__(self, message: str = _("Permission denied")):
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            http_status=HTTPStatus.FORBIDDEN,
        )


# Data Errors
class ResourceNotFoundError(BaseError):
    def __init__(self, resource_type: str, identifier: Any):
        super().__init__(
            message=f"{resource_type} with identifier {identifier} not found",
            error_code="RESOURCE_NOT_FOUND",
            http_status=HTTPStatus.NOT_FOUND,
        )


class ValidationError(BaseError):
    def __init__(self, errors: Dict[str, Any]):
        super().__init__(
            message="Validation error",
            error_code="VALIDATION_ERROR",
            http_status=HTTPStatus.BAD_REQUEST,
            extra={"validation_errors": errors},
        )


class IntegrityConstratintError(BaseError):
    def __init__(self, message: str = _("Database integrity error")):
        super().__init__(
            message=message,
            error_code="INTEGRITY_ERROR",
            http_status=HTTPStatus.CONFLICT,
        )


# Data Access Errors
class DoesNotExistError(BaseError):
    def __init__(self, entity: str):
        super().__init__(
            message=f"{entity} not found",
            error_code="DOES_NOT_EXIST",
            http_status=HTTPStatus.NOT_FOUND,
        )


class IntegrityConstraintError(BaseError):
    def __init__(
        self, message: str = _("Record already exists or violates constraints")
    ):
        super().__init__(
            message=message,
            error_code="INTEGRITY_ERROR",
            http_status=HTTPStatus.CONFLICT,
        )


class RestrictedError(BaseError):
    def __init__(self, message: str = _("Cannot delete due to existing dependencies")):
        super().__init__(
            message=message,
            error_code="RESTRICTED_DELETE",
            http_status=HTTPStatus.CONFLICT,
        )


# File Operation Errors
class FileOperationError(BaseError):
    def __init__(self, operation: str, detail: str):
        super().__init__(
            message=f"File {operation} failed: {detail}",
            error_code="FILE_OPERATION_ERROR",
            http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


# Business Logic Errors
class BusinessRuleError(BaseError):
    def __init__(self, rule: str, detail: str):
        super().__init__(
            message=f"Business rule violation - {rule}: {detail}",
            error_code="BUSINESS_RULE_ERROR",
            http_status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )


# System Errors
class SystemError(BaseError):
    def __init__(self, message: str = _("Internal system error")):
        super().__init__(
            message=message,
            error_code="SYSTEM_ERROR",
            http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

class Error(Exception):
    pass


class NoDbError(Error):
    pass


class RecordsAlreadyExist(Error):
    pass