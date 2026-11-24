"""
Test Suite for User Story US-38: Nhập chỉ số điện nước (Utility Readings Input).

Specification & Standards:
- docs/openapi.yaml:
  - GET /utility-readings (listUtilityReadings, US-38)
  - POST /utility-readings (createUtilityReading, US-38)
  - PATCH /utility-readings/{id} (updateUtilityReading, US-38)
- docs/API_CONTRACT.md (Section 3.14.8, 3.14.9, 3.14.10)
- docs/PRODUCT_BACKLOG.md (F-07.1, AC-38.1):
  - Given Kế toán chọn kỳ tháng và nhập chỉ số đầu/cuối kỳ cho từng hộ,
  - When lưu,
  - Then hệ thống tính lượng tiêu thụ (cuối - đầu) và tính tiền theo biểu giá đã cấu hình.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select, text

from app.core.security import create_access_token, get_password_hash
from app.models.billing import BillingPeriod, UtilityReading
from app.models.fee import FeeRate, FeeType
from app.models.property import Apartment, Household
from app.models.user import AuditLog, User

US38_HOUSEHOLD_CODES = ("HH_US38_01", "HH_US38_02", "HH_US38_03")
US38_FEE_CODES = ("FEE_US38_ELEC", "FEE_US38_WATER")


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
    user = db_session.scalar(select(User).where(User.username == "treasurer_test_us38"))
    if not user:
        user = User(
            id=538,
            username="treasurer_test_us38",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test US38",
            email="treasurer_38@bluemoon.local",
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
def clean_us38_tables(db_session):
    """Dọn dẹp sạch sẽ dữ liệu của suite test US-38 trước và sau mỗi test."""
    def _cleanup():
        db_session.query(AuditLog).filter(
            AuditLog.entity_type.in_(("UTILITY_READING", "BILLING_PERIOD"))
        ).delete(synchronize_session=False)

        # Xóa các chỉ số điện nước test
        db_session.query(UtilityReading).delete(synchronize_session=False)
        db_session.query(BillingPeriod).delete(synchronize_session=False)

        # Xóa đơn giá và loại phí test
        db_session.query(FeeRate).delete(synchronize_session=False)
        db_session.query(FeeType).filter(FeeType.code.in_(US38_FEE_CODES)).delete(synchronize_session=False)

        # Xóa căn hộ và hộ test
        for tbl in ["apartment_occupancies", "resident_members", "residents", "households", "apartments"]:
            try:
                db_session.execute(text(f"DELETE FROM {tbl}"))
            except Exception:
                pass
        db_session.commit()

    _cleanup()
    yield
    _cleanup()


@pytest.fixture
def setup_utility_environment(db_session):
    """Thiết lập môi trường chuẩn cho US-38: Hộ gia đình, Khoản thu Điện/Nước và Biểu giá."""
    # 1. Hộ gia đình
    hh1 = Household(household_code="HH_US38_01", status="ACTIVE")
    hh2 = Household(household_code="HH_US38_02", status="ACTIVE")
    hh3 = Household(household_code="HH_US38_03", status="ACTIVE")
    db_session.add_all([hh1, hh2, hh3])
    db_session.flush()

    # 2. Loại phí Điện (tính theo kWh)
    ft_elec = FeeType(
        code="FEE_US38_ELEC",
        name="Tiền điện sinh hoạt",
        fee_group="ELECTRICITY",
        calc_method="PER_INDEX",
        unit_label="kWh",
        status="ACTIVE",
    )
    # 3. Loại phí Nước (tính theo m3)
    ft_water = FeeType(
        code="FEE_US38_WATER",
        name="Tiền nước sinh hoạt",
        fee_group="WATER",
        calc_method="PER_INDEX",
        unit_label="m³",
        status="ACTIVE",
    )
    db_session.add_all([ft_elec, ft_water])
    db_session.flush()

    # 4. Đơn giá hiệu lực từ ngày 01/01/2026:
    # Điện: 2.500 đ/kWh
    # Nước: 15.000 đ/m3
    rate_elec = FeeRate(
        fee_type_id=ft_elec.id,
        unit_price=Decimal("2500.00"),
        effective_from=date(2026, 1, 1),
    )
    rate_water = FeeRate(
        fee_type_id=ft_water.id,
        unit_price=Decimal("15000.00"),
        effective_from=date(2026, 1, 1),
    )
    db_session.add_all([rate_elec, rate_water])
    db_session.flush()

    # 5. Kỳ thu phí tháng 11/2026 (OPEN)
    period_nov = BillingPeriod(
        period_month=date(2026, 11, 1),
        name="Kỳ thu tháng 11/2026",
        status="OPEN",
        due_date=date(2026, 11, 25),
    )
    # 6. Kỳ thu phí tháng 10/2026 (CLOSED)
    period_oct = BillingPeriod(
        period_month=date(2026, 10, 1),
        name="Kỳ thu tháng 10/2026",
        status="CLOSED",
        due_date=date(2026, 10, 25),
    )
    db_session.add_all([period_nov, period_oct])
    db_session.commit()

    return {
        "hh1_id": hh1.id,
        "hh2_id": hh2.id,
        "hh3_id": hh3.id,
        "ft_elec_id": ft_elec.id,
        "ft_water_id": ft_water.id,
        "period_nov_id": period_nov.id,
        "period_oct_id": period_oct.id,
    }


# ==============================================================================
# GROUP 1: PHÂN QUYỀN TRUY CẬP (RBAC - US-38)
# ==============================================================================

def test_rbac_list_utility_readings(client, admin_headers, accountant_headers, treasurer_headers, resident_headers):
    """GET /utility-readings: Chỉ ADMIN và ACCOUNTANT được xem, chặn TREASURER và RESIDENT."""
    # ADMIN: 200 OK
    res_admin = client.get("/api/v1/utility-readings", headers=admin_headers)
    assert res_admin.status_code == 200

    # ACCOUNTANT: 200 OK
    res_acc = client.get("/api/v1/utility-readings", headers=accountant_headers)
    assert res_acc.status_code == 200

    # TREASURER: 403 Forbidden
    res_tre = client.get("/api/v1/utility-readings", headers=treasurer_headers)
    assert res_tre.status_code == 403

    # RESIDENT: 403 Forbidden
    res_res = client.get("/api/v1/utility-readings", headers=resident_headers)
    assert res_res.status_code == 403

    # Không đăng nhập: 401 Unauthorized
    res_anon = client.get("/api/v1/utility-readings")
    assert res_anon.status_code == 401


def test_rbac_create_utility_reading(client, admin_headers, accountant_headers, treasurer_headers, resident_headers, setup_utility_environment):
    """POST /utility-readings: Chỉ ADMIN và ACCOUNTANT được tạo chỉ số, chặn các role khác."""
    env = setup_utility_environment
    payload = {
        "household_id": env["hh1_id"],
        "fee_type_id": env["ft_elec_id"],
        "billing_period_id": env["period_nov_id"],
        "previous_index": 100.0,
        "current_index": 150.0,
    }

    # TREASURER: 403 Forbidden
    res_tre = client.post("/api/v1/utility-readings", json=payload, headers=treasurer_headers)
    assert res_tre.status_code == 403

    # RESIDENT: 403 Forbidden
    res_res = client.post("/api/v1/utility-readings", json=payload, headers=resident_headers)
    assert res_res.status_code == 403

    # Không đăng nhập: 401 Unauthorized
    res_anon = client.post("/api/v1/utility-readings", json=payload)
    assert res_anon.status_code == 401

    # ACCOUNTANT: 201 Created
    res_acc = client.post("/api/v1/utility-readings", json=payload, headers=accountant_headers)
    assert res_acc.status_code == 201


def test_rbac_update_utility_reading(client, admin_headers, accountant_headers, treasurer_headers, resident_headers, setup_utility_environment):
    """PATCH /utility-readings/{id}: Chỉ ADMIN và ACCOUNTANT được sửa chỉ số."""
    env = setup_utility_environment
    # Tạo trước 1 bản ghi
    res_init = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    reading_id = res_init.json()["id"]

    patch_payload = {"current_index": 160.0}

    # TREASURER: 403 Forbidden
    res_tre = client.patch(f"/api/v1/utility-readings/{reading_id}", json=patch_payload, headers=treasurer_headers)
    assert res_tre.status_code == 403

    # RESIDENT: 403 Forbidden
    res_res = client.patch(f"/api/v1/utility-readings/{reading_id}", json=patch_payload, headers=resident_headers)
    assert res_res.status_code == 403

    # ACCOUNTANT: 200 OK
    res_acc = client.patch(f"/api/v1/utility-readings/{reading_id}", json=patch_payload, headers=accountant_headers)
    assert res_acc.status_code == 200


def test_rbac_password_change_required_blocked(client, db_session, setup_utility_environment):
    """User có must_change_password=True bị chặn 403 PASSWORD_CHANGE_REQUIRED."""
    user = db_session.get(User, 2)
    user.must_change_password = True
    db_session.commit()
    try:
        headers = make_headers(role="ACCOUNTANT", sub="2", username="accountant_test", must_change_password=True)
        res = client.get("/api/v1/utility-readings", headers=headers)
        assert res.status_code == 403
        assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    finally:
        user.must_change_password = False
        db_session.commit()


# ==============================================================================
# GROUP 2: TÍNH TOÁN & NHẬP CHỈ SỐ THÀNH CÔNG (AC-38.1 HAPPY PATHS)
# ==============================================================================

def test_create_reading_auto_unit_price_from_fee_rates(client, accountant_headers, setup_utility_environment):
    """
    AC-38.1: Given Kế toán chọn kỳ tháng và nhập chỉ số đầu/cuối kỳ cho hộ,
    When lưu mà không truyền unit_price,
    Then hệ thống tính lượng tiêu thụ (cuối - đầu) và tính tiền theo biểu giá đã cấu hình.
    """
    env = setup_utility_environment
    # Hộ 1: Chỉ số điện đầu 100, cuối 250 -> Tiêu thụ: 150 kWh
    # Biểu giá điện đã cấu hình: 2.500 đ/kWh -> Thành tiền: 150 * 2.500 = 375.000 đ
    payload = {
        "household_id": env["hh1_id"],
        "fee_type_id": env["ft_elec_id"],
        "billing_period_id": env["period_nov_id"],
        "previous_index": 100.0,
        "current_index": 250.0,
    }
    res = client.post("/api/v1/utility-readings", json=payload, headers=accountant_headers)
    assert res.status_code == 201
    data = res.json()

    assert data["household_id"] == env["hh1_id"]
    assert data["fee_type_id"] == env["ft_elec_id"]
    assert data["billing_period_id"] == env["period_nov_id"]
    assert data["previous_index"] == 100.0
    assert data["current_index"] == 250.0
    assert data["consumption"] == 150.0
    assert data["unit_price"] == 2500
    assert data["amount"] == 375000
    assert data["recorded_by"] == 2  # accountant sub=2


def test_create_reading_with_custom_unit_price(client, accountant_headers, setup_utility_environment):
    """Nhập chỉ số có truyền unit_price tùy chọn -> Hệ thống ưu tiên dùng unit_price được truyền."""
    env = setup_utility_environment
    # Nước: đầu 10, cuối 30 -> Tiêu thụ: 20 m3. Đơn giá chỉ định: 18.000 đ/m3 (thay vì 15.000 đ/m3)
    payload = {
        "household_id": env["hh2_id"],
        "fee_type_id": env["ft_water_id"],
        "billing_period_id": env["period_nov_id"],
        "previous_index": 10.0,
        "current_index": 30.0,
        "unit_price": 18000,
    }
    res = client.post("/api/v1/utility-readings", json=payload, headers=accountant_headers)
    assert res.status_code == 201
    data = res.json()

    assert data["consumption"] == 20.0
    assert data["unit_price"] == 18000
    assert data["amount"] == 360000  # 20 * 18.000


def test_create_reading_with_decimal_indexes(client, admin_headers, setup_utility_environment):
    """Nhập chỉ số có phần thập phân -> Tính lượng tiêu thụ và thành tiền chính xác."""
    env = setup_utility_environment
    # Điện: 120.25 -> 145.75 -> Tiêu thụ: 25.5 kWh. Đơn giá: 2.500 đ -> Thành tiền: 63.750 đ
    payload = {
        "household_id": env["hh1_id"],
        "fee_type_id": env["ft_elec_id"],
        "billing_period_id": env["period_nov_id"],
        "previous_index": 120.25,
        "current_index": 145.75,
    }
    res = client.post("/api/v1/utility-readings", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()

    assert data["consumption"] == 25.5
    assert data["unit_price"] == 2500
    assert data["amount"] == 63750


def test_create_reading_zero_consumption(client, admin_headers, setup_utility_environment):
    """Chỉ số đầu bằng chỉ số cuối (nhà không sử dụng) -> consumption = 0, amount = 0."""
    env = setup_utility_environment
    payload = {
        "household_id": env["hh3_id"],
        "fee_type_id": env["ft_water_id"],
        "billing_period_id": env["period_nov_id"],
        "previous_index": 50.0,
        "current_index": 50.0,
    }
    res = client.post("/api/v1/utility-readings", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()

    assert data["consumption"] == 0.0
    assert data["amount"] == 0


def test_create_reading_applies_correct_historical_fee_rate(client, admin_headers, db_session, setup_utility_environment):
    """Hệ thống chọn đúng đơn giá có hiệu lực tại ngày period_month khi có nhiều mức giá theo thời gian."""
    env = setup_utility_environment

    # Thêm đơn giá tương lai từ 01/12/2026: 3.000 đ/kWh (không được dùng cho kỳ tháng 11)
    rate_future = FeeRate(
        fee_type_id=env["ft_elec_id"],
        unit_price=Decimal("3000.00"),
        effective_from=date(2026, 12, 1),
    )
    # Thêm đơn giá cũ từ 01/01/2025: 2.000 đ/kWh
    rate_old = FeeRate(
        fee_type_id=env["ft_elec_id"],
        unit_price=Decimal("2000.00"),
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add_all([rate_future, rate_old])
    db_session.commit()

    # Kỳ thu tháng 11/2026 -> Đơn giá hiệu lực đúng là 2.500 đ (từ 01/01/2026), không phải 3.000 hay 2.000
    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 0.0,
            "current_index": 100.0,
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    assert res.json()["unit_price"] == 2500
    assert res.json()["amount"] == 250000


def test_create_reading_audit_log_recorded(client, admin_headers, db_session, setup_utility_environment):
    """Nhập chỉ số điện nước phải ghi nhận AuditLog đầy đủ chi tiết."""
    env = setup_utility_environment
    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 10.0,
            "current_index": 60.0,
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    reading_id = res.json()["id"]

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "CREATE_UTILITY_READING",
            AuditLog.entity_id == str(reading_id),
        )
    )
    assert audit is not None
    assert audit.entity_type == "UTILITY_READING"
    assert audit.new_value["consumption"] == 50.0
    assert audit.new_value["amount"] == 125000


# ==============================================================================
# GROUP 3: KIỂM SOÁT LỖI & RÀNG BUỘC NGHIỆP VỤ (VALIDATION & CONFLICTS)
# ==============================================================================

def test_create_reading_fails_when_current_less_than_previous(client, admin_headers, setup_utility_environment):
    """current_index < previous_index -> 400 Bad Request (VALIDATION_ERROR)."""
    env = setup_utility_environment
    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 150.0,
            "current_index": 100.0,  # Sai: cuối nhỏ hơn đầu
        },
        headers=admin_headers,
    )
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_create_reading_fails_when_household_not_found(client, admin_headers, setup_utility_environment):
    """household_id không tồn tại -> 404 NOT_FOUND."""
    env = setup_utility_environment
    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": 999999,
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_create_reading_fails_when_period_not_found(client, admin_headers, setup_utility_environment):
    """billing_period_id không tồn tại -> 404 NOT_FOUND."""
    env = setup_utility_environment
    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": 999999,
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_create_reading_fails_when_fee_type_not_found(client, admin_headers, setup_utility_environment):
    """fee_type_id không tồn tại -> 404 NOT_FOUND."""
    env = setup_utility_environment
    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": 999999,
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_create_reading_fails_when_period_closed(client, admin_headers, setup_utility_environment):
    """Kỳ thu đã đóng (CLOSED) -> 409 Conflict (PERIOD_CLOSED)."""
    env = setup_utility_environment
    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_oct_id"],  # Kỳ tháng 10 đã CLOSED
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["code"] == "PERIOD_CLOSED"


def test_create_reading_fails_when_duplicate(client, admin_headers, setup_utility_environment):
    """Chỉ số cho cùng 1 hộ, 1 loại phí trong 1 kỳ đã tồn tại -> 409 Conflict (DUPLICATE_READING)."""
    env = setup_utility_environment
    payload = {
        "household_id": env["hh1_id"],
        "fee_type_id": env["ft_elec_id"],
        "billing_period_id": env["period_nov_id"],
        "previous_index": 100.0,
        "current_index": 150.0,
    }
    # Nhập lần 1: Thành công
    res1 = client.post("/api/v1/utility-readings", json=payload, headers=admin_headers)
    assert res1.status_code == 201

    # Nhập lần 2 trùng lặp: 409 Conflict
    res2 = client.post("/api/v1/utility-readings", json=payload, headers=admin_headers)
    assert res2.status_code == 409
    assert res2.json()["code"] == "DUPLICATE_READING"


def test_create_reading_fails_when_no_unit_price_and_no_effective_rate(client, admin_headers, db_session, setup_utility_environment):
    """Bỏ trống unit_price nhưng không có cấu hình đơn giá cho khoản thu -> 400 Bad Request."""
    env = setup_utility_environment
    # Tạo loại phí mới chưa có FeeRate nào
    ft_empty = FeeType(
        code="FEE_US38_GAS",
        name="Phí Gas trung tâm",
        fee_group="OTHER",
        calc_method="PER_INDEX",
        unit_label="m³",
        status="ACTIVE",
    )
    db_session.add(ft_empty)
    db_session.commit()

    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": ft_empty.id,
            "billing_period_id": env["period_nov_id"],
            "previous_index": 10.0,
            "current_index": 20.0,
            # Không truyền unit_price
        },
        headers=admin_headers,
    )
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


# ==============================================================================
# GROUP 4: SỬA CHỈ SỐ ĐIỆN NƯỚC (PATCH /utility-readings/{id})
# ==============================================================================

def test_update_reading_current_index_recalculates_amount(client, admin_headers, setup_utility_environment):
    """Sửa current_index -> Hệ thống tự động tính lại consumption và amount."""
    env = setup_utility_environment
    # Tạo ban đầu: 100 -> 150 (tiêu thụ 50, đơn giá 2500 -> 125.000 đ)
    res_init = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    reading_id = res_init.json()["id"]

    # Sửa current_index thành 180 (tiêu thụ 80 -> amount = 80 * 2500 = 200.000 đ)
    res_patch = client.patch(
        f"/api/v1/utility-readings/{reading_id}",
        json={"current_index": 180.0},
        headers=admin_headers,
    )
    assert res_patch.status_code == 200
    data = res_patch.json()
    assert data["current_index"] == 180.0
    assert data["consumption"] == 80.0
    assert data["amount"] == 200000


def test_update_reading_previous_index_recalculates_amount(client, admin_headers, setup_utility_environment):
    """Sửa previous_index -> Hệ thống tự động tính lại consumption và amount."""
    env = setup_utility_environment
    # Tạo ban đầu: 100 -> 150 (tiêu thụ 50 -> 125.000 đ)
    res_init = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    reading_id = res_init.json()["id"]

    # Sửa previous_index thành 120 (tiêu thụ 30 -> amount = 30 * 2500 = 75.000 đ)
    res_patch = client.patch(
        f"/api/v1/utility-readings/{reading_id}",
        json={"previous_index": 120.0},
        headers=admin_headers,
    )
    assert res_patch.status_code == 200
    data = res_patch.json()
    assert data["previous_index"] == 120.0
    assert data["consumption"] == 30.0
    assert data["amount"] == 75000


def test_update_reading_unit_price_recalculates_amount(client, admin_headers, setup_utility_environment):
    """Sửa unit_price -> Hệ thống tự động tính lại amount."""
    env = setup_utility_environment
    # Tạo ban đầu: 100 -> 150 (tiêu thụ 50, giá 2500 -> 125.000 đ)
    res_init = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    reading_id = res_init.json()["id"]

    # Sửa unit_price thành 3000 (amount = 50 * 3000 = 150.000 đ)
    res_patch = client.patch(
        f"/api/v1/utility-readings/{reading_id}",
        json={"unit_price": 3000},
        headers=admin_headers,
    )
    assert res_patch.status_code == 200
    data = res_patch.json()
    assert data["unit_price"] == 3000
    assert data["amount"] == 150000


def test_update_reading_fails_when_not_found(client, admin_headers):
    """Cập nhật ID không tồn tại -> 404 NOT_FOUND."""
    res = client.patch(
        "/api/v1/utility-readings/999999",
        json={"current_index": 200.0},
        headers=admin_headers,
    )
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_update_reading_fails_when_period_closed(client, admin_headers, db_session, setup_utility_environment):
    """Kỳ thu đã đóng -> 409 Conflict (PERIOD_CLOSED)."""
    env = setup_utility_environment
    # Tạo trước 1 reading
    res_init = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    reading_id = res_init.json()["id"]

    # Đóng kỳ thu tháng 11
    period = db_session.get(BillingPeriod, env["period_nov_id"])
    period.status = "CLOSED"
    db_session.commit()

    # Thử sửa reading -> 409 PERIOD_CLOSED
    res = client.patch(
        f"/api/v1/utility-readings/{reading_id}",
        json={"current_index": 180.0},
        headers=admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["code"] == "PERIOD_CLOSED"


def test_update_reading_fails_when_current_less_than_previous(client, admin_headers, setup_utility_environment):
    """Sửa khiến current_index < previous_index -> 400 Bad Request."""
    env = setup_utility_environment
    # Ban đầu: 100 -> 150
    res_init = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    reading_id = res_init.json()["id"]

    # Sửa current_index thành 80 (< 100) -> 400
    res1 = client.patch(
        f"/api/v1/utility-readings/{reading_id}",
        json={"current_index": 80.0},
        headers=admin_headers,
    )
    assert res1.status_code == 400
    assert res1.json()["code"] == "VALIDATION_ERROR"

    # Sửa previous_index thành 170 (> 150) -> 400
    res2 = client.patch(
        f"/api/v1/utility-readings/{reading_id}",
        json={"previous_index": 170.0},
        headers=admin_headers,
    )
    assert res2.status_code == 400
    assert res2.json()["code"] == "VALIDATION_ERROR"


def test_update_reading_audit_log_recorded(client, admin_headers, db_session, setup_utility_environment):
    """Cập nhật chỉ số phải ghi nhận AuditLog với old_value và new_value."""
    env = setup_utility_environment
    res_init = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 100.0,
            "current_index": 150.0,
        },
        headers=admin_headers,
    )
    reading_id = res_init.json()["id"]

    client.patch(
        f"/api/v1/utility-readings/{reading_id}",
        json={"current_index": 200.0},
        headers=admin_headers,
    )

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "UPDATE_UTILITY_READING",
            AuditLog.entity_id == str(reading_id),
        )
    )
    assert audit is not None
    assert audit.old_value["current_index"] == 150.0
    assert audit.old_value["amount"] == 125000
    assert audit.new_value["current_index"] == 200.0
    assert audit.new_value["amount"] == 250000


# ==============================================================================
# GROUP 5: TRA CỨU DANH SÁCH & BỘ LỌC (GET /utility-readings)
# ==============================================================================

def test_list_readings_pagination_and_filters(client, admin_headers, setup_utility_environment):
    """Tra cứu danh sách chỉ số điện nước có phân trang và bộ lọc theo kỳ, loại phí, hộ."""
    env = setup_utility_environment

    # Tạo 3 bản ghi:
    # 1. Hộ 1 - Điện - Kỳ Nov
    client.post(
        "/api/v1/utility-readings",
        json={"household_id": env["hh1_id"], "fee_type_id": env["ft_elec_id"], "billing_period_id": env["period_nov_id"], "previous_index": 0.0, "current_index": 50.0},
        headers=admin_headers,
    )
    # 2. Hộ 1 - Nước - Kỳ Nov
    client.post(
        "/api/v1/utility-readings",
        json={"household_id": env["hh1_id"], "fee_type_id": env["ft_water_id"], "billing_period_id": env["period_nov_id"], "previous_index": 0.0, "current_index": 20.0},
        headers=admin_headers,
    )
    # 3. Hộ 2 - Điện - Kỳ Nov
    client.post(
        "/api/v1/utility-readings",
        json={"household_id": env["hh2_id"], "fee_type_id": env["ft_elec_id"], "billing_period_id": env["period_nov_id"], "previous_index": 10.0, "current_index": 40.0},
        headers=admin_headers,
    )

    # 1. Phân trang: page_size=2
    res_page = client.get("/api/v1/utility-readings?page=1&page_size=2", headers=admin_headers)
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert page_data["total"] == 3
    assert page_data["page"] == 1
    assert page_data["page_size"] == 2
    assert page_data["total_pages"] == 2
    assert len(page_data["items"]) == 2

    # 2. Lọc theo hộ gia đình (household_id)
    res_hh = client.get(f"/api/v1/utility-readings?household_id={env['hh1_id']}", headers=admin_headers)
    assert res_hh.status_code == 200
    assert res_hh.json()["total"] == 2

    # 3. Lọc theo loại phí (fee_type_id)
    res_fee = client.get(f"/api/v1/utility-readings?fee_type_id={env['ft_elec_id']}", headers=admin_headers)
    assert res_fee.status_code == 200
    assert res_fee.json()["total"] == 2

    # 4. Lọc kết hợp (household_id + fee_type_id)
    res_combo = client.get(
        f"/api/v1/utility-readings?household_id={env['hh1_id']}&fee_type_id={env['ft_water_id']}",
        headers=admin_headers,
    )
    assert res_combo.status_code == 200
    assert res_combo.json()["total"] == 1
    assert res_combo.json()["items"][0]["household_id"] == env["hh1_id"]
    assert res_combo.json()["items"][0]["fee_type_id"] == env["ft_water_id"]


def test_update_reading_both_indexes(client, admin_headers, setup_utility_environment):
    """Cập nhật đồng thời cả previous_index và current_index trong một request."""
    env = setup_utility_environment
    res_init = client.post(
        "/api/v1/utility-readings",
        json={"household_id": env["hh1_id"], "fee_type_id": env["ft_elec_id"], "billing_period_id": env["period_nov_id"], "previous_index": 50.0, "current_index": 100.0},
        headers=admin_headers,
    )
    reading_id = res_init.json()["id"]

    res_patch = client.patch(
        f"/api/v1/utility-readings/{reading_id}",
        json={"previous_index": 80.0, "current_index": 150.0},
        headers=admin_headers,
    )
    assert res_patch.status_code == 200
    data = res_patch.json()
    assert data["previous_index"] == 80.0
    assert data["current_index"] == 150.0
    assert data["consumption"] == 70.0
    assert data["amount"] == 175000  # 70 * 2500


def test_list_readings_empty_result_when_no_match(client, admin_headers, setup_utility_environment):
    """Lọc với điều kiện không có bản ghi nào khớp -> Trả về danh sách rỗng (total=0, items=[])."""
    res = client.get("/api/v1/utility-readings?billing_period_id=999999", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["total_pages"] == 0


def test_create_reading_large_index_values(client, admin_headers, setup_utility_environment):
    """Nhập chỉ số lớn (vượt ngưỡng hàng trăm ngàn) -> Tính toán chính xác không tràn số."""
    env = setup_utility_environment
    res = client.post(
        "/api/v1/utility-readings",
        json={
            "household_id": env["hh1_id"],
            "fee_type_id": env["ft_elec_id"],
            "billing_period_id": env["period_nov_id"],
            "previous_index": 999000.0,
            "current_index": 1000500.0,  # Tiêu thụ 1.500 kWh
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["consumption"] == 1500.0
    assert data["amount"] == 3750000  # 1500 * 2500


def test_create_readings_multiple_households_same_period(client, admin_headers, setup_utility_environment):
    """Nhiều hộ gia đình khác nhau cùng nhập chỉ số cho cùng 1 loại phí trong cùng 1 kỳ -> Thành công."""
    env = setup_utility_environment
    res1 = client.post(
        "/api/v1/utility-readings",
        json={"household_id": env["hh1_id"], "fee_type_id": env["ft_elec_id"], "billing_period_id": env["period_nov_id"], "previous_index": 10.0, "current_index": 50.0},
        headers=admin_headers,
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/utility-readings",
        json={"household_id": env["hh2_id"], "fee_type_id": env["ft_elec_id"], "billing_period_id": env["period_nov_id"], "previous_index": 20.0, "current_index": 70.0},
        headers=admin_headers,
    )
    assert res2.status_code == 201


def test_reading_response_contains_household_code_and_fee_name(client, admin_headers, setup_utility_environment):
    """Thông tin trả về phải chứa household_code và fee_name đầy đủ."""
    env = setup_utility_environment
    res = client.post(
        "/api/v1/utility-readings",
        json={"household_id": env["hh1_id"], "fee_type_id": env["ft_elec_id"], "billing_period_id": env["period_nov_id"], "previous_index": 0.0, "current_index": 100.0},
        headers=admin_headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["household_code"] == "HH_US38_01"
    assert data["fee_name"] == "Tiền điện sinh hoạt"

