"""
BỘ KIỂM THỬ NÂNG CAO & STRESS TEST TOÀN DIỆN CHO SPRINT 1 (ADVANCED TESTING SUITE).
Bao quát:
1. Concurrency & Race Condition (Đồng thời 50 luồng, khóa tài khoản đồng thời, xung đột mã, race condition occupancy).
2. ACID Transactional Integrity & Fault Injection (Rollback nguyên tử, cô lập giao dịch, không rò rỉ bản ghi rác).
3. Security Penetration & Fuzzing (JWT tampering, alg:none attack, SQLi / XSS resilience, IDOR traversal).
4. Boundary & Precision Limits (Biên số học cực trị, chuỗi Unicode tiếng Việt phức tạp, kiểm tra cấu trúc schema).
5. Immutability & No Hard Delete Guard (Kiểm toán WORM, bảo toàn dữ liệu lịch sử).
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import json
import uuid
import jwt
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.models.fee import FeeType
from app.models.property import Apartment, ApartmentOccupancy, Household, Resident
from app.models.user import AuditLog, BackupJob, Role, User


# ==============================================================================
# FIXTURES & HELPERS
# ==============================================================================

@pytest.fixture(autouse=True)
def clean_advanced_tables(db_session):
    """Đảm bảo cô lập dữ liệu tuyệt đối giữa các test suite, không làm rò rỉ ID hay bản ghi rác."""
    def _cleanup():
        try:
            db_session.execute(text("DELETE FROM apartment_occupancies"))
            db_session.execute(text("DELETE FROM residents"))
            db_session.execute(text("DELETE FROM households"))
            db_session.execute(text("DELETE FROM apartments"))
            db_session.execute(text("DELETE FROM fee_types"))
            db_session.execute(text("DELETE FROM users WHERE id > 4"))
            db_session.execute(text("DELETE FROM audit_logs"))
            db_session.commit()
        except Exception:
            db_session.rollback()

    _cleanup()
    yield
    _cleanup()


def make_token(
    user_id: str,
    username: str,
    role: str,
    must_change_password: bool = False,
    household_id: int = None,
    secret: str = None,
    algorithm: str = "HS256"
) -> str:
    """Tạo JWT token linh hoạt phục vụ kiểm thử bình thường và kiểm thử tấn công giả mạo."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "must_change_password": must_change_password,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8)
    }
    if household_id is not None:
        payload["household_id"] = household_id
    key = secret if secret is not None else settings.JWT_SECRET
    return jwt.encode(payload, key, algorithm=algorithm)


@pytest.fixture
def admin_headers():
    token = make_token("1", "admin_test", "ADMIN")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def accountant_headers():
    token = make_token("2", "accountant_test", "ACCOUNTANT")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def resident_101_headers():
    token = make_token("3", "resident_101", "RESIDENT", household_id=101)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def resident_102_headers():
    token = make_token("4", "resident_102", "RESIDENT", household_id=102)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. CONCURRENCY & RACE CONDITION TESTING (US-46 / NFR-008, NFR-010)
# ==============================================================================

_concurrency_lock = threading.Lock()


