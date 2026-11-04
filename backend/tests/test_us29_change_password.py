"""
Unit & Integration Tests for US-29: Đổi mật khẩu cá nhân (Change Password).
Black-Box Testing Specification according to AC-29.1, docs/openapi.yaml & docs/API_CONTRACT.md:
- Endpoint: POST /api/v1/auth/change-password
- Authentication: Yêu cầu Bearer JWT Token hợp lệ (tất cả vai trò: ADMIN, ACCOUNTANT, TREASURER, RESIDENT).
- Phản hồi thành công: HTTP 204 No Content.
- Xác thực mật khẩu cũ: HTTP 400 Bad Request với code="WRONG_OLD_PASSWORD", message="Mật khẩu cũ không chính xác." (TUYỆT ĐỐI không phải 401).
- Chính sách mật khẩu mới (AC-29.1): Tối thiểu 8 ký tự, ít nhất 1 chữ hoa, 1 chữ thường, 1 chữ số.
  Nếu không đạt: HTTP 400 Bad Request với code="VALIDATION_ERROR".
- Chuyển đổi trạng thái tài khoản: Hạ cờ must_change_password=False, cập nhật password_changed_at.
- Kiểm tra tính bất biến của các trường dữ liệu người dùng khác.
- Kiểm tra bảo mật Token (hết hạn, thiếu token, token giả mạo, tài khoản bị vô hiệu hóa).
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import Role, User


# =====================================================================
# HẰNG SỐ & HÀM TIỆN ÍCH DÙNG CHUNG TRONG TEST
# =====================================================================

ENDPOINT_CHANGE_PASSWORD = f"{settings.API_V1_STR}/auth/change-password"
ENDPOINT_LOGIN = f"{settings.API_V1_STR}/auth/login"

# Mã băm tính toán sẵn một lần duy nhất tại module level để tối ưu hiệu năng
HASH_ADMIN = get_password_hash("AdminPass123!")
HASH_ACCOUNTANT = get_password_hash("AccPass123!")
HASH_RESIDENT = get_password_hash("ResPass123!")
HASH_TREASURER = get_password_hash("TreasurerPass123!")

DEFAULT_HASH_MAP = {
    1: HASH_ADMIN,
    2: HASH_ACCOUNTANT,
    3: HASH_RESIDENT,
    4: HASH_RESIDENT,
    5: HASH_TREASURER,
}


def make_auth_header(
    user_id: int,
    username: str = "test_user",
    role: str = "RESIDENT",
    household_id: int = None,
    must_change_password: bool = False,
    expires_delta: timedelta = None,
) -> dict:
    """Sinh Bearer Authorization header từ JWT claims."""
    claims = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "household_id": household_id,
        "must_change_password": must_change_password,
    }
    token = create_access_token(claims, expires_delta=expires_delta)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def restore_seeded_users(db_session):
    """
    Fixture tự động khôi phục mật khẩu và cờ trạng thái của các tài khoản sau mỗi test case,
    đảm bảo tính cô lập độc lập tuyệt đối giữa các test case.
    """
    yield
    for uid, original_hash in DEFAULT_HASH_MAP.items():
        user = db_session.get(User, uid)
        if user:
            user.password_hash = original_hash
            user.must_change_password = False
            user.is_active = True
            user.password_changed_at = None
    db_session.commit()


@pytest.fixture
def ensure_treasurer_user(db_session):
    """Đảm bảo tài khoản Thủ quỹ (Role TREASURER id=3) tồn tại trong database SQLite."""
    user = db_session.get(User, 5)
    if not user:
        user = User(
            id=5,
            username="treasurer_test",
            password_hash=HASH_TREASURER,
            full_name="Thủ Quỹ Test",
            email="treasurer@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(user)
        db_session.commit()
    else:
        user.password_hash = HASH_TREASURER
        user.must_change_password = False
        user.is_active = True
        user.password_changed_at = None
        db_session.commit()
    return user


# =====================================================================
# NHÓM 1: HAPPY PATHS - ĐỔI MẬT KHẨU THÀNH CÔNG CHO 4 VAI TRÒ
# (Admin, Accountant, Treasurer, Resident)
# =====================================================================

def test_change_password_happy_path_admin(client, db_session):
    """
    Happy Path - Quản trị viên (ADMIN) đổi mật khẩu:
    - HTTP 204 No Content.
    - Database: password_hash thay đổi, verify_password thành công với pass mới.
    - Database: must_change_password=False, password_changed_at được thiết lập.
    - Đăng nhập mới với mật khẩu mới thành công (HTTP 200).
    - Đăng nhập với mật khẩu cũ thất bại (HTTP 401 INVALID_CREDENTIALS).
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    old_pwd = "AdminPass123!"
    new_pwd = "NewAdminPass2026!"

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": old_pwd, "new_password": new_pwd},
    )
    assert res.status_code == 204
    assert res.content == b""

    # Kiểm tra Database
    user = db_session.get(User, 1)
    assert verify_password(new_pwd, user.password_hash) is True
    assert verify_password(old_pwd, user.password_hash) is False
    assert user.must_change_password is False
    assert user.password_changed_at is not None

    # Xác thực đăng nhập với mật khẩu mới
    login_new = client.post(
        ENDPOINT_LOGIN,
        json={"username": "admin_test", "password": new_pwd},
    )
    assert login_new.status_code == 200
    assert "token" in login_new.json()

    # Xác thực mật khẩu cũ không còn tác dụng
    login_old = client.post(
        ENDPOINT_LOGIN,
        json={"username": "admin_test", "password": old_pwd},
    )
    assert login_old.status_code == 401
    assert login_old.json()["code"] == "INVALID_CREDENTIALS"


