from __future__ import annotations
from dataclasses import dataclass, field
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token, GUEST_COLLECTIONS

bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    role: str
    collections: list[str] = field(default_factory=list)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def can_access(self, collection: str) -> bool:
        return self.is_admin or collection in self.collections


GUEST = CurrentUser(id="guest", role="guest", collections=GUEST_COLLECTIONS)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    """Returns authenticated user or guest (read-only on 'general')."""
    if credentials is None:
        return GUEST

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")

    return CurrentUser(
        id=payload["sub"],
        role=payload.get("role", "user"),
        collections=payload.get("collections", GUEST_COLLECTIONS),
    )


async def require_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role == "guest":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")
    return user


async def require_admin(user: CurrentUser = Depends(require_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Droits administrateur requis")
    return user
