"""Password hashing (bcrypt via pwdlib) and JWT creation/decoding."""
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# pwdlib is the modern, maintained successor to passlib. We use bcrypt explicitly
# (install `pwdlib[argon2]` and PasswordHash.recommended() for argon2 in production).
_password_hash = PasswordHash((BcryptHasher(),))

ACCESS = "access"
REFRESH = "refresh"


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,               # the user id
        "type": token_type,           # access | refresh
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(subject, ACCESS,
                         timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, REFRESH,
                         timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict:
    """Decode & validate a JWT. Raises jwt.PyJWTError on invalid/expired tokens."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