def test_change_password_happy_path_accountant(client, db_session):
    """
    Happy Path - Kế toán (ACCOUNTANT) đổi mật khẩu thành công:
    - HTTP 204 No Content.
    - Kiểm tra cập nhật DB và chu kỳ đăng nhập sau đổi.
    """
    headers = make_auth_header(2, "accountant_test", "ACCOUNTANT")
    old_pwd = "AccPass123!"
    new_pwd = "NewAccPass2026@"

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": old_pwd, "new_password": new_pwd},
    )
    assert res.status_code == 204
    assert res.content == b""

    user = db_session.get(User, 2)
    assert verify_password(new_pwd, user.password_hash) is True
    assert verify_password(old_pwd, user.password_hash) is False
    assert user.must_change_password is False
    assert user.password_changed_at is not None

    # Đăng nhập với mật khẩu mới OK
    login_res = client.post(
        ENDPOINT_LOGIN,
        json={"username": "accountant_test", "password": new_pwd},
    )
    assert login_res.status_code == 200

    # Đăng nhập với mật khẩu cũ FAIL
    login_fail = client.post(
        ENDPOINT_LOGIN,
        json={"username": "accountant_test", "password": old_pwd},
    )
    assert login_fail.status_code == 401


def test_change_password_happy_path_resident_101(client, db_session):
    """
    Happy Path - Cư dân hộ 101 (RESIDENT) đổi mật khẩu thành công:
    - HTTP 204 No Content.
    - Database cập nhật chuẩn xác.
    """
    headers = make_auth_header(3, "resident_101", "RESIDENT", household_id=101)
    old_pwd = "ResPass123!"
    new_pwd = "NewRes101Pass#2026"

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": old_pwd, "new_password": new_pwd},
    )
    assert res.status_code == 204
    assert res.content == b""

    user = db_session.get(User, 3)
    assert verify_password(new_pwd, user.password_hash) is True
    assert user.must_change_password is False
    assert user.password_changed_at is not None

    login_res = client.post(
        ENDPOINT_LOGIN,
        json={"username": "resident_101", "password": new_pwd},
    )
    assert login_res.status_code == 200


