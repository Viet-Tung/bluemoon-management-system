import re
import secrets
import string
from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.core.security import get_password_hash
from app.models.user import AuditLog, Role, User
from app.schemas.auth import UserResponse
from app.schemas.user import (
    TempPassword,
    UserCreate,
    UserPage,
    UserUpdate,
    UserWithTempPassword,
)

router = APIRouter(tags=["Users"])


def generate_secure_temporary_password(length: int = 12) -> str:
    """
    Tự động sinh mật khẩu tạm thời ngẫu nhiên an toàn (AC-29.1, AC-44.1):
    - Độ dài tối thiểu 12 ký tự
    - Đảm bảo chứa ít nhất 1 chữ cái hoa, 1 chữ cái thường, 1 chữ số, 1 ký tự đặc biệt
    """
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*"

    password_chars = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    all_chars = upper + lower + digits + special
    for _ in range(length - 4):
        password_chars.append(secrets.choice(all_chars))

    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


@router.get(
    "",
    response_model=UserPage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách tài khoản",
    description="Xem danh sách tài khoản người dùng, hỗ trợ phân trang và tìm kiếm (US-30). Phân quyền: ADMIN.",
)
def list_users(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi trên một trang"),
    q: Optional[str] = Query(default=None, description="Tìm theo username hoặc họ và tên"),
    role: Optional[str] = Query(default=None, description="Lọc theo mã vai trò: ADMIN, ACCOUNTANT, TREASURER, RESIDENT"),
    is_active: Optional[bool] = Query(default=None, description="Lọc theo trạng thái hoạt động"),
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserPage:
    """Lấy danh sách người dùng có phân trang và bộ lọc tìm kiếm."""
    stmt = select(User).join(User.role)

    # 1. Lọc theo từ khóa tìm kiếm (username hoặc full_name)
    if q and q.strip():
        search_kw = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.username).ilike(search_kw),
                func.lower(User.full_name).ilike(search_kw),
            )
        )

    # 2. Lọc theo mã vai trò
    if role and role.strip():
        role_code = role.strip().upper()
        stmt = stmt.where(Role.code == role_code)

    # 3. Lọc theo trạng thái hoạt động
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    # Đếm tổng số bản ghi thỏa mãn điều kiện
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0

    # Phân trang và sắp xếp theo ID tăng dần
    items_stmt = stmt.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size)
    users = db.scalars(items_stmt).all()

    return UserPage(
        page=page,
        page_size=page_size,
        total=total,
        items=[UserResponse.model_validate(u) for u in users],
    )