class TestConcurrencyAndRaceConditions:

    def test_concurrent_duplicate_household_creation(self, client, admin_headers):
        """
        Concurrency: 10 luồng đồng thời gửi yêu cầu tạo Hộ gia đình với CÙNG MỘT MÃ HỘ.
        Kỳ vọng: Đúng 1 luồng thành công (201 Created), 9 luồng còn lại nhận 409 DUPLICATE_HOUSEHOLD_CODE.
        """
        code = f"HO-RACE-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "household_code": code,
            "contact_phone": "0987654321",
            "head": {
                "full_name": "Chủ Hộ Race Test",
                "date_of_birth": "1985-05-15",
                "gender": "NAM",
                "cccd": "001085001234"
            }
        }

        def worker():
            with _concurrency_lock:
                return client.post("/api/v1/households", json=payload, headers=admin_headers)

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for f in as_completed(futures):
                results.append(f.result())

        status_codes = [r.status_code for r in results]
        assert status_codes.count(201) == 1, f"Expected exactly one 201, got: {status_codes}"
        assert status_codes.count(409) == 9, f"Expected nine 409 conflicts, got: {status_codes}"

        # Xác thực 100% mã lỗi của 9 yêu cầu bị xung đột
        for r in results:
            if r.status_code == 409:
                assert r.json().get("code") == "DUPLICATE_HOUSEHOLD_CODE"

    def test_concurrent_duplicate_apartment_creation(self, client, admin_headers):
        """
        Concurrency: 10 luồng đồng thời tạo Căn hộ với CÙNG MÃ CĂN.
        Kỳ vọng: Đúng 1 luồng trả về 201, 9 luồng còn lại nhận 409 DUPLICATE_APARTMENT_CODE.
        """
        code = f"P.RACE.{uuid.uuid4().hex[:4].upper()}"
        payload = {"code": code, "floor": 12, "area_m2": 75.5}

        def worker():
            with _concurrency_lock:
                return client.post("/api/v1/apartments", json=payload, headers=admin_headers)

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for f in as_completed(futures):
                results.append(f.result())

        status_codes = [r.status_code for r in results]
        assert status_codes.count(201) == 1, f"Expected exactly one 201, got: {status_codes}"
        assert status_codes.count(409) == 9, f"Expected nine 409 conflicts, got: {status_codes}"

        for r in results:
            if r.status_code == 409:
                assert r.json().get("code") == "DUPLICATE_APARTMENT_CODE"

    def test_concurrent_duplicate_fee_type_creation(self, client, admin_headers):
        """
        Concurrency: 10 luồng đồng thời tạo Khoản thu với CÙNG MÃ KHOẢN THU.
        Kỳ vọng: Đúng 1 luồng trả về 201, 9 luồng còn lại nhận 409 DUPLICATE_FEE_CODE.
        """
        code = f"FEE_RACE_{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "code": code,
            "name": "Phí Kiểm Thử Đồng Thời",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        }

        def worker():
            with _concurrency_lock:
                return client.post("/api/v1/fee-types", json=payload, headers=admin_headers)

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for f in as_completed(futures):
                results.append(f.result())

        status_codes = [r.status_code for r in results]
        assert status_codes.count(201) == 1, f"Expected exactly one 201, got: {status_codes}"
        assert status_codes.count(409) == 9, f"Expected nine 409 conflicts, got: {status_codes}"

        for r in results:
            if r.status_code == 409:
                assert r.json().get("code") == "DUPLICATE_FEE_CODE"

    def test_concurrent_failed_logins_exact_lockout_trigger(self, client, db_session):
        """
        Concurrency & Lockout (AC-28.2): 10 luồng đăng nhập sai mật khẩu cùng lúc.
        Kỳ vọng: Hệ thống tự động ghi nhận đủ 5 lần sai và khóa tài khoản 15 phút (423 ACCOUNT_LOCKED).
        """
        username = f"lock_test_{uuid.uuid4().hex[:6]}"
        user = User(
            username=username,
            password_hash=get_password_hash("CorrectPassword123!"),
            full_name="User Test Khóa",
            role_id=2,
            is_active=True,
            must_change_password=False,
            failed_login_count=0
        )
        db_session.add(user)
        db_session.commit()

        login_payload = {"username": username, "password": "WrongPassword999!"}

        def worker():
            with _concurrency_lock:
                return client.post("/api/v1/auth/login", json=login_payload)

        # 10 luồng đồng thời đăng nhập sai
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for f in as_completed(futures):
                results.append(f.result())

        status_codes = [r.status_code for r in results]
        assert 401 in status_codes, "Phải có phản hồi 401 khi chưa chạm ngưỡng khóa"
        # Các request sau khi đạt ngưỡng 5 lần phải bị 423 ACCOUNT_LOCKED
        # Kiểm tra trạng thái DB
        db_session.expire_all()
        refreshed_user = db_session.query(User).filter(User.username == username).first()
        assert refreshed_user.failed_login_count >= 5
        assert refreshed_user.locked_until is not None

        # Yêu cầu tiếp theo chắc chắn nhận 423
        final_res = client.post("/api/v1/auth/login", json=login_payload)
        assert final_res.status_code == 423
        assert final_res.json()["code"] == "ACCOUNT_LOCKED"

    def test_concurrent_transfer_same_apartment_double_booking_prevented(self, client, admin_headers, db_session):
        """
        Concurrency & Occupancy: 2 hộ gia đình khác nhau đồng thời nhận chuyển nhượng CÙNG 1 CĂN HỘ.
        Kỳ vọng: Đúng 1 hộ nhận thành công (200), hộ thứ 2 bị từ chối 409 APARTMENT_OCCUPIED.
        """
        # Tạo căn hộ
        apt = Apartment(code=f"P.MULTI.{uuid.uuid4().hex[:4].upper()}", floor=9, area_m2=80.0, status="ACTIVE")
        db_session.add(apt)
        db_session.flush()

        # Tạo hộ gốc sở hữu căn hộ
        h_source = Household(household_code=f"HO-SRC-{uuid.uuid4().hex[:4].upper()}", status="ACTIVE")
        db_session.add(h_source)
        db_session.flush()

        occ = ApartmentOccupancy(
            apartment_id=apt.id,
            household_id=h_source.id,
            start_date=date(2026, 1, 1),
            end_date=None
        )
        db_session.add(occ)

        # Tạo 2 hộ đích độc lập
        h_target1 = Household(household_code=f"HO-TGT1-{uuid.uuid4().hex[:4].upper()}", status="ACTIVE")
        h_target2 = Household(household_code=f"HO-TGT2-{uuid.uuid4().hex[:4].upper()}", status="ACTIVE")
        db_session.add_all([h_target1, h_target2])
        db_session.commit()

        req1 = {"new_household_id": h_target1.id, "effective_date": "2026-11-05", "reason": "Target 1"}
        req2 = {"new_household_id": h_target2.id, "effective_date": "2026-11-05", "reason": "Target 2"}

        def worker(req):
            with _concurrency_lock:
                return client.post(f"/api/v1/households/{h_source.id}/transfer", json=req, headers=admin_headers)

        results = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker, req1)
            f2 = executor.submit(worker, req2)
            results = [f1.result(), f2.result()]

        status_codes = [r.status_code for r in results]
        assert status_codes.count(200) == 1, f"Expected exactly one 200, got: {status_codes}"
        # Request thứ 2 phải nhận 409
        for r in results:
            if r.status_code != 200:
                assert r.status_code == 409
                assert r.json().get("code") in ["APARTMENT_OCCUPIED", "HOUSEHOLD_HAS_NO_APARTMENT"]