def test_change_password_happy_path_resident_102(client, db_session):
    """
    Happy Path - Cư dân hộ 102 (RESIDENT) đổi mật khẩu thành công.
    """
    headers = make_auth_header(4, "resident_102", "RESIDENT", household_id=102)
    old_pwd = "ResPass123!"
    new_pwd = "NewRes102Pass$2026"

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": old_pwd, "new_password": new_pwd},
    )
    assert res.status_code == 204

    user = db_session.get(User, 4)
    assert verify_password(new_pwd, user.password_hash) is True
    assert user.must_change_password is False

    login_res = client.post(
        ENDPOINT_LOGIN,
        json={"username": "resident_102", "password": new_pwd},
    )
    assert login_res.status_code == 200


def test_change_password_happy_path_treasurer(client, db_session, ensure_treasurer_user):
    """
    Happy Path - Thủ quỹ (TREASURER) đổi mật khẩu thành công:
    - HTTP 204 No Content.
    - Database cập nhật và đăng nhập thành công.
    """
    headers = make_auth_header(5, "treasurer_test", "TREASURER")
    old_pwd = "TreasurerPass123!"
    new_pwd = "NewTreasurerPass2026!"

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": old_pwd, "new_password": new_pwd},
    )
    assert res.status_code == 204
    assert res.content == b""

    user = db_session.get(User, 5)
    assert verify_password(new_pwd, user.password_hash) is True
    assert user.must_change_password is False

    login_res = client.post(
        ENDPOINT_LOGIN,
        json={"username": "treasurer_test", "password": new_pwd},
    )
    assert login_res.status_code == 200


# =====================================================================
# NHÓM 2: KỊCH BẢN BẮT BUỘC ĐỔI MẬT KHẨU (must_change_password = True)
# =====================================================================

def test_change_password_when_must_change_password_is_true_admin(client, db_session):
    """
    Tài khoản Admin ban đầu có cờ must_change_password=True:
    - Đổi mật khẩu thành công (HTTP 204).
    - Cờ must_change_password trong DB được hạ xuống False.
    - Đăng nhập mới trả về user.must_change_password == False.
    """
    user = db_session.get(User, 1)
    user.must_change_password = True
    db_session.commit()

    headers = make_auth_header(1, "admin_test", "ADMIN", must_change_password=True)
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "FreshAdminPass2026!"},
    )
    assert res.status_code == 204

    db_session.refresh(user)
    assert user.must_change_password is False

    # Đăng nhập lại để xác thực response
    login_res = client.post(
        ENDPOINT_LOGIN,
        json={"username": "admin_test", "password": "FreshAdminPass2026!"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["must_change_password"] is False


def test_change_password_when_must_change_password_is_true_resident(client, db_session):
    """
    Tài khoản Cư dân ban đầu có cờ must_change_password=True:
    - Đổi mật khẩu thành công (HTTP 204).
    - Cờ must_change_password tự động chuyển thành False.
    """
    user = db_session.get(User, 3)
    user.must_change_password = True
    db_session.commit()

    headers = make_auth_header(3, "resident_101", "RESIDENT", household_id=101, must_change_password=True)
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "ResPass123!", "new_password": "FreshResidentPass2026!"},
    )
    assert res.status_code == 204

    db_session.refresh(user)
    assert user.must_change_password is False


def test_change_password_when_must_change_password_is_true_accountant(client, db_session):
    """
    Kế toán có cờ must_change_password=True đổi mật khẩu thành công và cờ được gỡ.
    """
    user = db_session.get(User, 2)
    user.must_change_password = True
    db_session.commit()

    headers = make_auth_header(2, "accountant_test", "ACCOUNTANT", must_change_password=True)
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AccPass123!", "new_password": "FreshAccountant2026!"},
    )
    assert res.status_code == 204

    db_session.refresh(user)
    assert user.must_change_password is False