@router.post(
    "",
    response_model=UserWithTempPassword,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tài khoản nhân sự",
    description="Tạo mới tài khoản nhân sự (ADMIN, ACCOUNTANT, TREASURER). Tự động sinh mật khẩu tạm thời (US-30). Phân quyền: ADMIN.",
)
def create_user(
    req: UserCreate,
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserWithTempPassword:
    """Tạo tài khoản người dùng mới với mật khẩu tạm thời an toàn."""
    normalized_username = req.username.strip().lower()

    # 1. Kiểm tra trùng lặp username (case-insensitive)
    existing_stmt = select(User).where(func.lower(User.username) == normalized_username)
    if db.scalars(existing_stmt).first():
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_USERNAME",
            message=f"Tên đăng nhập '{req.username.strip()}' đã tồn tại trong hệ thống.",
        )

    # 2. Kiểm tra vai trò hợp lệ
    role = db.scalar(select(Role).where(Role.id == req.role_id))
    if not role:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=f"Vai trò với ID {req.role_id} không tồn tại trong hệ thống.",
        )

    # Ràng buộc: Chỉ tạo tài khoản nhân sự, cấm tạo tài khoản RESIDENT qua endpoint này
    if role.code == "RESIDENT":
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Không thể tạo trực tiếp tài khoản Cư dân (RESIDENT). Tài khoản cư dân được hệ thống tự động sinh khi khai báo Hộ gia đình.",
        )

    # 3. Tự sinh mật khẩu tạm thời đạt chuẩn AC-29.1, băm bcrypt rounds >= 12
    temp_password = generate_secure_temporary_password()
    hashed_password = get_password_hash(temp_password)

    new_user = User(
        username=req.username.strip(),
        password_hash=hashed_password,
        full_name=req.full_name.strip(),
        email=req.email.strip() if req.email else None,
        phone=req.phone.strip() if req.phone else None,
        role_id=role.id,
        is_active=True,
        must_change_password=True,
        failed_login_count=0,
        locked_until=None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    user_response = UserResponse.model_validate(new_user)
    return UserWithTempPassword(
        **user_response.model_dump(),
        temporary_password=temp_password,
        temp_password=temp_password,
    )


@router.get(
    "/{userId}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết tài khoản",
    description="Xem thông tin chi tiết một tài khoản theo ID (US-30). Phân quyền: ADMIN.",
)
def get_user(
    userId: int = Path(..., ge=1, description="ID người dùng"),
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Lấy thông tin chi tiết tài khoản người dùng."""
    user = db.scalar(select(User).where(User.id == userId))
    if not user:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message=f"Không tìm thấy người dùng có ID {userId}.",
        )
    return UserResponse.model_validate(user)


@router.patch(
    "/{userId}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật thông tin tài khoản",
    description="Cập nhật các thông tin cơ bản của người dùng (US-30). Phân quyền: ADMIN.",
)
def update_user(
    req: UserUpdate,
    userId: int = Path(..., ge=1, description="ID người dùng"),
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Cập nhật thông tin tài khoản người dùng."""
    user = db.scalar(select(User).where(User.id == userId))
    if not user:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message=f"Không tìm thấy người dùng có ID {userId}.",
        )

    if req.full_name is not None:
        user.full_name = req.full_name.strip()
    if req.email is not None:
        user.email = req.email.strip() if req.email else None
    if req.phone is not None:
        user.phone = req.phone.strip() if req.phone else None
    if req.is_active is not None:
        user.is_active = req.is_active

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post(
    "/{userId}/lock",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Khóa tài khoản",
    description="Khóa tài khoản tức thì. Cấm Admin tự khóa chính mình (US-30). Phân quyền: ADMIN.",
)
def lock_user(
    request: Request,
    userId: int = Path(..., ge=1, description="ID người dùng"),
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Khóa tài khoản người dùng ngay lập tức."""
    # Ràng buộc: Cấm Admin tự khóa chính mình
    if current_user.id == userId:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="CANNOT_LOCK_SELF",
            message="Quản trị viên không được phép tự khóa tài khoản của chính mình.",
        )

    user = db.scalar(select(User).where(User.id == userId))
    if not user:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message=f"Không tìm thấy người dùng có ID {userId}.",
        )

    old_active = user.is_active
    user.is_active = False

    # Ghi nhận Audit Log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="LOCK_USER",
        entity_type="USER",
        entity_id=str(user.id),
        old_value={"is_active": old_active},
        new_value={"is_active": False},
        reason=f"Admin '{current_user.username}' đã khóa tài khoản '{user.username}'.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/{userId}/unlock",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Mở khóa tài khoản",
    description="Mở khóa tài khoản tức thì, reset số lần đăng nhập sai (US-30). Phân quyền: ADMIN.",
)
def unlock_user(
    request: Request,
    userId: int = Path(..., ge=1, description="ID người dùng"),
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Mở khóa tài khoản người dùng ngay lập tức."""
    user = db.scalar(select(User).where(User.id == userId))
    if not user:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message=f"Không tìm thấy người dùng có ID {userId}.",
        )

    old_state = {
        "is_active": user.is_active,
        "failed_login_count": user.failed_login_count,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
    }

    user.is_active = True
    user.failed_login_count = 0
    user.locked_until = None

    # Ghi nhận Audit Log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="UNLOCK_USER",
        entity_type="USER",
        entity_id=str(user.id),
        old_value=old_state,
        new_value={"is_active": True, "failed_login_count": 0, "locked_until": None},
        reason=f"Admin '{current_user.username}' đã mở khóa tài khoản '{user.username}'.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/{userId}/reset-password",
    response_model=TempPassword,
    status_code=status.HTTP_200_OK,
    summary="Cấp lại mật khẩu tạm",
    description="Cấp lại mật khẩu tạm thời cho tài khoản, buộc đổi ở lần đăng nhập tới (US-30, US-29). Phân quyền: ADMIN.",
)
def reset_user_password(
    request: Request,
    userId: int = Path(..., ge=1, description="ID người dùng"),
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> TempPassword:
    """Cấp lại mật khẩu tạm thời đạt chuẩn an toàn."""
    user = db.scalar(select(User).where(User.id == userId))
    if not user:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message=f"Không tìm thấy người dùng có ID {userId}.",
        )

    temp_password = generate_secure_temporary_password()
    user.password_hash = get_password_hash(temp_password)
    user.must_change_password = True
    user.failed_login_count = 0
    user.locked_until = None

    # Ghi nhận Audit Log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="RESET_PASSWORD",
        entity_type="USER",
        entity_id=str(user.id),
        old_value={"must_change_password": user.must_change_password},
        new_value={"must_change_password": True},
        reason=f"Admin '{current_user.username}' đã cấp lại mật khẩu tạm cho tài khoản '{user.username}'.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()

    return TempPassword(
        temporary_password=temp_password,
        temp_password=temp_password,
    )