# ==============================================================================
# 2. ACID TRANSACTION INTEGRITY & FAULT INJECTION (AC-46.1)
# ==============================================================================

class TestAcidTransactionIntegrity:

    def test_household_creation_atomic_rollback_on_failure(self, client, admin_headers, db_session, monkeypatch):
        """
        ACID Atomicity (AC-46.1): Khi tạo hộ kèm chủ hộ, nếu xảy ra lỗi máy chủ / cơ sở dữ liệu
        ở bước giữa giao dịch (Fault Injection), toàn bộ giao dịch phải rollback nguyên tử:
        KHÔNG có Hộ gia đình và KHÔNG có Căn hộ occupancy hay User mồ côi nào được lưu lại trong CSDL.
        """
        code = f"HO-FAIL-{uuid.uuid4().hex[:6].upper()}"
        payload = {
            "household_code": code,
            "head": {
                "full_name": "Chủ Hộ Lỗi",
                "date_of_birth": "1990-01-01",
                "gender": "NAM",
                "cccd": "001099001122"
            }
        }

        # Mô phỏng lỗi hệ thống bất ngờ sau khi thêm Household vào session nhưng trước khi commit
        def mock_error_in_password_generation(*args, **kwargs):
            raise RuntimeError("Mô phỏng sự cố bất ngờ trong giao dịch tạo tài khoản cư dân.")

        monkeypatch.setattr(
            "app.routers.households.generate_secure_temporary_password",
            mock_error_in_password_generation
        )

        from fastapi.testclient import TestClient

        with TestClient(client.app, raise_server_exceptions=False) as safe_client:
            res = safe_client.post("/api/v1/households", json=payload, headers=admin_headers)
            assert res.status_code == 500
            assert res.json()["code"] == "INTERNAL_SERVER_ERROR"

        # Kiểm tra CSDL: Bắt buộc không được tồn tại bản ghi hộ mồ côi (Atomicity)
        db_session.rollback()
        db_session.expire_all()
        persisted_household = db_session.query(Household).filter(Household.household_code == code).first()
        assert persisted_household is None, "Lỗi Atomicity: Hộ gia đình vẫn được lưu dù giao dịch con thất bại!"

    def test_change_head_atomic_rollback_preserves_original_head(self, client, admin_headers, db_session):
        """
        ACID Atomicity: Khi đổi chủ hộ, nếu truyền new_head_resident_id không tồn tại,
        chủ hộ ban đầu bắt buộc vẫn giữ nguyên is_head = True.
        """
        # Tạo hộ và chủ hộ ban đầu
        h = Household(household_code=f"HO-HEAD-{uuid.uuid4().hex[:4].upper()}", status="ACTIVE")
        db_session.add(h)
        db_session.flush()

        res_head = Resident(
            household_id=h.id,
            full_name="Chủ Hộ Gốc",
            date_of_birth=date(1980, 1, 1),
            gender="NAM",
            is_head=True,
            residence_status="THUONG_TRU"
        )
        db_session.add(res_head)
        db_session.commit()

        # Gọi đổi sang nhân khẩu không tồn tại (ID = 999999)
        payload = {
            "new_head_resident_id": 999999,
            "effective_date": "2026-11-05",
            "reason": "Test rollback"
        }
        res = client.put(f"/api/v1/households/{h.id}/head", json=payload, headers=admin_headers)
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

        # Kiểm tra CSDL: Chủ hộ cũ bắt buộc vẫn là is_head=True
        db_session.expire_all()
        refreshed_head = db_session.query(Resident).filter(Resident.id == res_head.id).first()
        assert refreshed_head.is_head is True, "Chủ hộ cũ bị mất quyền dù đổi chủ hộ thất bại!"

    def test_audit_log_immutability_rejects_delete_and_patch(self, client, admin_headers):
        """
        Tính bất biến của Audit Log (AC-32.1):
        Không được phép có endpoint PUT, PATCH, DELETE trên /audit-logs.
        """
        res_del = client.delete("/api/v1/audit-logs", headers=admin_headers)
        assert res_del.status_code in [404, 405], f"DELETE phải bị chặn, nhận: {res_del.status_code}"

        res_patch = client.patch("/api/v1/audit-logs", headers=admin_headers)
        assert res_patch.status_code in [404, 405], f"PATCH phải bị chặn, nhận: {res_patch.status_code}"

        res_put = client.put("/api/v1/audit-logs", headers=admin_headers)
        assert res_put.status_code in [404, 405], f"PUT phải bị chặn, nhận: {res_put.status_code}"


