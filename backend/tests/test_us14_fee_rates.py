"""
Test Suite for User Story US-14: Quản lý lịch sử đơn giá khoản thu (Fee Rates).

Standards:
- docs/openapi.yaml (/fee-types/{id}/rates: GET, POST)
- docs/API_CONTRACT.md (Section 3.11.5, 3.11.6)
- docs/PRODUCT_BACKLOG.md (AC-14.1: lưu bảng lịch sử đơn giá theo ngày hiệu lực, tự động khép đơn giá cũ, ghi Audit Log khi đổi giá)
"""

from datetime import date, timedelta  # [SỬA] Bỏ import thừa datetime
import pytest
from sqlalchemy import select  # [SỬA] Bỏ import thừa func

from app.core.security import create_access_token, get_password_hash
from app.models.fee import FeeRate, FeeType
from app.models.user import AuditLog, User  # [SỬA] Bỏ import thừa Role


# ==============================================================================
# Helper Functions & Fixtures for Authentication & Roles
# ==============================================================================

def make_headers(
    role: str = "ADMIN",
    sub: str = "1",
    username: str = "admin_test",
    must_change_password: bool = False,
):
    token = create_access_token({
        "sub": str(sub),
        "username": username,
        "role": role,
        "must_change_password": must_change_password,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    return make_headers(role="ADMIN", sub="1", username="admin_test")


@pytest.fixture
def accountant_headers():
    return make_headers(role="ACCOUNTANT", sub="2", username="accountant_test")


@pytest.fixture
def treasurer_headers(db_session):
    user = db_session.scalar(select(User).where(User.username == "treasurer_test_us14"))
    if not user:
        user = User(
            id=514,
            username="treasurer_test_us14",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test US14",
            email="treasurer_14@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(user)
        db_session.commit()
    return make_headers(role="TREASURER", sub=str(user.id), username=user.username)


@pytest.fixture
def resident_headers():
    return make_headers(role="RESIDENT", sub="3", username="resident_101")


# [SỬA] Dọn bảng cả trước và sau mỗi test, bỏ try/except nuốt lỗi để phát hiện sớm nếu vướng khóa ngoại
@pytest.fixture(autouse=True)
def clean_fee_tables(db_session):
    """Đảm bảo bảng fee_rates, fee_types và audit_logs sạch sẽ trước và sau mỗi test."""
    def _cleanup():
        db_session.query(AuditLog).delete()
        db_session.query(FeeRate).delete()
        db_session.query(FeeType).delete()
        db_session.commit()

    _cleanup()
    yield
    _cleanup()


@pytest.fixture
def sample_fee_type(db_session):
    """Tạo 1 khoản thu mẫu để test đơn giá."""
    fee = FeeType(
        code="PQL_TEST_14",
        name="Phí quản lý test US-14",
        fee_group="MANAGEMENT",
        calc_method="PER_M2",
        unit_label="m2",
        cycle="MONTHLY",
        status="ACTIVE",
    )
    db_session.add(fee)
    db_session.commit()
    db_session.refresh(fee)
    return fee


# ==============================================================================
# 1. RBAC & Authentication Tests
# ==============================================================================

class TestFeeRatesRBAC:
    """Kiểm tra phân quyền: Chỉ ADMIN và ACCOUNTANT được xem và sửa đơn giá."""

    def test_list_rates_unauthenticated_fails_401(self, client, sample_fee_type):
        """Chưa đăng nhập -> 401 UNAUTHENTICATED."""
        res = client.get(f"/api/v1/fee-types/{sample_fee_type.id}/rates")
        assert res.status_code == 401

    def test_list_rates_invalid_token_fails_401(self, client, sample_fee_type):
        """Token không hợp lệ -> 401."""
        res = client.get(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert res.status_code == 401

    def test_list_rates_forbidden_treasurer_fails_403(self, client, sample_fee_type, treasurer_headers):
        """Thủ quỹ không có quyền xem đơn giá -> 403 FORBIDDEN."""
        res = client.get(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            headers=treasurer_headers
        )
        assert res.status_code == 403

    def test_list_rates_forbidden_resident_fails_403(self, client, sample_fee_type, resident_headers):
        """Cư dân không có quyền xem đơn giá -> 403 FORBIDDEN."""
        res = client.get(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            headers=resident_headers
        )
        assert res.status_code == 403

    def test_list_rates_allowed_admin_200(self, client, sample_fee_type, admin_headers):
        """ADMIN được phép xem đơn giá -> 200 OK."""
        res = client.get(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            headers=admin_headers
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_list_rates_allowed_accountant_200(self, client, sample_fee_type, accountant_headers):
        """ACCOUNTANT được phép xem đơn giá -> 200 OK."""
        res = client.get(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            headers=accountant_headers
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_create_rate_unauthenticated_fails_401(self, client, sample_fee_type):
        """Tạo đơn giá khi chưa đăng nhập -> 401."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 10000, "effective_from": "2026-01-01"}
        )
        assert res.status_code == 401

    def test_create_rate_forbidden_treasurer_fails_403(self, client, sample_fee_type, treasurer_headers):
        """Thủ quỹ không có quyền cập nhật đơn giá -> 403 FORBIDDEN."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 10000, "effective_from": "2026-01-01"},
            headers=treasurer_headers
        )
        assert res.status_code == 403

    def test_create_rate_forbidden_resident_fails_403(self, client, sample_fee_type, resident_headers):
        """Cư dân không có quyền cập nhật đơn giá -> 403 FORBIDDEN."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 10000, "effective_from": "2026-01-01"},
            headers=resident_headers
        )
        assert res.status_code == 403

    def test_create_rate_allowed_accountant_201(self, client, sample_fee_type, accountant_headers):
        """Kế toán được phép tạo đơn giá -> 201 CREATED."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 15000, "effective_from": "2026-01-01"},
            headers=accountant_headers
        )
        assert res.status_code == 201


# ==============================================================================
# 2. GET /fee-types/{id}/rates Tests
# ==============================================================================

class TestListFeeRates:
    """Kiểm thử API lấy danh sách lịch sử đơn giá."""

    def test_list_rates_not_found_fails_404(self, client, admin_headers):
        """Khoản thu không tồn tại -> 404 NOT_FOUND."""
        res = client.get("/api/v1/fee-types/999999/rates", headers=admin_headers)
        assert res.status_code == 404
        data = res.json()
        assert data["code"] == "NOT_FOUND"

    def test_list_rates_empty_when_no_rates(self, client, sample_fee_type, admin_headers):
        """Khoản thu chưa có đơn giá nào -> 200 OK với mảng rỗng []."""
        res = client.get(f"/api/v1/fee-types/{sample_fee_type.id}/rates", headers=admin_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_list_rates_sorted_by_effective_from_desc(self, client, sample_fee_type, admin_headers, db_session):
        """Danh sách đơn giá phải được sắp xếp theo effective_from giảm dần."""
        r1 = FeeRate(fee_type_id=sample_fee_type.id, unit_price=10000, effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31))
        r2 = FeeRate(fee_type_id=sample_fee_type.id, unit_price=12000, effective_from=date(2026, 1, 1), effective_to=date(2026, 6, 30))
        r3 = FeeRate(fee_type_id=sample_fee_type.id, unit_price=15000, effective_from=date(2026, 7, 1), effective_to=None)
        db_session.add_all([r1, r2, r3])
        db_session.commit()

        res = client.get(f"/api/v1/fee-types/{sample_fee_type.id}/rates", headers=admin_headers)
        assert res.status_code == 200
        rates = res.json()
        assert len(rates) == 3

        assert rates[0]["unit_price"] == 15000
        assert rates[0]["effective_from"] == "2026-07-01"
        assert rates[0]["effective_to"] is None

        assert rates[1]["unit_price"] == 12000
        assert rates[1]["effective_from"] == "2026-01-01"
        assert rates[1]["effective_to"] == "2026-06-30"

        assert rates[2]["unit_price"] == 10000
        assert rates[2]["effective_from"] == "2025-01-01"
        assert rates[2]["effective_to"] == "2025-12-31"

    def test_list_rates_isolates_different_fee_types(self, client, admin_headers, db_session):
        """Đơn giá của khoản thu này không bị lẫn vào khoản thu khác."""
        fee1 = FeeType(code="FEE_1", name="Phí 1", fee_group="OTHER", calc_method="PER_HOUSEHOLD", unit_label="hộ", status="ACTIVE")
        fee2 = FeeType(code="FEE_2", name="Phí 2", fee_group="OTHER", calc_method="PER_HOUSEHOLD", unit_label="hộ", status="ACTIVE")
        db_session.add_all([fee1, fee2])
        db_session.commit()

        r1 = FeeRate(fee_type_id=fee1.id, unit_price=50000, effective_from=date(2026, 1, 1), effective_to=None)
        r2 = FeeRate(fee_type_id=fee2.id, unit_price=90000, effective_from=date(2026, 1, 1), effective_to=None)
        db_session.add_all([r1, r2])
        db_session.commit()

        res1 = client.get(f"/api/v1/fee-types/{fee1.id}/rates", headers=admin_headers)
        assert res1.status_code == 200
        rates1 = res1.json()
        assert len(rates1) == 1
        assert rates1[0]["unit_price"] == 50000

        res2 = client.get(f"/api/v1/fee-types/{fee2.id}/rates", headers=admin_headers)
        assert res2.status_code == 200
        rates2 = res2.json()
        assert len(rates2) == 1
        assert rates2[0]["unit_price"] == 90000


# ==============================================================================
# 3. POST /fee-types/{id}/rates Tests (Creation & Auto-close)
# ==============================================================================

class TestCreateFeeRate:
    """Kiểm thử API tạo đơn giá mới và cơ chế tự động khép đơn giá cũ (AC-14.1)."""

    def test_create_rate_not_found_fails_404(self, client, admin_headers):
        """Khoản thu không tồn tại -> 404 NOT_FOUND."""
        res = client.post(
            "/api/v1/fee-types/999999/rates",
            json={"unit_price": 10000, "effective_from": "2026-01-01"},
            headers=admin_headers
        )
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_create_first_rate_success_201(self, client, sample_fee_type, admin_headers, db_session):
        """Tạo đơn giá đầu tiên cho khoản thu thành công (effective_to = None)."""
        payload = {
            "unit_price": 15000,
            "effective_from": "2026-01-01",
        }
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json=payload,
            headers=admin_headers
        )
        assert res.status_code == 201
        data = res.json()
        assert data["unit_price"] == 15000
        assert data["effective_from"] == "2026-01-01"
        assert data["effective_to"] is None
        assert data["fee_type_id"] == sample_fee_type.id
        assert "created_at" in data

        rate_in_db = db_session.get(FeeRate, data["id"])
        assert rate_in_db is not None
        assert int(rate_in_db.unit_price) == 15000
        assert rate_in_db.effective_to is None

        audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "CREATE_FEE_RATE"))
        assert audit is not None
        assert audit.entity_type == "FEE_RATE"
        assert audit.entity_id == str(data["id"])
        assert audit.new_value["unit_price"] == 15000
        assert audit.old_value is None

    def test_create_second_rate_auto_closes_previous_rate(self, client, sample_fee_type, admin_headers, db_session):
        """
        Nghiệp vụ AC-14.1 & OpenAPI:
        Tạo đơn giá mới (2026-07-01) -> Server tự động khép đơn giá đang áp dụng (2026-01-01)
        với effective_to = 2026-06-30 (ngày liền trước effective_from mới).
        """
        res1 = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 12000, "effective_from": "2026-01-01"},
            headers=admin_headers
        )
        assert res1.status_code == 201
        rate1_id = res1.json()["id"]

        res2 = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 16000, "effective_from": "2026-07-01"},
            headers=admin_headers
        )
        assert res2.status_code == 201
        rate2_data = res2.json()
        assert rate2_data["unit_price"] == 16000
        assert rate2_data["effective_from"] == "2026-07-01"
        assert rate2_data["effective_to"] is None

        rate1_in_db = db_session.get(FeeRate, rate1_id)
        assert rate1_in_db.effective_to == date(2026, 6, 30)

        audits = db_session.scalars(
            select(AuditLog).where(AuditLog.action == "CREATE_FEE_RATE").order_by(AuditLog.id.desc())
        ).all()
        assert len(audits) >= 2
        latest_audit = audits[0]
        assert latest_audit.old_value is not None
        assert latest_audit.old_value["rate_id"] == rate1_id
        assert latest_audit.old_value["unit_price"] == 12000
        assert latest_audit.new_value["unit_price"] == 16000

    def test_create_third_rate_successive_updates(self, client, sample_fee_type, admin_headers, db_session):
        """Khép nối tiếp nhiều lần đổi giá trong tương lai."""
        client.post(f"/api/v1/fee-types/{sample_fee_type.id}/rates", json={"unit_price": 10000, "effective_from": "2026-01-01"}, headers=admin_headers)
        client.post(f"/api/v1/fee-types/{sample_fee_type.id}/rates", json={"unit_price": 12000, "effective_from": "2026-06-01"}, headers=admin_headers)
        res3 = client.post(f"/api/v1/fee-types/{sample_fee_type.id}/rates", json={"unit_price": 15000, "effective_from": "2027-01-01"}, headers=admin_headers)
        assert res3.status_code == 201

        rates = db_session.scalars(select(FeeRate).where(FeeRate.fee_type_id == sample_fee_type.id).order_by(FeeRate.effective_from.asc())).all()
        assert len(rates) == 3
        assert rates[0].effective_from == date(2026, 1, 1) and rates[0].effective_to == date(2026, 5, 31)
        assert rates[1].effective_from == date(2026, 6, 1) and rates[1].effective_to == date(2026, 12, 31)
        assert rates[2].effective_from == date(2027, 1, 1) and rates[2].effective_to is None

    def test_create_zero_unit_price_is_allowed(self, client, sample_fee_type, admin_headers):
        """Đơn giá bằng 0 VNĐ (vd miễn phí gửi xe đạp) là hợp lệ."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 0, "effective_from": "2026-01-01"},
            headers=admin_headers
        )
        assert res.status_code == 201
        assert res.json()["unit_price"] == 0


# ==============================================================================
# 4. Conflict & Overlap Tests (409 RATE_OVERLAP)
# ==============================================================================

class TestFeeRateOverlapConflicts:
    """Kiểm tra chặn xung đột ngày hiệu lực theo mã lỗi RATE_OVERLAP (HTTP 409)."""

    def test_conflict_when_effective_from_same_as_active_rate(self, client, sample_fee_type, admin_headers):
        """Ngày hiệu lực mới trùng ngày bắt đầu của đơn giá đang áp dụng -> 409 RATE_OVERLAP."""
        client.post(f"/api/v1/fee-types/{sample_fee_type.id}/rates", json={"unit_price": 10000, "effective_from": "2026-06-01"}, headers=admin_headers)

        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 12000, "effective_from": "2026-06-01"},
            headers=admin_headers
        )
        assert res.status_code == 409
        data = res.json()
        assert data["code"] == "RATE_OVERLAP"
        assert "phải sau ngày bắt đầu" in data["message"].lower()

    def test_conflict_when_effective_from_earlier_than_active_rate(self, client, sample_fee_type, admin_headers):
        """Ngày hiệu lực mới trước ngày bắt đầu của đơn giá đang áp dụng -> 409 RATE_OVERLAP."""
        client.post(f"/api/v1/fee-types/{sample_fee_type.id}/rates", json={"unit_price": 10000, "effective_from": "2026-06-01"}, headers=admin_headers)

        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 12000, "effective_from": "2026-01-01"},
            headers=admin_headers
        )
        assert res.status_code == 409
        assert res.json()["code"] == "RATE_OVERLAP"

    # [SỬA] Bỏ r2 (active_rate) để test thực sự đi vào nhánh kiểm tra chồng lấn với đơn giá cũ đã đóng (r1)
    def test_conflict_when_effective_from_falls_within_closed_rate(self, client, sample_fee_type, admin_headers, db_session):
        """Ngày hiệu lực mới nằm trong khoảng thời gian của một đơn giá cũ đã đóng -> 409 RATE_OVERLAP."""
        r1 = FeeRate(
            fee_type_id=sample_fee_type.id,
            unit_price=10000,
            effective_from=date(2025, 1, 1),
            effective_to=date(2025, 12, 31),
        )
        db_session.add(r1)
        db_session.commit()

        # Thử thêm đơn giá bắt đầu vào 2025-06-01 (nằm trong khoảng r1)
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 11000, "effective_from": "2025-06-01"},
            headers=admin_headers
        )
        assert res.status_code == 409
        data = res.json()
        assert data["code"] == "RATE_OVERLAP"
        assert "chồng lấn" in data["message"].lower()


# ==============================================================================
# 5. Validation Error Tests (400 / 422)
# ==============================================================================

class TestFeeRateValidationErrors:
    """Kiểm tra tính hợp lệ của dữ liệu đầu vào (đơn giá âm, thập phân, boolean, ngày sai)."""

    def test_negative_unit_price_rejected(self, client, sample_fee_type, admin_headers):
        """Đơn giá âm -> Bị từ chối (HTTP 400 hoặc 422)."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": -5000, "effective_from": "2026-01-01"},
            headers=admin_headers
        )
        assert res.status_code in (400, 422)

    def test_boolean_unit_price_rejected(self, client, sample_fee_type, admin_headers):
        """Đơn giá là boolean (True) -> Bị từ chối theo validator convert_unit_price."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": True, "effective_from": "2026-01-01"},
            headers=admin_headers
        )
        assert res.status_code in (400, 422)

    def test_decimal_unit_price_rejected(self, client, sample_fee_type, admin_headers):
        """Đơn giá là số thập phân có phần lẻ (7500.9) -> Bị từ chối."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 7500.9, "effective_from": "2026-01-01"},
            headers=admin_headers
        )
        assert res.status_code in (400, 422)

    def test_invalid_date_format_rejected(self, client, sample_fee_type, admin_headers):
        """Ngày hiệu lực sai định dạng -> Bị từ chối."""
        res = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 10000, "effective_from": "01-01-2026"},
            headers=admin_headers
        )
        assert res.status_code in (400, 422)

    def test_missing_required_fields_rejected(self, client, sample_fee_type, admin_headers):
        """Thiếu trường bắt buộc -> Bị từ chối."""
        res1 = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"effective_from": "2026-01-01"},
            headers=admin_headers
        )
        assert res1.status_code in (400, 422)

        res2 = client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 10000},
            headers=admin_headers
        )
        assert res2.status_code in (400, 422)