def test_change_password_when_must_change_password_is_true_treasurer(client, db_session, ensure_treasurer_user):
    """
    Thủ quỹ có cờ must_change_password=True đổi mật khẩu thành công và cờ được gỡ.
    """
    user = db_session.get(User, 5)
    user.must_change_password = True
    db_session.commit()

    headers = make_auth_header(5, "treasurer_test", "TREASURER", must_change_password=True)
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "TreasurerPass123!", "new_password": "FreshTreasurer2026!"},
    )
    assert res.status_code == 204

    db_session.refresh(user)
    assert user.must_change_password is False


def test_change_password_token_with_must_change_flag_is_accepted(client):
    """
    Xác nhận endpoint /change-password chấp nhận và xử lý token mang claim must_change_password=True
    (người dùng không bị chặn truy cập endpoint đổi mật khẩu khi bắt buộc đổi mật khẩu).
    """
    headers = make_auth_header(1, "admin_test", "ADMIN", must_change_password=True)
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "PassChangeAccepted123!"},
    )
    assert res.status_code == 204


# =====================================================================
# NHÓM 3: XÁC THỰC MẬT KHẨU CŨ SAI (HTTP 400 WRONG_OLD_PASSWORD)
# (Tuyệt đối trả về HTTP 400, không được trả về HTTP 401)
# =====================================================================

@pytest.mark.parametrize("wrong_old_pwd", [
    "adminpass123!",        # Sai chữ hoa
    "ADMINPASS123!",        # Toàn bộ in hoa
    "AdminPass123",         # Thiếu ký tự đặc biệt cuối
    "AdminPass123! ",       # Thừa khoảng trắng cuối
    " AdminPass123!",       # Thừa khoảng trắng đầu
    "Admin_Pass123!",       # Thừa ký tự gạch dưới giữa
    "AdminPass123@",        # Sai ký tự đặc biệt
    "AdminPass456!",        # Sai cụm số
    "WrongPassword123!",    # Mật khẩu hoàn toàn khác
    "AccPass123!",          # Nhầm mật khẩu của role Kế toán
    "ResPass123!",          # Nhầm mật khẩu của role Cư dân
    "x",                    # Một ký tự duy nhất sai
    "   ",                  # Chuỗi chỉ toàn khoảng trắng
    "AdminРass123!",        # Ký tự đồng dạng Cyrillic P (\u0420)
    "' OR '1'='1",          # Thử nghiệm SQL Injection
])
def test_change_password_wrong_old_password_variants(client, db_session, wrong_old_pwd):
    """
    Xác thực mật khẩu cũ sai:
    - HTTP 400 Bad Request (TUYỆT ĐỐI không phải 401).
    - code == 'WRONG_OLD_PASSWORD'.
    - message == 'Mật khẩu cũ không chính xác.'.
    - Database: password_hash KHÔNG thay đổi.
    - Người dùng vẫn đăng nhập được bình thường bằng mật khẩu cũ chuẩn.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": wrong_old_pwd, "new_password": "ValidNewPassword2026!"},
    )
    assert res.status_code == 400
    err = res.json()
    assert err["code"] == "WRONG_OLD_PASSWORD"
    assert err["message"] == "Mật khẩu cũ không chính xác."

    # Xác nhận DB không bị thay đổi
    user = db_session.get(User, 1)
    assert verify_password("AdminPass123!", user.password_hash) is True


# =====================================================================
# NHÓM 4: KIỂM TRA ĐỘ MẠNH MẬT KHẨU MỚI THEO AC-29.1 (HTTP 400 VALIDATION_ERROR)
# Quy định: Tối thiểu 8 ký tự, có ít nhất 1 chữ hoa, 1 chữ thường, 1 chữ số.
# =====================================================================

@pytest.mark.parametrize("invalid_new_pwd, description", [
    ("Aa1!bcd", "Độ dài 7 ký tự (thiếu 1 ký tự để đạt 8)"),
    ("Pass1", "Độ dài 5 ký tự"),
    ("A1b!", "Độ dài 4 ký tự"),
    ("P1", "Độ dài 2 ký tự"),
    ("P", "Độ dài 1 ký tự"),
    ("abcdefg1", "Độ dài 8 ký tự nhưng thiếu chữ hoa"),
    ("bluemoon2026!", "Độ dài 14 ký tự nhưng thiếu chữ hoa"),
    ("superpassword123#", "Độ dài 18 ký tự nhưng thiếu chữ hoa"),
    ("ABCDEFG1", "Độ dài 8 ký tự nhưng thiếu chữ thường"),
    ("BLUEMOON2026!", "Độ dài 14 ký tự nhưng thiếu chữ thường"),
    ("ADMINPASS123#", "Độ dài 13 ký tự nhưng thiếu chữ thường"),
    ("Abcdefgh", "Độ dài 8 ký tự nhưng thiếu chữ số"),
    ("BlueMoonManagement!", "Độ dài 19 ký tự nhưng thiếu chữ số"),
    ("1234567890", "Chỉ chứa toàn chữ số"),
    ("abcdefghijk", "Chỉ chứa toàn chữ thường"),
    ("ABCDEFGHIJK", "Chỉ chứa toàn chữ hoa"),
])
def test_change_password_invalid_new_password_strength(client, invalid_new_pwd, description):
    """
    AC-29.1: Mật khẩu mới không đạt chuẩn độ mạnh:
    - HTTP 400 Bad Request.
    - code == 'VALIDATION_ERROR'.
    - Không làm thay đổi mật khẩu cũ trong hệ thống.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": invalid_new_pwd},
    )
    assert res.status_code == 400
    err = res.json()
    assert err["code"] == "VALIDATION_ERROR"
    assert "message" in err