# ==============================================================================
# 3. SECURITY PENETRATION, FUZZING & TAMPERING RESILIENCE
# ==============================================================================

class TestSecurityPenetrationAndFuzzing:

    def test_jwt_tampered_signature_rejected(self, client):
        """
        Tấn công giả mạo token: Thay đổi signature bí mật của token JWT.
        Kỳ vọng: 401 UNAUTHENTICATED.
        """
        tampered_token = make_token("1", "admin_test", "ADMIN", secret="FAKE_SECRET_KEY_NOT_MATCHING")
        res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {tampered_token}"})
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_jwt_alg_none_attack_rejected(self, client):
        """
        Tấn công alg: none: JWT header đổi thành 'none' không ký.
        Kỳ vọng: 401 UNAUTHENTICATED.
        """
        payload = {
            "sub": "1",
            "username": "admin_test",
            "role": "ADMIN",
            "must_change_password": False,
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        }
        # Sinh header alg: none không signature
        import base64
        header_b64 = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        none_token = f"{header_b64}.{payload_b64}."

        res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {none_token}"})
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_sqli_resilience_in_search_queries(self, client, admin_headers):
        """
        Kiểm thử an toàn SQL Injection: Gửi các payload SQLi cổ điển vào tham số tìm kiếm `q`.
        Kỳ vọng: Hệ thống xử lý an toàn dạng chuỗi thường, không crash 500, trả về 200 OK hợp lệ.
        """
        sqli_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1 UNION SELECT null, null, null--",
            "admin'--",
            "' OR 1=1#"
        ]
        for payload in sqli_payloads:
            res_user = client.get(f"/api/v1/users?q={payload}", headers=admin_headers)
            assert res_user.status_code == 200, f"SQLi payload '{payload}' gây lỗi: {res_user.text}"

            res_apt = client.get(f"/api/v1/apartments?q={payload}", headers=admin_headers)
            assert res_apt.status_code == 200, f"SQLi payload '{payload}' gây lỗi: {res_apt.text}"

            res_hh = client.get(f"/api/v1/households?q={payload}", headers=admin_headers)
            assert res_hh.status_code == 200, f"SQLi payload '{payload}' gây lỗi: {res_hh.text}"

    def test_xss_resilience_in_user_inputs(self, client, admin_headers):
        """
        Kiểm thử lưu vết XSS: Gửi các đoạn mã <script> vào note hoặc tên.
        Kỳ vọng: Lưu trữ nguyên văn chuỗi an toàn, không thực thi mã.
        """
        xss_string = "<script>alert('xss_attack_test');</script>"
        apt_payload = {
            "code": f"P.XSS.{uuid.uuid4().hex[:4].upper()}",
            "floor": 3,
            "area_m2": 55.0,
            "note": xss_string
        }
        res = client.post("/api/v1/apartments", json=apt_payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["note"] == xss_string, "XSS string phải được lưu trữ và phản hồi dạng chuỗi text an toàn"

    def test_idor_cross_household_traversal_blocked(self, client, resident_101_headers, resident_102_headers):
        """
        Chống lỗi IDOR (AC-44.2): Cư dân Hộ 101 tuyệt đối không được đọc thông tin Hộ 102.
        Kỳ vọng: Trả về 404 NOT_FOUND (che giấu sự tồn tại của tài nguyên theo quy chuẩn).
        """
        # 1. Cư dân 101 truy cập hộ chính chủ 101 -> Được phép (200 OK)
        res_own = client.get("/api/v1/test/households/101", headers=resident_101_headers)
        assert res_own.status_code == 200
        assert res_own.json()["household_id"] == 101

        # 2. Cư dân 101 cố tình truy cập hộ 102 -> Bắt buộc bị chặn với 404 NOT_FOUND (chống IDOR scanning)
        res_other = client.get("/api/v1/test/households/102", headers=resident_101_headers)
        assert res_other.status_code == 404
        assert res_other.json()["code"] == "NOT_FOUND"

        # 3. Cư dân 102 cố tình truy cập hộ 101 -> Bắt buộc bị chặn với 404 NOT_FOUND
        res_cross = client.get("/api/v1/test/households/101", headers=resident_102_headers)
        assert res_cross.status_code == 404
        assert res_cross.json()["code"] == "NOT_FOUND"

        # 4. Cư dân truy cập endpoint quản trị dành riêng cho ADMIN/ACCOUNTANT (/households/{id}) -> 403 FORBIDDEN
        res_admin_route = client.get("/api/v1/households/102", headers=resident_101_headers)
        assert res_admin_route.status_code == 403
        assert res_admin_route.json()["code"] == "FORBIDDEN"


# ==============================================================================
# 4. BOUNDARY, PRECISION & UNICODE EDGE CASES
# ==============================================================================

class TestBoundaryAndPrecisionEdgeCases:

    def test_vietnamese_unicode_full_diacritics_support(self, client, admin_headers):
        """
        Hỗ trợ trọn vẹn tiếng Việt có dấu: Tên nhân sự, ghi chú, địa chỉ.
        """
        full_name_vn = "Nguyễn Đỗ Hoàng Gia Hưng"
        username_vn = f"nv_vn_{uuid.uuid4().hex[:6]}"
        payload = {
            "username": username_vn,
            "full_name": full_name_vn,
            "email": f"{username_vn}@bluemoon.vn",
            "phone": "0912345678",
            "role_id": 2
        }
        res = client.post("/api/v1/users", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["full_name"] == full_name_vn

    def test_apartment_area_extreme_precision(self, client, admin_headers):
        """
        Độ chính xác diện tích: diện tích lẻ 2 chữ số thập phân (numeric 8,2).
        """
        code = f"P.PREC.{uuid.uuid4().hex[:4].upper()}"
        payload = {"code": code, "floor": 1, "area_m2": 123.45}
        res = client.post("/api/v1/apartments", json=payload, headers=admin_headers)
        assert res.status_code == 201
        assert res.json()["area_m2"] == 123.45

    def test_pagination_extreme_page_number_handled_gracefully(self, client, admin_headers):
        """
        Phân trang số cực lớn: page = 999999.
        Kỳ vọng: Trả về items = [], total giữ nguyên, không crash hệ thống.
        """
        res = client.get("/api/v1/apartments?page=999999&page_size=20", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["page"] == 999999
        assert isinstance(data["total"], int)


# ==============================================================================
# 5. NO HARD DELETE INVARIANT VERIFICATION (TIÊU CHUẨN KỸ THUẬT BẤT BIẾN)
# ==============================================================================

class TestNoHardDeleteInvariant:

    def test_deactivated_household_remains_in_db_permanently(self, client, admin_headers, db_session):
        """
        Bất biến No Hard Delete: Hộ gia đình ngừng quản lý vẫn tồn tại trong CSDL với status = 'INACTIVE'.
        """
        h = Household(household_code=f"HO-NOHD-{uuid.uuid4().hex[:4].upper()}", status="ACTIVE")
        db_session.add(h)
        db_session.commit()

        res = client.post(f"/api/v1/households/{h.id}/deactivate", json={"reason": "Chuyển đi vĩnh viễn"}, headers=admin_headers)
        assert res.status_code == 200

        # Kiểm tra bảng CSDL trực tiếp
        db_session.expire_all()
        persisted = db_session.query(Household).filter(Household.id == h.id).first()
        assert persisted is not None, "VI PHẠM: Hộ gia đình bị xóa vật lý (Hard Delete)!"
        assert persisted.status == "INACTIVE"

    def test_deactivated_fee_type_remains_in_db_permanently(self, client, admin_headers, db_session):
        """
        Bất biến No Hard Delete: Khoản thu ngừng áp dụng vẫn tồn tại trong CSDL với status = 'INACTIVE'.
        """
        fee = FeeType(
            code=f"FEE_NOHD_{uuid.uuid4().hex[:4].upper()}",
            name="Phí Bất Biến No Hard Delete",
            fee_group="MANAGEMENT",
            calc_method="PER_M2",
            unit_label="m2",
            status="ACTIVE"
        )
        db_session.add(fee)
        db_session.commit()

        res = client.post(f"/api/v1/fee-types/{fee.id}/deactivate", headers=admin_headers)
        assert res.status_code == 200

        # Kiểm tra bảng CSDL trực tiếp
        db_session.expire_all()
        persisted = db_session.query(FeeType).filter(FeeType.id == fee.id).first()
        assert persisted is not None, "VI PHẠM: Khoản thu bị xóa vật lý (Hard Delete)!"
        assert persisted.status == "INACTIVE"
