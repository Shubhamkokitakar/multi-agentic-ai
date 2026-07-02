from jose import JWTError, jwt
from authentication.auth import SECRET_KEY, ALGORITHM


def verify_token(token: str):

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email = payload.get("sub")
        role = payload.get("role")

        if not email:
            return None

        return {"email": email, "role": role}

    except JWTError:
        return None