@pytest.mark.parametrize("valid_new_pwd", [
    "Abcd1234",                                                 # Đúng 8 ký tự tối thiểu chuẩn mực
    "A1b!cdef",                                                 # 8 ký tự kèm ký tự đặc biệt
    "P@ssw0rd2026!",                                            # Mật khẩu mạnh tiêu chuẩn
    "SuperSecurePassphraseWithDigits123456AndSpecialChars!#$",   # Mật khẩu dài > 50 ký tự
    "~`!@#$%^&*()_-+={[}]|:;'<,>.?/Aa1",                        # Mật khẩu chứa đa dạng ký tự đặc biệt
    "MậtKhẩuMạnh2026!",                                         # Chứa chữ tiếng Việt có dấu
    "123456aA",                                                 # Chữ số đặt ở đầu, chữ hoa chữ thường ở cuối
    "987654321Zz",                                              # Ký tự hoa thường đặt ở cuối
])
def test_change_password_valid_new_password_variety(client, db_session, valid_new_pwd):
    """
    AC-29.1: Các dạng mật khẩu mới hợp lệ khác nhau:
    - HTTP 204 No Content.
    - Xác thực thành công với mật khẩu mới.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": valid_new_pwd},
    )
    assert res.status_code == 204

    # Kiểm tra database cập nhật chính xác
    user = db_session.get(User, 1)
    assert verify_password(valid_new_pwd, user.password_hash) is True


# =====================================================================
# NHÓM 5: KIỂM TRA BẢO MẬT & XÁC THỰC TOKEN (HTTP 401 UNAUTHENTICATED)
# =====================================================================

def test_change_password_unauthenticated_missing_header(client):
    """Thiếu Authorization header hoàn toàn -> HTTP 401 UNAUTHENTICATED."""
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_change_password_unauthenticated_empty_header(client):
    """Authorization header rỗng -> HTTP 401 UNAUTHENTICATED."""
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers={"Authorization": ""},
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_change_password_unauthenticated_whitespace_header(client):
    """Authorization header chỉ có khoảng trắng -> HTTP 401 UNAUTHENTICATED."""
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers={"Authorization": "   "},
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_change_password_unauthenticated_bearer_without_token(client):
    """Authorization header chỉ có 'Bearer ' không có chuỗi token -> HTTP 401 UNAUTHENTICATED."""
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers={"Authorization": "Bearer "},
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_change_password_unauthenticated_custom_scheme_basic(client):
    """Authorization header dùng scheme Basic thay vì Bearer -> HTTP 401 UNAUTHENTICATED."""
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_change_password_unauthenticated_custom_scheme_token(client):
    """Authorization header dùng scheme Token thay vì Bearer -> HTTP 401 UNAUTHENTICATED."""
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers={"Authorization": "Token eyJhbGciOiJIUzI1NiJ9.test"},
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_change_password_unauthenticated_garbage_token(client):
    """Chuỗi token vô nghĩa rác -> HTTP 401 UNAUTHENTICATED."""
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers={"Authorization": "Bearer not_a_valid_jwt_token_payload"},
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_change_password_unauthenticated_expired_token(client):
    """Token đã hết hạn (thời điểm exp nằm trong quá khứ) -> HTTP 401 UNAUTHENTICATED."""
    headers = make_auth_header(1, "admin_test", "ADMIN", expires_delta=timedelta(minutes=-30))
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"
    assert "hết hạn" in res.json()["message"]


def test_change_password_unauthenticated_tampered_token(client):
    """Token bị chỉnh sửa phần chữ ký signature -> HTTP 401 UNAUTHENTICATED."""
    headers = make_auth_header(1, "admin_test", "ADMIN")
    tampered_auth = headers["Authorization"] + "tampered"
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers={"Authorization": tampered_auth},
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_change_password_unauthenticated_nonexistent_user(client):
    """Token chứa ID người dùng không tồn tại trong hệ thống (sub=99999) -> HTTP 401 UNAUTHENTICATED."""
    headers = make_auth_header(99999, "ghost_user", "RESIDENT")
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"
    assert "không tồn tại" in res.json()["message"]


def test_change_password_unauthenticated_disabled_user(client, db_session):
    """Tài khoản bị vô hiệu hóa (is_active=False) -> HTTP 401 UNAUTHENTICATED."""
    user = db_session.get(User, 1)
    user.is_active = False
    db_session.commit()

    headers = make_auth_header(1, "admin_test", "ADMIN")
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "NewAdminPass2026!"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"
    assert "vô hiệu hóa" in res.json()["message"]


# =====================================================================
# NHÓM 6: KIỂM TRA DỮ LIỆU ĐẦU VÀO KHÔNG HỢP LỆ (HTTP 400 VALIDATION_ERROR)
# =====================================================================

@pytest.mark.parametrize("invalid_payload", [
    {},                                                                     # Body rỗng hoàn toàn
    {"old_password": "AdminPass123!"},                                      # Thiếu trường new_password
    {"new_password": "NewAdminPass2026!"},                                  # Thiếu trường old_password
    {"old_password": "", "new_password": "NewAdminPass2026!"},              # old_password rỗng (min_length=1)
    {"old_password": "AdminPass123!", "new_password": ""},                  # new_password rỗng (min_length=8)
    {"old_password": None, "new_password": "NewAdminPass2026!"},            # old_password là null
    {"old_password": "AdminPass123!", "new_password": None},                # new_password là null
    {"old_password": 12345, "new_password": "NewAdminPass2026!"},           # old_password sai kiểu dữ liệu int
    {"old_password": "AdminPass123!", "new_password": 12345678},            # new_password sai kiểu dữ liệu int
    {"old_password": True, "new_password": "NewAdminPass2026!"},            # old_password sai kiểu dữ liệu bool
    {"old_password": "AdminPass123!", "new_password": False},               # new_password sai kiểu dữ liệu bool
    {"old_password": ["AdminPass123!"], "new_password": "NewAdminPass2026!"}, # old_password dạng array
    {"old_password": "AdminPass123!", "new_password": ["NewAdminPass2026!"]}, # new_password dạng array
    {"old_password": {"p": "AdminPass123!"}, "new_password": "NewPass123!"}, # old_password dạng dict
])
def test_change_password_invalid_request_payloads(client, invalid_payload):
    """
    Payload không đúng định dạng schema (thiếu trường, sai kiểu dữ liệu, null):
    - HTTP 400 Bad Request.
    - code == 'VALIDATION_ERROR'.
    - details chứa danh sách lỗi chi tiết.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json=invalid_payload,
    )
    assert res.status_code == 400
    err = res.json()
    assert err["code"] == "VALIDATION_ERROR"
    assert len(err["details"]) > 0


