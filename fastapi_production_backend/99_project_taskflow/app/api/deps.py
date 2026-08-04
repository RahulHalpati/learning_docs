"""Shared API dependencies: current user, pagination, role guards."""
from typing import Annotated

import jwt
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.exceptions import AuthError, PermissionDeniedError
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    try:
        payload = security.decode_token(token)
    except jwt.PyJWTError:
        raise AuthError("Could not validate credentials.")
    if payload.get("type") != security.ACCESS:
        raise AuthError("Not an access token.")
    user = await UserRepository(db).get(int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != Role.admin:
        raise PermissionDeniedError("Admin privileges required.")
    return user


class Pagination:
    """`page`/`size` query params, bounded to sane limits."""
    def __init__(
        self,
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
    ):
        self.page = page
        self.size = size


PageParams = Annotated[Pagination, Depends()]