# ==============================================================================
# 6. Integration with FeeType.current_unit_price
# ==============================================================================

class TestFeeTypeCurrentUnitPriceIntegration:
    """Kiểm tra tích hợp: GET /fee-types/{id} phản ánh chính xác current_unit_price sau khi cập nhật đơn giá."""

    def test_current_unit_price_reflects_active_rate(self, client, sample_fee_type, admin_headers):
        """Trước khi tạo rate: current_unit_price là None. Sau khi tạo rate hiệu lực: phản ánh đúng giá."""
        get_res_1 = client.get(f"/api/v1/fee-types/{sample_fee_type.id}", headers=admin_headers)
        assert get_res_1.status_code == 200
        assert get_res_1.json()["current_unit_price"] is None

        client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 18500, "effective_from": "2025-01-01"},
            headers=admin_headers
        )

        get_res_2 = client.get(f"/api/v1/fee-types/{sample_fee_type.id}", headers=admin_headers)
        assert get_res_2.status_code == 200
        assert get_res_2.json()["current_unit_price"] == 18500

    def test_future_rate_does_not_override_current_rate_yet(self, client, sample_fee_type, admin_headers):
        """Đơn giá có hiệu lực trong tương lai (năm sau) chưa thay thế đơn giá hiện tại trong get_current_unit_price."""
        today = date.today()
        past_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        future_date = (today + timedelta(days=60)).strftime("%Y-%m-%d")

        client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 20000, "effective_from": past_date},
            headers=admin_headers
        )

        client.post(
            f"/api/v1/fee-types/{sample_fee_type.id}/rates",
            json={"unit_price": 25000, "effective_from": future_date},
            headers=admin_headers
        )

        res = client.get(f"/api/v1/fee-types/{sample_fee_type.id}", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["current_unit_price"] == 20000