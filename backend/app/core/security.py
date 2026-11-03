from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import bcrypt
import jwt
from app.core.config import settings


def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with configurable work factor (AC-44.1).
    Default work factor is rounds >= 12 to ensure brute-force resistance.
    """
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Constant-time comparison prevents timing attacks.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a signed JWT Access Token with claims and expiration.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a signed JWT Access Token.
    Raises jwt.PyJWTError if expired, tampered, or invalid.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Enforce password policy (AC-29.1):
    - Minimum length >= 8 characters
    - Contains at least 1 uppercase letter
    - Contains at least 1 lowercase letter
    - Contains at least 1 digit
    """
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False, f"Mật khẩu phải có độ dài tối thiểu {settings.MIN_PASSWORD_LENGTH} ký tự."
    if not any(c.isupper() for c in password):
        return False, "Mật khẩu phải chứa ít nhất 1 chữ hoa."
    if not any(c.islower() for c in password):
        return False, "Mật khẩu phải chứa ít nhất 1 chữ thường."
    if not any(c.isdigit() for c in password):
        return False, "Mật khẩu phải chứa ít nhất 1 chữ số."
    return True, "Hợp lệ"
