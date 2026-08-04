"""Auth service — registration, login, token refresh."""
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.exceptions import AuthError, ConflictError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.token import TokenPair
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, session: AsyncSession):
        self.users = UserRepository(session)

    async def register(self, data: UserCreate) -> User:
        if await self.users.get_by_email(data.email):
            raise ConflictError("A user with this email already exists.")
        user = User(
            email=data.email,
            hashed_password=security.hash_password(data.password),
            full_name=data.full_name,
        )
        return await self.users.create(user)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if not user or not security.verify_password(password, user.hashed_password):
            raise AuthError("Incorrect email or password.")
        if not user.is_active:
            raise AuthError("Account is disabled.")
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=security.create_access_token(str(user.id)),
            refresh_token=security.create_refresh_token(str(user.id)),
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = security.decode_token(refresh_token)
        except jwt.PyJWTError:
            raise AuthError("Invalid or expired refresh token.")
        if payload.get("type") != security.REFRESH:
            raise AuthError("Not a refresh token.")
        user = await self.users.get(int(payload["sub"]))
        if not user or not user.is_active:
            raise AuthError("User no longer valid.")
        return self.issue_tokens(user)
