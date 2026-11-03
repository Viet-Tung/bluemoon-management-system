from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
import jwt

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import AuditLog, User
from app.schemas.auth import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class AppAPIException(HTTPException):
    """
    Standardized Application Exception yielding compliant Error responses.
    Conforms 100% to docs/API_CONTRACT.md (Chapter 1.2).
    """
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[List[dict]] = None,
        headers: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details or []


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticate request via JWT Bearer Token.
    Returns the authenticated User model with associated Role.
    """
    if not token:
        # Check header manually if auto_error=False
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise AppAPIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHENTICATED",
            message="Chưa đăng nhập hoặc thiếu token xác thực."
        )

    try:
        payload_data = decode_access_token(token)
        payload = TokenPayload(**payload_data)
        user_id = int(payload.sub)
    except (jwt.PyJWTError, ValueError, Exception):
        raise AppAPIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHENTICATED",
            message="Token không hợp lệ hoặc đã hết hạn."
        )

    stmt = select(User).where(User.id == user_id)
    user = db.scalars(stmt).first()

    if not user:
        raise AppAPIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHENTICATED",
            message="Người dùng không tồn tại hoặc đã bị xóa."
        )

    if not user.is_active:
        raise AppAPIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHENTICATED",
            message="Tài khoản đã bị vô hiệu hóa."
        )

    # Attach current user to request state for audit logging
    request.state.current_user = user
    return user


def require_roles(*allowed_roles: str) -> Callable:
    """
    Role-Based Access Control Guard (US-31, AC-31.1).
    Validates that current_user.role.code matches one of allowed_roles.
    """
    def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        user_role_code = current_user.role.code if current_user.role else ""
        if allowed_roles and user_role_code not in allowed_roles:
            # Ghi log ACCESS_DENIED vào audit_logs
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            audit = AuditLog(
                user_id=current_user.id,
                action="ACCESS_DENIED",
                entity_type="ENDPOINT",
                entity_id=request.url.path,
                reason=f"Vai trò {user_role_code} không có quyền truy cập endpoint này.",
                ip_address=client_ip,
                user_agent=user_agent
            )
            db.add(audit)
            db.commit()

            raise AppAPIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FORBIDDEN",
                message=f"Tài khoản không đủ quyền hạn ({allowed_roles})."
            )
        return current_user

    return role_checker


def check_household_access(
    household_id: int,
    current_user: User,
    db: Session,
    request: Request
) -> None:
    """
    IDOR Defense Mechanism (US-44, AC-44.2).
    If user is RESIDENT and attempts to access a household other than their own,
    system records an audit log and responds with 404 NOT_FOUND.
    """
    if current_user.role and current_user.role.code == "RESIDENT":
        if current_user.household_id != household_id:
            # Ghi nhận vi phạm IDOR
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            audit = AuditLog(
                user_id=current_user.id,
                action="ACCESS_DENIED",
                entity_type="HOUSEHOLD",
                entity_id=str(household_id),
                reason=f"IDOR attempt: Cư dân hộ {current_user.household_id} cố ý truy cập hộ {household_id}.",
                ip_address=client_ip,
                user_agent=user_agent
            )
            db.add(audit)
            db.commit()

            # Bắt buộc trả về 404 NOT_FOUND để chống rò rỉ ID
            raise AppAPIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
                message="Không tìm thấy thông tin hộ gia đình."
            )

