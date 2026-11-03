import pytest
from datetime import timedelta
from sqlalchemy import select
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    validate_password_strength,
)
from app.models.user import AuditLog


# =====================================================================
# 1. KIỂM THỬ TIÊU CHÍ AC-44.1: BĂM MẬT KHẨU BCRYPT (ROUNDS >= 12)
# =====================================================================

def test_ac44_1_bcrypt_hash_cost_factor_ge_12():
    """
    Kiểm thử AC-44.1: Mật khẩu bắt buộc được băm bằng bcrypt với salt rounds >= 12.
    Định dạng chuỗi bcrypt: $2b$<rounds>$...
    """
    plain_password = "SecretPassword@2026"
    hashed = get_password_hash(plain_password)

    # Kiểm tra tiền tố bcrypt version và cost factor
    parts = hashed.split("$")
    assert len(parts) >= 4, "Hash bcrypt phải có ít nhất 4 thành phần"
    assert parts[1] in ("2a", "2b", "2y"), f"Thuật toán không phải bcrypt: {parts[1]}"
    
    rounds = int(parts[2])
    assert rounds >= 12, f"AC-44.1 thất bại: Số rounds ({rounds}) nhỏ hơn 12"

    # Kiểm tra tính đúng đắn khi xác thực
    assert verify_password(plain_password, hashed) is True
    assert verify_password("WrongPassword@2026", hashed) is False


def test_password_strength_policy():
    """
    Kiểm thử chính sách độ mạnh mật khẩu (AC-29.1):
    >= 8 ký tự, gồm ít nhất 1 chữ hoa, 1 chữ thường, 1 chữ số.
    """
    # Quá ngắn (< 8 ký tự)
    valid, msg = validate_password_strength("Ab1!")
    assert valid is False
    assert "8 ký tự" in msg

    # Thiếu chữ hoa
    valid, msg = validate_password_strength("lowercase123")
    assert valid is False
    assert "chữ hoa" in msg

    # Thiếu chữ thường
    valid, msg = validate_password_strength("UPPERCASE123")
    assert valid is False
    assert "chữ thường" in msg

    # Thiếu chữ số
    valid, msg = validate_password_strength("ValidNoDigits")
    assert valid is False
    assert "chữ số" in msg

    # Hợp lệ
    valid, msg = validate_password_strength("StrongPass@2026")
    assert valid is True


# =====================================================================
# 2. KIỂM THỬ JWT ACCESS TOKEN
# =====================================================================

def test_jwt_token_creation_and_decoding():
    """Kiểm thử sinh và giải mã JWT token kèm theo đầy đủ claims."""
    payload_data = {
        "sub": "100",
        "username": "test_user",
        "role": "ACCOUNTANT",
        "household_id": 50,
        "must_change_password": False
    }
    token = create_access_token(payload_data, expires_delta=timedelta(minutes=30))
    decoded = decode_access_token(token)

    assert decoded["sub"] == "100"
    assert decoded["username"] == "test_user"
    assert decoded["role"] == "ACCOUNTANT"
    assert decoded["household_id"] == 50
    assert decoded["must_change_password"] is False
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_token_expired():
    """Kiểm thử từ chối token khi đã hết hạn."""
    payload_data = {"sub": "1", "username": "expired_user", "role": "ADMIN"}
    # Tạo token đã hết hạn 10 giây trước
    token = create_access_token(payload_data, expires_delta=timedelta(seconds=-10))

    with pytest.raises(Exception):
        decode_access_token(token)


# =====================================================================
# 3. KIỂM THỬ ENDPOINT SỨC KHỎE HỆ THỐNG (HEALTH CHECK)
# =====================================================================

def test_health_check_endpoint(client):
    """Kiểm thử endpoint GET /api/v1/health."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "BlueMoon" in data["app"]


# =====================================================================
# 4. KIỂM THỬ PHÂN QUYỀN RBAC GUARD (US-31, AC-31.1)
# =====================================================================

def test_rbac_guard_admin_access_allowed(client, auth_headers_admin):
    """Tài khoản ADMIN truy cập endpoint yêu cầu ADMIN thành công."""
    response = client.get("/api/v1/test/admin-only", headers=auth_headers_admin)
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_rbac_guard_resident_access_forbidden(client, auth_headers_resident_101, db_session):
    """Tài khoản RESIDENT truy cập endpoint yêu cầu ADMIN bị từ chối 403 FORBIDDEN."""
    response = client.get("/api/v1/test/admin-only", headers=auth_headers_resident_101)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"

    # Kiểm tra xem có ghi nhật ký ACCESS_DENIED vào audit_logs không
    stmt = select(AuditLog).where(
        AuditLog.action == "ACCESS_DENIED",
        AuditLog.user_id == 3
    )
    log = db_session.scalars(stmt).first()
    assert log is not None
    assert "không có quyền" in log.reason


# =====================================================================
# 5. KIỂM THỬ TIÊU CHÍ AC-44.2: CHỐNG LỖ HỔNG IDOR
# =====================================================================

def test_ac44_2_idor_same_household_access_allowed(client, auth_headers_resident_101):
    """Cư dân hộ 101 truy cập dữ liệu của chính hộ 101 thành công (200 OK)."""
    response = client.get("/api/v1/test/households/101", headers=auth_headers_resident_101)
    assert response.status_code == 200
    data = response.json()
    assert data["household_id"] == 101


def test_ac44_2_idor_cross_household_blocked_returns_404(
    client,
    auth_headers_resident_101,
    db_session
):
    """
    Kiểm thử AC-44.2: Cư dân hộ 101 cố ý đổi ID sang hộ 102 trên URL.
    Hệ thống BẮT BUỘC trả về 404 NOT_FOUND (không trả 403) và ghi Audit Log.
    """
    response = client.get("/api/v1/test/households/102", headers=auth_headers_resident_101)

    # AC-44.2: Phải trả về 404 NOT_FOUND
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"

    # Kiểm tra nhật ký kiểm toán ghi nhận IDOR attempt
    stmt = select(AuditLog).where(
        AuditLog.action == "ACCESS_DENIED",
        AuditLog.user_id == 3,
        AuditLog.entity_id == "102"
    )
    audit_record = db_session.scalars(stmt).first()
    assert audit_record is not None
    assert "IDOR attempt" in audit_record.reason


def test_admin_can_access_any_household(client, auth_headers_admin):
    """Admin có quyền truy cập thông tin của bất kỳ hộ nào (101 hoặc 102)."""
    res1 = client.get("/api/v1/test/households/101", headers=auth_headers_admin)
    assert res1.status_code == 200

    res2 = client.get("/api/v1/test/households/102", headers=auth_headers_admin)
    assert res2.status_code == 200


# =====================================================================
# 6. KIỂM THỬ CẤU TRÚC LỖI CHUẨN HÓA (ERROR ENVELOPE SPEC)
# =====================================================================

def test_unauthenticated_request_format(client):
    """Request không có token trả về 401 UNAUTHENTICATED đúng định dạng Error."""
    response = client.get("/api/v1/test/admin-only")
    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert data["code"] == "UNAUTHENTICATED"
    assert isinstance(data.get("details"), list)


def test_not_found_endpoint_format(client):
    """Gọi đường dẫn không tồn tại trả về 404 NOT_FOUND đúng chuẩn Error."""
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"
    assert "message" in data