# =====================================================================
# NHÓM 7: KỊCH BẢN NÂNG CAO, LIÊN TIẾP & TÍNH TOÀN VẸN DỮ LIỆU
# =====================================================================

def test_consecutive_password_changes_lifecycle(client, db_session):
    """
    Đổi mật khẩu liên tiếp 3 lần A -> B -> C:
    - Đổi lần 1: AdminPass123! -> PassPhase2026A! (204)
    - Đổi lần 2: PassPhase2026A! -> PassPhase2026B! (204)
    - Đổi lần 3: PassPhase2026B! -> PassPhase2026C! (204)
    - Xác nhận chỉ mật khẩu mới nhất (C) đăng nhập được, A và B đều bị từ chối.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")

    # Lần 1
    res1 = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "PassPhase2026A!"},
    )
    assert res1.status_code == 204

    # Lần 2
    res2 = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "PassPhase2026A!", "new_password": "PassPhase2026B!"},
    )
    assert res2.status_code == 204

    # Lần 3
    res3 = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "PassPhase2026B!", "new_password": "PassPhase2026C!"},
    )
    assert res3.status_code == 204

    # Xác thực đăng nhập
    assert client.post(ENDPOINT_LOGIN, json={"username": "admin_test", "password": "PassPhase2026C!"}).status_code == 200
    assert client.post(ENDPOINT_LOGIN, json={"username": "admin_test", "password": "PassPhase2026B!"}).status_code == 401
    assert client.post(ENDPOINT_LOGIN, json={"username": "admin_test", "password": "PassPhase2026A!"}).status_code == 401
    assert client.post(ENDPOINT_LOGIN, json={"username": "admin_test", "password": "AdminPass123!"}).status_code == 401


def test_reusing_initial_old_password_fails_after_change(client):
    """
    Sau khi đã đổi mật khẩu thành công sang mật khẩu mới,
    việc dùng lại mật khẩu ban đầu làm old_password sẽ bị từ chối với HTTP 400 WRONG_OLD_PASSWORD.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    res1 = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "NewSecretPass2026!"},
    )
    assert res1.status_code == 204

    # Thử đổi tiếp nhưng vẫn gửi old_password cũ ban đầu
    res2 = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "AnotherSecret2026!"},
    )
    assert res2.status_code == 400
    assert res2.json()["code"] == "WRONG_OLD_PASSWORD"


