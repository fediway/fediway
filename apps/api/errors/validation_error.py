from fastapi.exceptions import RequestValidationError
from fastapi.openapi.constants import REF_PREFIX
from fastapi.openapi.utils import validation_error_response_definition
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from shared.utils.logging import log_error


async def http422_error_handler(
    request: Request,
    exc: RequestValidationError | ValidationError,
) -> JSONResponse:
    errors = exc.errors()
    if type(errors) == list:
        for i in range(len(errors)):
            if "input" in errors[i]:
                del errors[i]["input"]
            log_error("Validation error", module="api", error=errors[i])

    return JSONResponse(
        content={"message": "invalid request"},
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    )


validation_error_response_definition["properties"] = {
    "errors": {
        "title": "Errors",
        "type": "array",
        "items": {"$ref": "{0}ValidationError".format(REF_PREFIX)},
    },
}
