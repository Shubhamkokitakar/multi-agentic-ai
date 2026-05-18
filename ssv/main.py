from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import logger
from apis import (
    access_control_routes,
    ai_response_routes,
    feedback_routes,
    history_control_routes,
)
from security.authentication_middleware import get_current_user

"""Main FastAPI application setup with CORS, JWT authentication, and route registration."""

logger.info("Initializing FastAPI")
app = FastAPI(title="SSV API", version="1.0")

# Configure CORS
logger.info("Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ssv-dev.azure.chevron.com",
        "https://ssv-test.azure.chevron.com",
        "https://ssv.azure.chevron.com",
        "https://localhost:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Security Headers Middleware (HSTS, etc.)
logger.info("Adding security headers middleware")
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses.
    
    HSTS (HTTP Strict Transport Security):
    - max-age=31536000: Policy valid for 1 year (in seconds)
    - includeSubDomains: Apply to all subdomains
    - preload: Allow inclusion in browser HSTS preload lists (optional)
    """
    response: Response = await call_next(request)
    # HSTS header - Force HTTPS for 1 year including subdomains
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    # Additional security headers 
    response.headers["X-Content-Type-Options"] = "nosniff"  # Prevent MIME sniffing
    response.headers["X-Frame-Options"] = "DENY"  # Prevent clickjacking
    response.headers["X-XSS-Protection"] = "1; mode=block"  # XSS protection
    
    return response

# Secure API routes with JWT authentication
logger.info("Registering secured API routes with JWT validation")
app.include_router(access_control_routes.router, dependencies=[Depends(get_current_user)])
app.include_router(ai_response_routes.router, dependencies=[Depends(get_current_user)])
app.include_router(feedback_routes.router, dependencies=[Depends(get_current_user)])
app.include_router(history_control_routes.router, dependencies=[Depends(get_current_user)])
app.include_router(ai_response_routes.router_ws)