def test_change_password_to_identical_password(client, db_session):
    """
    Đổi mật khẩu mới giống hệt mật khẩu hiện tại (new_password == old_password):
    - Đạt chuẩn độ mạnh -> Hệ thống cho phép thành công (HTTP 204).
    - Tạo ra mã băm mới (khác mã băm cũ do muối salt bcrypt ngẫu nhiên).
    - Vẫn đăng nhập thành công bình thường.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    old_user = db_session.get(User, 1)
    old_hash = old_user.password_hash

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": "AdminPass123!"},
    )
    assert res.status_code == 204

    db_session.refresh(old_user)
    assert old_user.password_hash != old_hash  # Muối bcrypt mới sinh ra chuỗi hash khác
    assert verify_password("AdminPass123!", old_user.password_hash) is True

    # Đăng nhập vẫn hợp lệ
    login_res = client.post(
        ENDPOINT_LOGIN,
        json={"username": "admin_test", "password": "AdminPass123!"},
    )
    assert login_res.status_code == 200


def test_change_password_preserves_other_user_attributes(client, db_session):
    """
    Kiểm tra tính toàn vẹn dữ liệu: Việc đổi mật khẩu không làm đột biến bất kỳ
    thuộc tính nào khác của người dùng (id, username, full_name, email, role_id, household_id, is_active).
    """
    headers = make_auth_header(3, "resident_101", "RESIDENT", household_id=101)
    before_user = db_session.get(User, 3)

    user_snapshot = {
        "id": before_user.id,
        "username": before_user.username,
        "full_name": before_user.full_name,
        "email": before_user.email,
        "role_id": before_user.role_id,
        "household_id": before_user.household_id,
        "is_active": before_user.is_active,
    }

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "ResPass123!", "new_password": "SafeUpdatePass2026!"},
    )
    assert res.status_code == 204

    db_session.refresh(before_user)
    for field, expected_val in user_snapshot.items():
        assert getattr(before_user, field) == expected_val


def test_change_password_with_extra_fields_in_payload(client, db_session):
    """
    Payload gửi kèm các trường bổ sung không xác định (extra fields):
    - Pydantic bỏ qua (extra='ignore').
    - Thực hiện đổi mật khẩu thành công HTTP 204 mà không phát sinh lỗi.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={
            "old_password": "AdminPass123!",
            "new_password": "ValidExtraFields2026!",
            "injected_admin_role": True,
            "fake_id": 9999,
            "extra_note": "Testing extra properties handling",
        },
    )
    assert res.status_code == 204

    user = db_session.get(User, 1)
    assert verify_password("ValidExtraFields2026!", user.password_hash) is True


