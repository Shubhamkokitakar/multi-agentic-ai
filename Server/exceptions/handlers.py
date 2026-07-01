from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def http_exception_handler(
    request: Request,
    exc: HTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        }
    )

async def generic_exception_handler(
    request: Request,
    exc: Exception
):
    # log here
    print(exc)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error"
        }
    )