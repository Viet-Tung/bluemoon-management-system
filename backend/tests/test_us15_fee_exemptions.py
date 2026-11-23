"""
Test Suite for User Story US-15 & US-16: Quản lý chính sách miễn giảm phí (Fee Exemptions).

Standards:
- docs/openapi.yaml:
  * GET /fee-exemptions (listExemptions, US-15)
  * POST /fee-exemptions (createExemption, US-15)
  * POST /fee-exemptions/{id}/revoke (revokeExemption, US-16)
- docs/API_CONTRACT.md (Section 3.11.7, 3.11.8, 3.11.9)
- docs/PRODUCT_BACKLOG.md:
  * AC-15.1: Cho phép gắn mức miễn giảm theo hộ + khoản thu + thời hạn hiệu lực; số tiền miễn giảm không vượt quá phí gốc.
  * AC-16.1: Hiển thị rõ lý do miễn giảm, người phê duyệt và tổng số tiền miễn giảm trong kỳ.
"""

from datetime import date, timedelta
import pytest
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.fee import FeeExemption, FeeRate, FeeType
from app.models.property import Household
from app.models.user import AuditLog, User


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
    user = db_session.scalar(select(User).where(User.username == "treasurer_test_us15"))
    if not user:
        user = User(
            id=515,
            username="treasurer_test_us15",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test US15",
            email="treasurer_15@bluemoon.local",
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


@pytest.fixture(autouse=True)
def clean_exemption_tables(db_session):
    """Đảm bảo các bảng liên quan sạch sẽ trước và sau mỗi test."""
    def _cleanup():
        db_session.query(AuditLog).delete()
        db_session.query(FeeExemption).delete()
        db_session.query(FeeRate).delete()
        db_session.query(FeeType).delete()
        db_session.query(Household).delete()
        db_session.commit()

    _cleanup()
    yield
    _cleanup()


# ==============================================================================
# Fixtures for Data Models
# ==============================================================================

@pytest.fixture
def sample_household(db_session):
    """Tạo 1 hộ gia đình mẫu để gắn chính sách miễn giảm."""
    hh = Household(
        id=1,
        household_code="H_US15_01",
        status="ACTIVE",
        contact_phone="0912345678",
        note="Hộ diện chính sách có công",
    )
    db_session.add(hh)
    db_session.commit()
    return hh


@pytest.fixture
def sample_household_2(db_session):
    """Tạo hộ gia đình thứ 2 để kiểm thử phân biệt hộ."""
    hh = Household(
        id=2,
        household_code="H_US15_02",
        status="ACTIVE",
        contact_phone="0987654321",
        note="Hộ gia đình thứ hai",
    )
    db_session.add(hh)
    db_session.commit()
    return hh


@pytest.fixture
def sample_fee_type_fixed(db_session):
    """Tạo 1 khoản thu cố định theo hộ (PER_HOUSEHOLD) kèm đơn giá gốc 50,000 VNĐ."""
    fee = FeeType(
        id=1,
        code="P_AN_NINH_15",
        name="Phí an ninh US-15",
        fee_group="MANAGEMENT",
        calc_method="PER_HOUSEHOLD",
        unit_label="hộ",
        cycle="MONTHLY",
        status="ACTIVE",
    )
    db_session.add(fee)
    db_session.commit()

    rate = FeeRate(
        fee_type_id=fee.id,
        unit_price=50000,
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )
    db_session.add(rate)
    db_session.commit()
    return fee


@pytest.fixture
def sample_fee_type_metered(db_session):
    """Tạo khoản thu theo m2 (PER_M2) để kiểm thử miễn giảm không bị ràng buộc đơn giá hộ."""
    fee = FeeType(
        id=2,
        code="PQL_TEST_15",
        name="Phí quản lý test US-15",
        fee_group="MANAGEMENT",
        calc_method="PER_M2",
        unit_label="m2",
        cycle="MONTHLY",
        status="ACTIVE",
    )
    db_session.add(fee)
    db_session.commit()

    rate = FeeRate(
        fee_type_id=fee.id,
        unit_price=10000,
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )
    db_session.add(rate)
    db_session.commit()
    return fee


@pytest.fixture
def inactive_fee_type(db_session):
    """Tạo khoản thu đã ngừng áp dụng (INACTIVE)."""
    fee = FeeType(
        id=3,
        code="P_CU_INACTIVE",
        name="Phí cũ ngừng áp dụng",
        fee_group="OTHER",
        calc_method="PER_HOUSEHOLD",
        unit_label="hộ",
        cycle="MONTHLY",
        status="INACTIVE",
    )
    db_session.add(fee)
    db_session.commit()
    return fee


# ==============================================================================
# 1. Test Suite: Phân quyền RBAC (US-15, US-16)
# ==============================================================================

class TestFeeExemptionsRBAC:
    """Kiểm tra phân quyền nghiêm ngặt theo docs/openapi.yaml: Chỉ ADMIN & ACCOUNTANT."""

    def test_list_exemptions_unauthenticated_fails_401(self, client):
        res = client.get("/api/v1/fee-exemptions")
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_list_exemptions_forbidden_treasurer_fails_403(self, client, treasurer_headers):
        res = client.get("/api/v1/fee-exemptions", headers=treasurer_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_list_exemptions_forbidden_resident_fails_403(self, client, resident_headers):
        res = client.get("/api/v1/fee-exemptions", headers=resident_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_list_exemptions_allowed_admin_200(self, client, admin_headers):
        res = client.get("/api/v1/fee-exemptions", headers=admin_headers)
        assert res.status_code == 200

    def test_list_exemptions_allowed_accountant_200(self, client, accountant_headers):
        res = client.get("/api/v1/fee-exemptions", headers=accountant_headers)
        assert res.status_code == 200

    def test_create_exemption_unauthenticated_fails_401(self, client):
        res = client.post("/api/v1/fee-exemptions", json={})
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_create_exemption_forbidden_treasurer_fails_403(
        self, client, treasurer_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Miễn giảm thủ quỹ gọi",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=treasurer_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_create_exemption_forbidden_resident_fails_403(
        self, client, resident_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Cư dân tự giảm",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=resident_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_create_exemption_allowed_accountant_201(
        self, client, accountant_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 20,
            "reason": "Kế toán tạo chính sách",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=accountant_headers)
        assert res.status_code == 201

    def test_revoke_exemption_unauthenticated_fails_401(self, client):
        res = client.post("/api/v1/fee-exemptions/1/revoke")
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_revoke_exemption_forbidden_treasurer_fails_403(self, client, treasurer_headers):
        res = client.post("/api/v1/fee-exemptions/1/revoke", headers=treasurer_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_revoke_exemption_forbidden_resident_fails_403(self, client, resident_headers):
        res = client.post("/api/v1/fee-exemptions/1/revoke", headers=resident_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"


# ==============================================================================
# 2. Test Suite: Tra cứu và phân trang chính sách miễn giảm (US-15)
# ==============================================================================

class TestListFeeExemptions:
    """Kiểm tra danh sách, bộ lọc và phân trang FeeExemptionPage."""

    def test_list_empty_when_no_exemptions(self, client, admin_headers):
        res = client.get("/api/v1/fee-exemptions", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_pagination(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, db_session
    ):
        # Tạo 5 chính sách với ngày hiệu lực khác nhau không chồng chéo
        for i in range(1, 6):
            ex = FeeExemption(
                household_id=sample_household.id,
                fee_type_id=sample_fee_type_fixed.id,
                discount_type="PERCENT",
                discount_value=10,
                reason=f"Chính sách số {i}",
                valid_from=date(2020 + i, 1, 1),
                valid_to=date(2020 + i, 12, 31),
                status="ACTIVE",
            )
            db_session.add(ex)
        db_session.commit()

        # Kiểm tra trang 1 kích thước 2
        res = client.get("/api/v1/fee-exemptions?page=1&page_size=2", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

        # Kiểm tra trang 3
        res3 = client.get("/api/v1/fee-exemptions?page=3&page_size=2", headers=admin_headers)
        assert res3.status_code == 200
        data3 = res3.json()
        assert len(data3["items"]) == 1

    def test_filter_by_household_id(
        self, client, admin_headers, sample_household, sample_household_2, sample_fee_type_fixed, db_session
    ):
        ex1 = FeeExemption(
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="PERCENT",
            discount_value=30,
            reason="Hộ 1",
            valid_from=date(2026, 1, 1),
            status="ACTIVE",
        )
        ex2 = FeeExemption(
            household_id=sample_household_2.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="PERCENT",
            discount_value=50,
            reason="Hộ 2",
            valid_from=date(2026, 1, 1),
            status="ACTIVE",
        )
        db_session.add_all([ex1, ex2])
        db_session.commit()

        res = client.get(f"/api/v1/fee-exemptions?household_id={sample_household.id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["household_id"] == sample_household.id
        assert data["items"][0]["reason"] == "Hộ 1"

    def test_filter_by_fee_type_id(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, sample_fee_type_metered, db_session
    ):
        ex1 = FeeExemption(
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="AMOUNT",
            discount_value=20000,
            reason="Khoản thu 1",
            valid_from=date(2026, 1, 1),
            status="ACTIVE",
        )
        ex2 = FeeExemption(
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_metered.id,
            discount_type="AMOUNT",
            discount_value=15000,
            reason="Khoản thu 2",
            valid_from=date(2026, 1, 1),
            status="ACTIVE",
        )
        db_session.add_all([ex1, ex2])
        db_session.commit()

        res = client.get(f"/api/v1/fee-exemptions?fee_type_id={sample_fee_type_metered.id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["fee_type_id"] == sample_fee_type_metered.id
        assert data["items"][0]["reason"] == "Khoản thu 2"

    def test_filter_by_status(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, db_session
    ):
        ex_active = FeeExemption(
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="PERCENT",
            discount_value=20,
            reason="Chính sách active",
            valid_from=date(2026, 1, 1),
            status="ACTIVE",
        )
        ex_revoked = FeeExemption(
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="PERCENT",
            discount_value=50,
            reason="Chính sách revoked",
            valid_from=date(2025, 1, 1),
            status="REVOKED",
        )
        db_session.add_all([ex_active, ex_revoked])
        db_session.commit()

        # Lọc ACTIVE
        res_a = client.get("/api/v1/fee-exemptions?status=ACTIVE", headers=admin_headers)
        assert res_a.status_code == 200
        assert res_a.json()["total"] == 1
        assert res_a.json()["items"][0]["status"] == "ACTIVE"

        # Lọc REVOKED
        res_r = client.get("/api/v1/fee-exemptions?status=REVOKED", headers=admin_headers)
        assert res_r.status_code == 200
        assert res_r.json()["total"] == 1
        assert res_r.json()["items"][0]["status"] == "REVOKED"

    def test_filter_invalid_status_rejected_400(self, client, admin_headers):
        res = client.get("/api/v1/fee-exemptions?status=INVALID_STATUS", headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_sorted_by_id_desc(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, db_session
    ):
        ex1 = FeeExemption(
            id=10,
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="PERCENT",
            discount_value=10,
            reason="ID 10",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            status="ACTIVE",
        )
        ex2 = FeeExemption(
            id=20,
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="PERCENT",
            discount_value=20,
            reason="ID 20",
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            status="ACTIVE",
        )
        db_session.add_all([ex1, ex2])
        db_session.commit()

        res = client.get("/api/v1/fee-exemptions", headers=admin_headers)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        assert items[0]["id"] == 20
        assert items[1]["id"] == 10


# ==============================================================================
# 3. Test Suite: Tạo chính sách miễn giảm thành công (US-15)
# ==============================================================================

class TestCreateFeeExemptionSuccess:
    """Kiểm tra tạo chính sách PERCENT, AMOUNT, thời hạn và Audit Log."""

    def test_create_percent_exemption_success_201(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, db_session
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 75.5,
            "reason": "Gia đình thương binh liệt sĩ",
            "decision_no": "QD-2026/01/UBND",
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["household_id"] == sample_household.id
        assert data["fee_type_id"] == sample_fee_type_fixed.id
        assert data["discount_type"] == "PERCENT"
        assert data["discount_value"] == 75.5
        assert data["reason"] == "Gia đình thương binh liệt sĩ"
        assert data["decision_no"] == "QD-2026/01/UBND"
        assert data["valid_from"] == "2026-01-01"
        assert data["valid_to"] == "2026-12-31"
        assert data["status"] == "ACTIVE"
        assert data["approved_by"] == 1  # Lấy từ sub=1 của admin

    def test_create_amount_exemption_success_201(
        self, client, accountant_headers, sample_household, sample_fee_type_fixed
    ):
        # Đơn giá gốc là 50,000; giảm 30,000 (< đơn giá gốc)
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "AMOUNT",
            "discount_value": 30000,
            "reason": "Hỗ trợ hộ cận nghèo",
            "valid_from": "2026-03-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=accountant_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["discount_type"] == "AMOUNT"
        assert data["discount_value"] == 30000.0
        assert data["valid_to"] is None
        assert data["approved_by"] == 2  # Lấy từ sub=2 của accountant

    def test_create_records_audit_log(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, db_session
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 100,
            "reason": "Miễn toàn bộ phí quản lý",
            "decision_no": "QD-MIEN-100",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 201
        created_id = res.json()["id"]

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "FEE_EXEMPTION",
                AuditLog.action == "CREATE_EXEMPTION",
                AuditLog.entity_id == str(created_id),
            )
        )
        assert audit is not None
        assert audit.user_id == 1
        assert audit.new_value["discount_value"] == 100
        assert audit.new_value["discount_type"] == "PERCENT"
        assert audit.new_value["reason"] == "Miễn toàn bộ phí quản lý"
        assert "Tạo chính sách miễn giảm" in audit.reason


# ==============================================================================
# 4. Test Suite: Ràng buộc Validation & Nghiệp vụ (US-15, AC-15.1)
# ==============================================================================

class TestCreateFeeExemptionValidationErrors:
    """Kiểm tra các lỗi xác thực dữ liệu đầu vào và vi phạm quy tắc nghiệp vụ."""

    def test_create_household_not_found_fails_404(
        self, client, admin_headers, sample_fee_type_fixed
    ):
        payload = {
            "household_id": 999999,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 20,
            "reason": "Test not found",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_create_fee_type_not_found_fails_404(
        self, client, admin_headers, sample_household
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": 999999,
            "discount_type": "PERCENT",
            "discount_value": 20,
            "reason": "Test not found",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_create_inactive_fee_type_fails_400(
        self, client, admin_headers, sample_household, inactive_fee_type
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": inactive_fee_type.id,
            "discount_type": "PERCENT",
            "discount_value": 20,
            "reason": "Gắn cho phí đã ngừng áp dụng",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"
        assert "ngừng áp dụng" in res.json()["message"]

    def test_create_percent_greater_than_100_rejected_400(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 105.0,  # Vượt quá 100%
            "reason": "Giảm quá 100%",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_create_amount_with_decimals_rejected_400(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "AMOUNT",
            "discount_value": 15000.5,  # Tiền mặt VNĐ không được lẻ
            "reason": "Số tiền lẻ",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_create_negative_discount_value_rejected_400(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": -10,
            "reason": "Giảm âm",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_create_zero_discount_value_rejected_400(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "AMOUNT",
            "discount_value": 0,
            "reason": "Giảm 0 đồng",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_create_empty_reason_rejected_400(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "   ",  # Chỉ chứa khoảng trắng
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_create_valid_to_before_valid_from_rejected_400(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Hạn kết thúc trước ngày bắt đầu",
            "valid_from": "2026-06-01",
            "valid_to": "2026-05-31",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_create_amount_exceeding_unit_price_rejected_400(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        """AC-15.1: Số tiền miễn giảm không vượt quá phí gốc (Đơn giá 50,000; yêu cầu giảm 60,000 -> 400)."""
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "AMOUNT",
            "discount_value": 60000,
            "reason": "Giảm vượt quá đơn giá gốc",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"
        assert "không được vượt quá đơn giá gốc" in res.json()["message"]

    def test_create_amount_equal_to_unit_price_allowed_201(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        """AC-15.1: Số tiền miễn giảm bằng đúng đơn giá gốc (50,000 == 50,000 -> Giảm 100% bằng tiền -> 201)."""
        payload = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "AMOUNT",
            "discount_value": 50000,
            "reason": "Miễn 100% bằng số tiền",
            "valid_from": "2026-01-01",
        }
        res = client.post("/api/v1/fee-exemptions", json=payload, headers=admin_headers)
        assert res.status_code == 201
        assert res.json()["discount_value"] == 50000.0


# ==============================================================================
# 5. Test Suite: Kiểm soát xung đột chồng lấn thời gian (EXEMPTION_OVERLAP, 409)
# ==============================================================================

class TestCreateFeeExemptionOverlapConflicts:
    """Kiểm tra chặn chồng chéo chính sách ACTIVE cho cùng một hộ và khoản thu."""

    def test_conflict_when_new_exemption_overlaps_existing_active_exemption_409(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        # Tạo chính sách 1: Từ 2026-01-01 đến 2026-06-30
        payload1 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 30,
            "reason": "Giảm 6 tháng đầu năm",
            "valid_from": "2026-01-01",
            "valid_to": "2026-06-30",
        }
        res1 = client.post("/api/v1/fee-exemptions", json=payload1, headers=admin_headers)
        assert res1.status_code == 201

        # Tạo chính sách 2: Bắt đầu từ 2026-05-01 (chồng lấn với tháng 5-6 của chính sách 1)
        payload2 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Giảm từ tháng 5",
            "valid_from": "2026-05-01",
            "valid_to": "2026-12-31",
        }
        res2 = client.post("/api/v1/fee-exemptions", json=payload2, headers=admin_headers)
        assert res2.status_code == 409
        assert res2.json()["code"] == "EXEMPTION_OVERLAP"

    def test_conflict_when_permanent_exemption_overlaps_409(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        # Tạo chính sách vô thời hạn (valid_to is None)
        payload1 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Vô thời hạn",
            "valid_from": "2026-01-01",
        }
        res1 = client.post("/api/v1/fee-exemptions", json=payload1, headers=admin_headers)
        assert res1.status_code == 201

        # Tạo thêm chính sách khác trong tương lai cho cùng hộ + khoản thu
        payload2 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 20,
            "reason": "Năm 2027",
            "valid_from": "2027-01-01",
            "valid_to": "2027-12-31",
        }
        res2 = client.post("/api/v1/fee-exemptions", json=payload2, headers=admin_headers)
        assert res2.status_code == 409
        assert res2.json()["code"] == "EXEMPTION_OVERLAP"

    def test_allowed_when_time_ranges_do_not_overlap_201(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        # Kỳ 1: 01/01/2026 - 30/06/2026
        payload1 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 30,
            "reason": "6 tháng đầu năm",
            "valid_from": "2026-01-01",
            "valid_to": "2026-06-30",
        }
        res1 = client.post("/api/v1/fee-exemptions", json=payload1, headers=admin_headers)
        assert res1.status_code == 201

        # Kỳ 2: 01/07/2026 - 31/12/2026 (nối tiếp, không chồng chéo)
        payload2 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "6 tháng cuối năm",
            "valid_from": "2026-07-01",
            "valid_to": "2026-12-31",
        }
        res2 = client.post("/api/v1/fee-exemptions", json=payload2, headers=admin_headers)
        assert res2.status_code == 201

    def test_allowed_when_previous_exemption_is_revoked_201(
        self, client, admin_headers, sample_household, sample_fee_type_fixed
    ):
        # Tạo chính sách 1
        payload1 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 30,
            "reason": "Chính sách ban đầu",
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
        }
        res1 = client.post("/api/v1/fee-exemptions", json=payload1, headers=admin_headers)
        assert res1.status_code == 201
        ex_id = res1.json()["id"]

        # Thu hồi chính sách 1 (chuyển sang REVOKED)
        res_revoke = client.post(f"/api/v1/fee-exemptions/{ex_id}/revoke", headers=admin_headers)
        assert res_revoke.status_code == 200

        # Tạo chính sách mới thay thế cùng khoảng thời gian -> Thành công vì chính sách cũ đã REVOKED
        payload2 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Chính sách mới thay thế",
            "valid_from": "2026-01-01",
            "valid_to": "2026-12-31",
        }
        res2 = client.post("/api/v1/fee-exemptions", json=payload2, headers=admin_headers)
        assert res2.status_code == 201
        assert res2.json()["reason"] == "Chính sách mới thay thế"

    def test_allowed_for_different_households_same_fee_type_201(
        self, client, admin_headers, sample_household, sample_household_2, sample_fee_type_fixed
    ):
        payload1 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Hộ 1",
            "valid_from": "2026-01-01",
        }
        payload2 = {
            "household_id": sample_household_2.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Hộ 2",
            "valid_from": "2026-01-01",
        }
        res1 = client.post("/api/v1/fee-exemptions", json=payload1, headers=admin_headers)
        res2 = client.post("/api/v1/fee-exemptions", json=payload2, headers=admin_headers)
        assert res1.status_code == 201
        assert res2.status_code == 201

    def test_allowed_for_same_household_different_fee_types_201(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, sample_fee_type_metered
    ):
        payload1 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_fixed.id,
            "discount_type": "PERCENT",
            "discount_value": 50,
            "reason": "Khoản thu An ninh",
            "valid_from": "2026-01-01",
        }
        payload2 = {
            "household_id": sample_household.id,
            "fee_type_id": sample_fee_type_metered.id,
            "discount_type": "PERCENT",
            "discount_value": 30,
            "reason": "Khoản thu Quản lý",
            "valid_from": "2026-01-01",
        }
        res1 = client.post("/api/v1/fee-exemptions", json=payload1, headers=admin_headers)
        res2 = client.post("/api/v1/fee-exemptions", json=payload2, headers=admin_headers)
        assert res1.status_code == 201
        assert res2.status_code == 201


# ==============================================================================
# 6. Test Suite: Thu hồi chính sách miễn giảm (US-16)
# ==============================================================================

class TestRevokeFeeExemption:
    """Kiểm tra thu hồi chính sách miễn giảm (POST /fee-exemptions/{id}/revoke)."""

    def test_revoke_not_found_fails_404(self, client, admin_headers):
        res = client.post("/api/v1/fee-exemptions/999999/revoke", headers=admin_headers)
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_revoke_active_exemption_success_200(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, db_session
    ):
        ex = FeeExemption(
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="PERCENT",
            discount_value=30,
            reason="Cần thu hồi",
            valid_from=date(2026, 1, 1),
            status="ACTIVE",
        )
        db_session.add(ex)
        db_session.commit()

        res = client.post(f"/api/v1/fee-exemptions/{ex.id}/revoke", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == ex.id
        assert data["status"] == "REVOKED"

        # Kiểm tra database đã cập nhật
        db_session.expire_all()
        reloaded = db_session.get(FeeExemption, ex.id)
        assert reloaded.status == "REVOKED"

    def test_revoke_already_revoked_fails_409(
        self, client, admin_headers, sample_household, sample_fee_type_fixed, db_session
    ):
        """Kiểm tra mã lỗi 409 ALREADY_REVOKED theo docs/openapi.yaml."""
        ex = FeeExemption(
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="PERCENT",
            discount_value=30,
            reason="Đã thu hồi trước đó",
            valid_from=date(2026, 1, 1),
            status="REVOKED",
        )
        db_session.add(ex)
        db_session.commit()

        res = client.post(f"/api/v1/fee-exemptions/{ex.id}/revoke", headers=admin_headers)
        assert res.status_code == 409
        assert res.json()["code"] == "ALREADY_REVOKED"
        assert "đã bị thu hồi trước đó" in res.json()["message"]

    def test_revoke_records_audit_log(
        self, client, accountant_headers, sample_household, sample_fee_type_fixed, db_session
    ):
        ex = FeeExemption(
            household_id=sample_household.id,
            fee_type_id=sample_fee_type_fixed.id,
            discount_type="AMOUNT",
            discount_value=25000,
            reason="Thu hồi kèm ghi log",
            valid_from=date(2026, 1, 1),
            status="ACTIVE",
        )
        db_session.add(ex)
        db_session.commit()

        res = client.post(f"/api/v1/fee-exemptions/{ex.id}/revoke", headers=accountant_headers)
        assert res.status_code == 200

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "FEE_EXEMPTION",
                AuditLog.action == "REVOKE_EXEMPTION",
                AuditLog.entity_id == str(ex.id),
            )
        )
        assert audit is not None
        assert audit.user_id == 2  # sub=2 của accountant
        assert audit.old_value == {"status": "ACTIVE"}
        assert audit.new_value == {"status": "REVOKED"}
        assert f"Thu hồi chính sách miễn giảm ID {ex.id}" in audit.reason