def test_change_password_unicode_and_complex_symbols(client, db_session):
    """
    Đổi mật khẩu với chuỗi ký tự Unicode và emoji phức tạp:
    - Mật khẩu mới: 'BầuTrờiXanh#2026🔒' (thỏa mãn chữ hoa, chữ thường, số, độ dài >= 8).
    - Cập nhật thành công HTTP 204.
    - Đăng nhập lại với mật khẩu Unicode chính xác thành công.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    unicode_pwd = "BầuTrờiXanh#2026🔒"

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": unicode_pwd},
    )
    assert res.status_code == 204

    user = db_session.get(User, 1)
    assert verify_password(unicode_pwd, user.password_hash) is True

    login_res = client.post(
        ENDPOINT_LOGIN,
        json={"username": "admin_test", "password": unicode_pwd},
    )
    assert login_res.status_code == 200


def test_change_password_max_length_boundary_70_chars(client, db_session):
    """
    Kiểm thử biên độ dài lớn: Mật khẩu mới dài 70 ký tự (sát ngưỡng tối đa 72 bytes của chuẩn bcrypt):
    - Thỏa mãn chuẩn mật khẩu AC-29.1 (có hoa, thường, số).
    - Đổi thành công HTTP 204 và lưu mã băm bcrypt an toàn.
    """
    headers = make_auth_header(1, "admin_test", "ADMIN")
    long_pwd = "Pass" + ("a" * 65) + "1"  # 70 ký tự

    res = client.post(
        ENDPOINT_CHANGE_PASSWORD,
        headers=headers,
        json={"old_password": "AdminPass123!", "new_password": long_pwd},
    )
    assert res.status_code == 204

    user = db_session.get(User, 1)
    assert verify_password(long_pwd, user.password_hash) is True

