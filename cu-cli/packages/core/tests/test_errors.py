import pytest

from cu_cli_core.errors import (
    AuthenticationError,
    ConflictError,
    CuCoreError,
    ErrorCategory,
    LocalIOError,
    NotFoundError,
    ServiceError,
    ServiceErrorDetail,
    UsageError,
    ValidationError,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "error_type, category",
    [
        (UsageError, ErrorCategory.USAGE),
        (ValidationError, ErrorCategory.VALIDATION),
        (AuthenticationError, ErrorCategory.AUTHENTICATION),
        (NotFoundError, ErrorCategory.NOT_FOUND),
        (ConflictError, ErrorCategory.CONFLICT),
        (ServiceError, ErrorCategory.SERVICE),
        (LocalIOError, ErrorCategory.LOCAL_IO),
    ],
)
def test_error_subclasses_have_stable_categories(error_type, category):
    assert error_type("failure").category is category


def test_core_error_retains_structured_frontend_neutral_context():
    details = (ServiceErrorDetail("InvalidField", "bad value", "fields.total"),)
    error = CuCoreError(
        "request failed",
        hint="correct the field",
        status_code=400,
        details=details,
        context={"operation": "analyzer.create"},
    )

    assert str(error) == "request failed"
    assert error.message == "request failed"
    assert error.hint == "correct the field"
    assert error.status_code == 400
    assert error.details == details
    assert error.context == {"operation": "analyzer.create"}
