# app/core/custom_exceptions.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.modules.core.types.response import AppResponse

async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:  # Unauthorized error
        return JSONResponse(
            status_code=exc.status_code,
            content=AppResponse(
                success=False,
                status_code=exc.status_code,
                message="Not authenticated" if not exc.detail else exc.detail,
                data=None
            ).model_dump()  # Use model_dump instead of dict
        )
    # For other HTTPExceptions, default to FastAPI's behavior
    return JSONResponse(
        status_code=exc.status_code,
        content=AppResponse(
            success=False,
            status_code=exc.status_code,
            message=exc.detail,
            data=None
        ).model_dump()  # Use model_dump instead of dict
    )
