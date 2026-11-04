from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, get_current_user
from app.core.security import (
    create_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
)

router = APIRouter(tags=["Auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập",
    description="Xác thực người dùng, cấp JWT Token hạn 8h (US-28). Sai 5 lần liên tiếp tự khóa 15 phút (AC-28.2).",
)
def login(
    req: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Đăng nhập hệ thống:
    - Nếu đúng: reset failed_login_count, cập nhật last_login_at, trả về JWT Token và User profile.
    - Nếu sai mật khẩu >= 5 lần liên tiếp: khóa tài khoản 15 phút, trả về HTTP 423 ACCOUNT_LOCKED (AC-28.2).
    - Nếu tài khoản is_active = False: trả về HTTP 403 ACCOUNT_DISABLED.
    """
    username = req.username.strip().lower()
    stmt = select(User).where(func.lower(User.username) == username)
    user = db.scalars(stmt).first()

    if not user:
        raise AppAPIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            message="Tên đăng nhập hoặc mật khẩu không chính xác.",
        )

    # 1. Kiểm tra trạng thái khóa tài khoản do nhập sai quá số lần (AC-28.2)
    now = datetime.now(timezone.utc)
    if user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)

        if locked_until > now:
            raise AppAPIException(
                status_code=status.HTTP_423_LOCKED,
                code="ACCOUNT_LOCKED",
                message=f"Tài khoản đang bị tạm khóa {settings.ACCOUNT_LOCKOUT_MINUTES} phút do nhập sai mật khẩu nhiều lần.",
            )
        else:
            # Thời hạn khóa đã hết -> tự động gỡ khóa
            user.locked_until = None
            user.failed_login_count = 0
            db.commit()

    # 2. Kiểm tra tài khoản có bị vô hiệu hóa không
    if not user.is_active:
        raise AppAPIException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="ACCOUNT_DISABLED",
            message="Tài khoản đã bị vô hiệu hóa.",
        )

    # 3. Xác thực mật khẩu
    if not verify_password(req.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
            db.commit()
            raise AppAPIException(
                status_code=status.HTTP_423_LOCKED,
                code="ACCOUNT_LOCKED",
                message=f"Tài khoản đã bị tạm khóa {settings.ACCOUNT_LOCKOUT_MINUTES} phút do nhập sai mật khẩu {settings.MAX_FAILED_LOGIN_ATTEMPTS} lần liên tiếp.",
            )
        db.commit()
        remaining_attempts = settings.MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_count
        raise AppAPIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            message=f"Tên đăng nhập hoặc mật khẩu không chính xác. Bạn còn {remaining_attempts} lần thử.",
        )

    # 4. Đăng nhập thành công -> Reset đếm lỗi và cập nhật thời điểm đăng nhập
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    db.refresh(user)

    # 5. Sinh JWT Token (hạn 8 giờ)
    role_code = user.role.code if user.role else ""
    token_claims = {
        "sub": str(user.id),
        "username": user.username,
        "role": role_code,
        "household_id": user.household_id,
        "must_change_password": user.must_change_password,
    }
    access_token = create_access_token(token_claims)

    return LoginResponse(
        token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Đăng xuất",
    description="Thu hồi phiên đăng nhập hiện tại (US-28).",
)
def logout(
    current_user: User = Depends(get_current_user),
) -> Response:
    """Đăng xuất khỏi hệ thống."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Thông tin tài khoản đang đăng nhập",
    description="Lấy thông tin profile người dùng và vai trò hiện tại (US-28).",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Lấy thông tin Profile tài khoản hiện tại kèm vai trò."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Đổi mật khẩu cá nhân",
    description=(
        "Cho phép mọi tài khoản đã xác thực đổi mật khẩu cá nhân (US-29, AC-29.1). "
        "Hoạt động bình thường ngay cả khi must_change_password = True. "
        "Nếu sai mật khẩu cũ trả về HTTP 400 WRONG_OLD_PASSWORD."
    ),
)
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """
    Đổi mật khẩu cá nhân:
    - Xác thực mật khẩu cũ: Nếu không khớp, trả về HTTP 400 với mã lỗi WRONG_OLD_PASSWORD.
    - Kiểm tra độ mạnh mật khẩu mới: độ dài >= 8, có ít nhất 1 chữ hoa, 1 chữ thường, 1 chữ số (AC-29.1).
    - Cập nhật password_hash (bcrypt rounds >= 12).
    - Gỡ cờ must_change_password = False.
    - Cập nhật thời điểm password_changed_at = now.
    - Trả về HTTP 204 No Content.
    """
    # 1. Xác thực mật khẩu cũ (bắt buộc trả 400 WRONG_OLD_PASSWORD, không dùng 401)
    if not verify_password(req.old_password, current_user.password_hash):
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="WRONG_OLD_PASSWORD",
            message="Mật khẩu cũ không chính xác.",
        )

    # 2. Kiểm tra độ mạnh mật khẩu mới theo chính sách hệ thống (AC-29.1)
    is_valid, error_msg = validate_password_strength(req.new_password)
    if not is_valid:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=error_msg,
            details=[{"field": "new_password", "message": error_msg}],
        )

    # 3. Băm mật khẩu mới và cập nhật trạng thái người dùng
    now = datetime.now(timezone.utc)
    current_user.password_hash = get_password_hash(req.new_password)
    current_user.must_change_password = False
    current_user.password_changed_at = now
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
