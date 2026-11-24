from datetime import datetime, timedelta, timezone
import secrets
import string
import threading
from typing import Any, Dict, Optional, Tuple
import bcrypt
import jwt
from app.core.config import settings

_REVOKED_TOKENS: Dict[str, int] = {}
_REVOKED_LOCK = threading.Lock()


def _prune_revoked_tokens_locked(now_ts: int) -> None:
    expired = [key for key, exp_ts in _REVOKED_TOKENS.items() if exp_ts and exp_ts <= now_ts]
    for key in expired:
        _REVOKED_TOKENS.pop(key, None)


def revoke_token(token: str, exp: Optional[int] = None) -> None:
    """Blacklist a JWT token (by jti if present, else raw token) until expiration."""
    key = token
    exp_ts = exp or int((datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())
    try:
        payload = decode_access_token(token)
        if payload.get("jti"):
            key = str(payload["jti"])
        if payload.get("exp"):
            exp_ts = int(payload["exp"])
    except Exception:
        pass
    now_ts = int(datetime.now(timezone.utc).timestamp())
    with _REVOKED_LOCK:
        _prune_revoked_tokens_locked(now_ts)
        _REVOKED_TOKENS[key] = exp_ts


def is_token_revoked(token: str) -> bool:
    """Return True if the JWT token has been logged out / revoked."""
    now_ts = int(datetime.now(timezone.utc).timestamp())
    key = token
    try:
        payload = decode_access_token(token)
        if payload.get("jti"):
            key = str(payload["jti"])
    except Exception:
        pass
    with _REVOKED_LOCK:
        _prune_revoked_tokens_locked(now_ts)
        return key in _REVOKED_TOKENS or token in _REVOKED_TOKENS


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
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
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
    for _ in range(max(0, length - 4)):
        password_chars.append(secrets.choice(all_chars))

    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)
