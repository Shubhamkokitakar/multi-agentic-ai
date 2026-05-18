import os
import jwt
from typing import Dict, Any, Callable, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from config.config import env, client_id, client_secret, tenant_id
from services.access_control import AccessControl
from utils.logger import logger

security = HTTPBearer()


class AuthMiddleware:
    """Middleware for validating Azure AD JWT tokens from the CAL frontend."""

    def __init__(self) -> None:
        """Initialize Azure AD configuration and JWKS client."""
        self.tenant_id = os.environ.get(
            "AZURE_TENANT_ID", "fd799da1-bfc1-4234-a91c-72b3a1cb9e26"
        )
        self.client_id = os.environ.get("AZURE_CLIENT_ID")

        if not self.client_id:
            logger.warning("AZURE_CLIENT_ID not set")

        self.issuer_v2 = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        self.issuer_v1 = f"https://sts.windows.net/{self.tenant_id}/"
        self.jwks_uri_v2 = (
            f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        )
        self.jwks_uri_v1 = "https://login.microsoftonline.com/common/discovery/keys"

        try:
            self.jwks_client = PyJWKClient(self.jwks_uri_v1)
        except Exception as e:
            logger.warning(f"Failed v1.0 JWKS init, trying v2.0: {e}")
            try:
                self.jwks_client = PyJWKClient(self.jwks_uri_v2)
                logger.info("JWT middleware initialized with v2.0 fallback")
            except Exception as e2:
                logger.error(f"Failed to initialize JWKS clients: {e2}")
                self.jwks_client = None

    async def verify_token(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        Verify and decode a JWT token using Azure AD public keys.

        Args:
            credentials: Authorization header with bearer token.

        Returns:
            Decoded JWT payload containing user and group claims.

        Raises:
            HTTPException: If the token is invalid or verification fails.
        """
        token = credentials.credentials 
        webapp_audience = f"https://ssv{'-test' if env != 'prod' else ''}.azure.chevron.com"

        # Check for test environment
        if os.environ.get("TESTING") == "true":
            try:
                # In test environment, decode with test key
                payload = jwt.decode(
                    token,
                    key="test-key",
                    algorithms=["HS256"],
                    options={
                        "verify_exp": True,
                        "verify_aud": False,
                        "verify_iss": False,
                    }
                )
                logger.info("Test token validation succeeded")
                return payload
            except Exception as e:
                logger.error(f"Test token validation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Test token validation failed: {e}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        try:
            if self.jwks_client:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    key=signing_key.key,
                    algorithms=["RS256"],
                    audience=webapp_audience,
                    issuer=self.issuer_v1,
                    options={
                        "verify_exp": True,
                        "verify_aud": True,
                        "verify_iss": True,
                        "verify_signature": True,
                    },
                )
                logger.info("JWT validation succeeded (strict)")
            else:
                logger.error("JWKS client unavailable, cannot validate JWT.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="JWKS client unavailable, cannot validate JWT.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            username = payload.get("preferred_username", "unknown")
            groups = payload.get("groups", [])
            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidAudienceError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid audience",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidIssuerError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )


authentication_middleware = AuthMiddleware()


async def get_current_user(
    token_payload: Dict[str, Any] = Depends(authentication_middleware.verify_token),
) -> Dict[str, Any]:
    """
    Extract user identity and group membership from the validated JWT payload.

    Args:
        token_payload: Decoded JWT payload from verify_token().

    Returns:
        Dictionary containing user information.
    """
    return {
        "user_id": token_payload.get("oid"),
        "username": token_payload.get("preferred_username"),
        "name": token_payload.get("name"),
        "email": token_payload.get("upn") or token_payload.get("preferred_username"),
        "groups": token_payload.get("groups", []),
        "roles": token_payload.get("roles", []),
        "tenant_id": token_payload.get("tid"),
    }


def require_admin_group(required_groups: List[str] = None) -> Callable:
    """
    Dependency factory to check if user belongs to required admin groups.
    
    Args:
        required_groups: List of group IDs that are allowed access.
        
    Returns:
        Callable dependency that validates group membership.
    """
    if required_groups is None:
        required_groups = ["4490f665-1b85-49c7-9534-91909187e0ff",
        ]
    
    async def check_admin_access(
        token_payload: Dict[str, Any] = Depends(authentication_middleware.verify_token)
    ) -> Dict[str, Any]:
        """
        Verify that the current user belongs to at least one of the required admin groups.
        
        Args:
            token_payload: JWT token payload from verify_token dependency.
            
        Returns:
            User information dict if authorized.
            
        Raises:
            HTTPException: If user is not in any of the required groups.
        """
        user_email = token_payload.get("unique_name") 
        user_id = token_payload.get("oid")
        
        logger.info(f"Checking admin access for user: {user_email} (ID: {user_id})")
        
        access_control = AccessControl(client_id, client_secret, tenant_id)
        has_access = access_control.is_email_in_groups(user_email, required_groups)
        
        if not has_access:
            logger.warning(f"Access denied for user {user_email} (ID: {user_id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource. Admin access required."
            )
        
        logger.info(f"Admin access granted for user {user_email} (ID: {user_id})")
        
        return {
            "user_id": user_id,
            "username": token_payload.get("preferred_username"),
            "unique_name": user_email,
            "name": token_payload.get("name"),
            "email": user_email,
            "groups": token_payload.get("groups", []),
            "roles": token_payload.get("roles", []),
            "tenant_id": token_payload.get("tid"),
        }
    
    return check_admin_access