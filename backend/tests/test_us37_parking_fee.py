"""
Test Suite for User Story US-37: Tính Phí gửi xe (Parking Fee Calculation).

Specification & Standards:
- docs/openapi.yaml:
  - POST /billing-periods (createBillingPeriod, US-17)
  - GET /billing-periods (listBillingPeriods, US-17)
  - GET /billing-periods/{id} (getBillingPeriod, US-17)
  - POST /billing-periods/{id}/generate (generateInvoices, US-17, US-37)
  - POST /billing-periods/{id}/close (closeBillingPeriod, US-17)
  - GET /invoices (listInvoices, US-17, US-47)
  - GET /invoices/{id} (getInvoice, US-47)
- docs/API_CONTRACT.md (Section 3.14)
- docs/PRODUCT_BACKLOG.md (F-06.2, AC-37.1):
  - Given phương tiện đã đăng ký của hộ (status = 'ACTIVE')
  - When Kế toán tạo kỳ thu phí gửi xe tháng đó
  - Then hệ thống tính số tiền = đơn giá theo loại xe × số xe đăng ký của hộ và ghi vào bảng phải nộp.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import delete, select, text

from app.core.security import create_access_token, get_password_hash
from app.models.billing import BillingPeriod, Invoice, InvoiceItem
from app.models.fee import FeeExemption, FeeRate, FeeType
from app.models.property import Apartment, ApartmentOccupancy, Household
from app.models.user import AuditLog, User
from app.models.vehicle import Vehicle

US37_HOUSEHOLD_CODES = ("HH_US37_01", "HH_US37_02", "HH_US37_03", "HH_US37_NO_VEHICLE")
US37_FEE_CODES = ("FEE_US37_MOTO", "FEE_US37_CAR", "FEE_US37_BIKE", "FEE_US37_MGT")
US37_APT_CODES = ("APT_US37_101", "APT_US37_102", "APT_US37_103")


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
    user = db_session.scalar(select(User).where(User.username == "treasurer_test_us37"))
    if not user:
        user = User(
            id=537,
            username="treasurer_test_us37",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test US37",
            email="treasurer_37@bluemoon.local",
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
def clean_us37_tables(db_session):
    """Dọn dẹp sạch sẽ dữ liệu của suite test US-37 trước và sau mỗi test."""
    def _cleanup():
        db_session.query(AuditLog).filter(
            AuditLog.entity_type.in_(("BILLING_PERIOD", "INVOICE"))
        ).delete(synchronize_session=False)

        # Xóa các hóa đơn và dòng phí liên quan
        db_session.query(InvoiceItem).delete(synchronize_session=False)
        db_session.query(Invoice).delete(synchronize_session=False)
        db_session.query(BillingPeriod).delete(synchronize_session=False)

        # Xóa xe cộ test
        db_session.query(Vehicle).delete(synchronize_session=False)

        # Xóa miễn giảm, đơn giá, loại phí test
        db_session.query(FeeExemption).delete(synchronize_session=False)
        db_session.query(FeeRate).delete(synchronize_session=False)
        db_session.query(FeeType).filter(FeeType.code.in_(US37_FEE_CODES)).delete(synchronize_session=False)

        # Xóa căn hộ và hộ
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
def setup_parking_environment(db_session):
    """Thiết lập môi trường chuẩn: Hộ gia đình, Căn hộ, Phương tiện và Biểu phí gửi xe."""
    # 1. Căn hộ
    apt1 = Apartment(code="APT_US37_101", floor=1, area_m2=Decimal("80.00"), status="ACTIVE")
    apt2 = Apartment(code="APT_US37_102", floor=1, area_m2=Decimal("100.00"), status="ACTIVE")
    db_session.add_all([apt1, apt2])
    db_session.flush()

    # 2. Hộ gia đình
    hh1 = Household(household_code="HH_US37_01", status="ACTIVE")  # Hộ có 2 xe máy + 1 ô tô
    hh2 = Household(household_code="HH_US37_02", status="ACTIVE")  # Hộ có 1 xe đạp + 1 xe máy
    hh3 = Household(household_code="HH_US37_NO_VEHICLE", status="ACTIVE")  # Hộ không có xe nào
    db_session.add_all([hh1, hh2, hh3])
    db_session.flush()

    # 3. Gán cư trú Căn hộ
    occ1 = ApartmentOccupancy(household_id=hh1.id, apartment_id=apt1.id, start_date=date(2026, 1, 1))
    occ2 = ApartmentOccupancy(household_id=hh2.id, apartment_id=apt2.id, start_date=date(2026, 1, 1))
    db_session.add_all([occ1, occ2])

    # 4. Phương tiện đăng ký (US-36)
    v1_1 = Vehicle(household_id=hh1.id, plate_number="29M1-11111", vehicle_type="MOTORBIKE", status="ACTIVE")
    v1_2 = Vehicle(household_id=hh1.id, plate_number="29M1-22222", vehicle_type="MOTORBIKE", status="ACTIVE")
    v1_3 = Vehicle(household_id=hh1.id, plate_number="30A-88888", vehicle_type="CAR", status="ACTIVE")
    v1_inact = Vehicle(household_id=hh1.id, plate_number="29M1-99999", vehicle_type="MOTORBIKE", status="INACTIVE")  # Xe đã hủy

    v2_1 = Vehicle(household_id=hh2.id, plate_number="29M2-33333", vehicle_type="MOTORBIKE", status="ACTIVE")
    v2_2 = Vehicle(household_id=hh2.id, plate_number="BIKE-001", vehicle_type="BICYCLE", status="ACTIVE")
    db_session.add_all([v1_1, v1_2, v1_3, v1_inact, v2_1, v2_2])

    # 5. Khoản thu Phí gửi xe (US-12)
    ft_moto = FeeType(
        code="FEE_US37_MOTO",
        name="Phí gửi xe máy",
        fee_group="PARKING",
        calc_method="PER_VEHICLE",
        unit_label="xe",
        vehicle_type="MOTORBIKE",
        status="ACTIVE",
    )
    ft_car = FeeType(
        code="FEE_US37_CAR",
        name="Phí gửi ô tô",
        fee_group="PARKING",
        calc_method="PER_VEHICLE",
        unit_label="xe",
        vehicle_type="CAR",
        status="ACTIVE",
    )
    ft_bike = FeeType(
        code="FEE_US37_BIKE",
        name="Phí gửi xe đạp",
        fee_group="PARKING",
        calc_method="PER_VEHICLE",
        unit_label="xe",
        vehicle_type="BICYCLE",
        status="ACTIVE",
    )
    db_session.add_all([ft_moto, ft_car, ft_bike])
    db_session.flush()

    # 6. Đơn giá hiệu lực từ 01/01/2026 (US-14)
    # Xe máy: 70.000 đ | Ô tô: 1.200.000 đ | Xe đạp: 30.000 đ
    fr_moto = FeeRate(fee_type_id=ft_moto.id, unit_price=Decimal("70000.00"), effective_from=date(2026, 1, 1))
    fr_car = FeeRate(fee_type_id=ft_car.id, unit_price=Decimal("1200000.00"), effective_from=date(2026, 1, 1))
    fr_bike = FeeRate(fee_type_id=ft_bike.id, unit_price=Decimal("30000.00"), effective_from=date(2026, 1, 1))
    db_session.add_all([fr_moto, fr_car, fr_bike])
    db_session.commit()

    return {
        "hh1_id": hh1.id,
        "hh2_id": hh2.id,
        "hh3_id": hh3.id,
        "ft_moto_id": ft_moto.id,
        "ft_car_id": ft_car.id,
        "ft_bike_id": ft_bike.id,
    }


# ==============================================================================
# PHẦN 1: RBAC & BẢO MẬT PHÂN HỆ BILLING
# ==============================================================================

def test_rbac_admin_and_accountant_can_create_billing_period(client, admin_headers, accountant_headers):
    """US-17: ADMIN và ACCOUNTANT đều có quyền tạo kỳ thu."""
    res1 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11/2026"},
        headers=admin_headers,
    )
    assert res1.status_code == 201
    assert res1.json()["status"] == "DRAFT"

    res2 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-12-01", "name": "Kỳ 12/2026"},
        headers=accountant_headers,
    )
    assert res2.status_code == 201
    assert res2.json()["status"] == "DRAFT"


def test_rbac_treasurer_and_resident_forbidden_create_billing_period(client, treasurer_headers, resident_headers):
    """US-17: TREASURER và RESIDENT bị chặn tạo kỳ thu (403 FORBIDDEN)."""
    res1 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11/2026"},
        headers=treasurer_headers,
    )
    assert res1.status_code == 403
    assert res1.json()["code"] == "FORBIDDEN"

    res2 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11/2026"},
        headers=resident_headers,
    )
    assert res2.status_code == 403
    assert res2.json()["code"] == "FORBIDDEN"


def test_rbac_unauthenticated_request_rejected(client):
    """Không có token bị từ chối 401 UNAUTHENTICATED."""
    res = client.post("/api/v1/billing-periods", json={"period_month": "2026-11-01", "name": "Kỳ 11/2026"})
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


# ==============================================================================
# PHẦN 2: VALIDATION TẠO KỲ THU (POST /billing-periods)
# ==============================================================================

def test_create_period_not_first_day_of_month_rejected(client, admin_headers):
    """Ngày period_month không phải ngày 1 của tháng -> 400 VALIDATION_ERROR."""
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-15", "name": "Kỳ giữa tháng"},
        headers=admin_headers,
    )
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_create_period_due_date_before_period_month_rejected(client, admin_headers):
    """Hạn nộp phí due_date nhỏ hơn ngày bắt đầu kỳ thu -> 400 VALIDATION_ERROR."""
    res = client.post(
        "/api/v1/billing-periods",
        json={
            "period_month": "2026-11-01",
            "name": "Kỳ 11/2026",
            "due_date": "2026-10-25",
        },
        headers=admin_headers,
    )
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_create_duplicate_period_month_returns_409(client, admin_headers):
    """Trùng tháng kỳ thu đã có -> 409 DUPLICATE_PERIOD."""
    res1 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11 lần 1"},
        headers=admin_headers,
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11 lần 2"},
        headers=admin_headers,
    )
    assert res2.status_code == 409
    assert res2.json()["code"] == "DUPLICATE_PERIOD"


def test_create_period_records_audit_log(client, admin_headers, db_session):
    """Tạo kỳ thu mới phải ghi nhật ký kiểm toán AuditLog."""
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ thu tháng 11 Audit"},
        headers=admin_headers,
    )
    assert res.status_code == 201
    period_id = res.json()["id"]

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "CREATE_BILLING_PERIOD",
            AuditLog.entity_id == str(period_id),
        )
    )
    assert audit is not None
    assert audit.new_value["name"] == "Kỳ thu tháng 11 Audit"


# ==============================================================================
# PHẦN 3: TÂM ĐIỂM US-37 & AC-37.1 (TÍNH PHÍ GỬI XE THEO LOẠI XE VÀ THÁNG)
# ==============================================================================

def test_ac37_1_calculate_parking_fees_multiple_vehicles(client, admin_headers, setup_parking_environment):
    """
    AC-37.1: Given phương tiện đã đăng ký ACTIVE của hộ,
    When Kế toán tạo kỳ thu phí tháng đó,
    Then hệ thống tính số tiền = đơn giá theo loại xe × số xe đăng ký của hộ và ghi vào bảng phải nộp.
    """
    # 1. Tạo kỳ thu tháng 11/2026
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ thu tháng 11/2026"},
        headers=admin_headers,
    )
    assert res.status_code == 201
    period_id = res.json()["id"]

    # 2. Chạy động cơ tính phí (POST /billing-periods/{id}/generate)
    res_gen = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["households_processed"] == 3
    assert gen_data["invoices_created"] == 3

    # 3. Kiểm tra chi tiết giấy báo nộp phí của Hộ 1 (HH_US37_01):
    # Hộ 1 có: 2 xe máy (ACTIVE) + 1 ô tô (ACTIVE) + 1 xe máy (INACTIVE).
    # Đơn giá: Xe máy = 70.000 đ | Ô tô = 1.200.000 đ.
    # Tiền xe máy = 2 * 70.000 = 140.000 đ
    # Tiền ô tô = 1 * 1.200.000 = 1.200.000 đ
    # Tổng phí gửi xe = 1.340.000 đ
    hh1_id = setup_parking_environment["hh1_id"]
    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh1_id}", headers=admin_headers)
    assert res_inv.status_code == 200
    invoices = res_inv.json()["items"]
    assert len(invoices) == 1
    inv1 = invoices[0]

    assert inv1["fee_amount"] == 1340000
    assert inv1["discount_amount"] == 0
    assert inv1["total_due"] == 1340000
    assert inv1["status"] == "UNPAID"

    # Kiểm tra chi tiết từng dòng phí (GET /invoices/{id})
    res_detail = client.get(f"/api/v1/invoices/{inv1['id']}", headers=admin_headers)
    assert res_detail.status_code == 200
    items = res_detail.json()["items"]
    assert len(items) == 2  # Đúng 2 dòng: Xe máy và Ô tô

    # Dòng xe máy
    moto_item = next(it for it in items if it["fee_type_id"] == setup_parking_environment["ft_moto_id"])
    assert moto_item["quantity"] == 2.0
    assert moto_item["unit_price"] == 70000
    assert moto_item["gross_amount"] == 140000
    assert moto_item["net_amount"] == 140000
    assert "2 Phí gửi xe máy × 70,000 đ" in moto_item["description"]

    # Dòng ô tô
    car_item = next(it for it in items if it["fee_type_id"] == setup_parking_environment["ft_car_id"])
    assert car_item["quantity"] == 1.0
    assert car_item["unit_price"] == 1200000
    assert car_item["gross_amount"] == 1200000
    assert car_item["net_amount"] == 1200000
    assert "1 Phí gửi ô tô × 1,200,000 đ" in car_item["description"]


def test_ac37_1_household_with_bike_and_motorbike(client, admin_headers, setup_parking_environment):
    """Hộ 2 có 1 xe máy (70.000) và 1 xe đạp (30.000) -> Tổng phí = 100.000 đ."""
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11/2026 Hộ 2"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]

    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    hh2_id = setup_parking_environment["hh2_id"]
    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh2_id}", headers=admin_headers)
    inv2 = res_inv.json()["items"][0]

    # Tổng tiền = 70.000 + 30.000 = 100.000 đ
    assert inv2["total_due"] == 100000

    res_detail = client.get(f"/api/v1/invoices/{inv2['id']}", headers=admin_headers)
    items = res_detail.json()["items"]
    assert len(items) == 2

    bike_item = next(it for it in items if it["fee_type_id"] == setup_parking_environment["ft_bike_id"])
    assert bike_item["quantity"] == 1.0
    assert bike_item["unit_price"] == 30000
    assert bike_item["net_amount"] == 30000


def test_ac37_1_household_without_vehicles_has_zero_parking_fee(client, admin_headers, setup_parking_environment):
    """Hộ không đăng ký xe nào -> Không sinh dòng phí gửi xe nào."""
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11 Không xe"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    hh3_id = setup_parking_environment["hh3_id"]
    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh3_id}", headers=admin_headers)
    inv3 = res_inv.json()["items"][0]

    # Hóa đơn có fee_amount = 0 và status = PAID (không có khoản phải nộp)
    assert inv3["fee_amount"] == 0
    assert inv3["total_due"] == 0
    assert inv3["status"] == "PAID"

    res_detail = client.get(f"/api/v1/invoices/{inv3['id']}", headers=admin_headers)
    assert len(res_detail.json()["items"]) == 0


def test_ac37_1_inactive_vehicle_not_counted(client, admin_headers, db_session, setup_parking_environment):
    """Phương tiện đã hủy đăng ký (status = INACTIVE) không được tính vào kỳ thu."""
    hh1_id = setup_parking_environment["hh1_id"]

    # Hủy toàn bộ xe máy của Hộ 1, chỉ để lại 1 xe máy INACTIVE
    db_session.execute(
        delete(Vehicle).where(Vehicle.household_id == hh1_id, Vehicle.vehicle_type == "CAR")
    )
    db_session.query(Vehicle).filter(
        Vehicle.household_id == hh1_id, Vehicle.vehicle_type == "MOTORBIKE"
    ).update({"status": "INACTIVE"})
    db_session.commit()

    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11 Xe hủy"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh1_id}", headers=admin_headers)
    inv = res_inv.json()["items"][0]
    assert inv["total_due"] == 0

    res_detail = client.get(f"/api/v1/invoices/{inv['id']}", headers=admin_headers)
    assert len(res_detail.json()["items"]) == 0


# ==============================================================================
# PHẦN 4: MIỄN GIẢM PHÍ GỬI XE (US-15, US-16 TÍCH HỢP US-37)
# ==============================================================================

def test_parking_fee_with_percent_exemption(client, admin_headers, db_session, setup_parking_environment):
    """Hộ được giảm 50% phí gửi xe máy theo chính sách miễn giảm."""
    hh1_id = setup_parking_environment["hh1_id"]
    ft_moto_id = setup_parking_environment["ft_moto_id"]

    # Cấp chính sách giảm 50% phí xe máy
    exemption = FeeExemption(
        household_id=hh1_id,
        fee_type_id=ft_moto_id,
        discount_type="PERCENT",
        discount_value=Decimal("50.00"),
        reason="Hộ gia đình chính sách",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        status="ACTIVE",
    )
    db_session.add(exemption)
    db_session.commit()

    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11 Miễn giảm 50%"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh1_id}", headers=admin_headers)
    inv = res_inv.json()["items"][0]

    # Gross: 2 xe máy (140k) + 1 ô tô (1.200k) = 1.340.000 đ
    # Discount: 50% xe máy = 70.000 đ
    # Net total_due = 1.340.000 - 70.000 = 1.270.000 đ
    assert inv["fee_amount"] == 1340000
    assert inv["discount_amount"] == 70000
    assert inv["total_due"] == 1270000

    res_detail = client.get(f"/api/v1/invoices/{inv['id']}", headers=admin_headers)
    moto_item = next(it for it in res_detail.json()["items"] if it["fee_type_id"] == ft_moto_id)
    assert moto_item["gross_amount"] == 140000
    assert moto_item["discount_amount"] == 70000
    assert moto_item["net_amount"] == 70000


def test_parking_fee_with_100_percent_full_exemption(client, admin_headers, db_session, setup_parking_environment):
    """Hộ được miễn 100% phí gửi xe máy -> net_amount = 0."""
    hh1_id = setup_parking_environment["hh1_id"]
    ft_moto_id = setup_parking_environment["ft_moto_id"]

    exemption = FeeExemption(
        household_id=hh1_id,
        fee_type_id=ft_moto_id,
        discount_type="PERCENT",
        discount_value=Decimal("100.00"),
        reason="Miễn 100% phí xe máy",
        valid_from=date(2026, 1, 1),
        status="ACTIVE",
    )
    db_session.add(exemption)
    db_session.commit()

    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11 Miễn 100%"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh1_id}", headers=admin_headers)
    inv_id = res_inv.json()["items"][0]["id"]

    res_detail = client.get(f"/api/v1/invoices/{inv_id}", headers=admin_headers)
    moto_item = next(it for it in res_detail.json()["items"] if it["fee_type_id"] == ft_moto_id)
    assert moto_item["gross_amount"] == 140000
    assert moto_item["discount_amount"] == 140000
    assert moto_item["net_amount"] == 0


def test_parking_fee_with_amount_exemption(client, admin_headers, db_session, setup_parking_environment):
    """Hộ được giảm 200.000 đ cố định trên phí ô tô."""
    hh1_id = setup_parking_environment["hh1_id"]
    ft_car_id = setup_parking_environment["ft_car_id"]

    exemption = FeeExemption(
        household_id=hh1_id,
        fee_type_id=ft_car_id,
        discount_type="AMOUNT",
        discount_value=Decimal("200000.00"),
        reason="Hỗ trợ gửi ô tô",
        valid_from=date(2026, 1, 1),
        status="ACTIVE",
    )
    db_session.add(exemption)
    db_session.commit()

    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11 Giảm cố định 200k"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh1_id}", headers=admin_headers)
    inv_id = res_inv.json()["items"][0]["id"]

    res_detail = client.get(f"/api/v1/invoices/{inv_id}", headers=admin_headers)
    car_item = next(it for it in res_detail.json()["items"] if it["fee_type_id"] == ft_car_id)
    assert car_item["gross_amount"] == 1200000
    assert car_item["discount_amount"] == 200000
    assert car_item["net_amount"] == 1000000


def test_expired_or_revoked_exemption_not_applied(client, admin_headers, db_session, setup_parking_environment):
    """Chính sách miễn giảm đã hết hạn hoặc bị thu hồi (REVOKED) không được áp dụng."""
    hh1_id = setup_parking_environment["hh1_id"]
    ft_moto_id = setup_parking_environment["ft_moto_id"]

    # Đã hết hạn từ 31/10/2026
    ex_expired = FeeExemption(
        household_id=hh1_id,
        fee_type_id=ft_moto_id,
        discount_type="PERCENT",
        discount_value=Decimal("50.00"),
        reason="Hết hạn",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 10, 31),
        status="ACTIVE",
    )
    # Bị thu hồi
    ex_revoked = FeeExemption(
        household_id=hh1_id,
        fee_type_id=setup_parking_environment["ft_car_id"],
        discount_type="AMOUNT",
        discount_value=Decimal("500000.00"),
        reason="Đã thu hồi",
        valid_from=date(2026, 1, 1),
        status="REVOKED",
    )
    db_session.add_all([ex_expired, ex_revoked])
    db_session.commit()

    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11 Miễn giảm vô hiệu"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh1_id}", headers=admin_headers)
    inv = res_inv.json()["items"][0]
    # Không được giảm đồng nào
    assert inv["discount_amount"] == 0
    assert inv["total_due"] == 1340000


# ==============================================================================
# PHẦN 5: ĐƠN GIÁ THEO LỊCH SỬ THỜI GIAN (US-14 TÍCH HỢP US-37)
# ==============================================================================

def test_parking_fee_applies_correct_historical_rate(client, admin_headers, db_session, setup_parking_environment):
    """
    US-14: Lịch sử đơn giá:
    - Đơn giá xe máy cũ: 60.000 đ (hiệu lực 01/01/2026 -> 30/06/2026)
    - Đơn giá xe máy mới: 70.000 đ (hiệu lực từ 01/07/2026)
    Kỳ 05/2026 phải áp giá 60.000 đ.
    Kỳ 11/2026 phải áp giá 70.000 đ.
    """
    ft_moto_id = setup_parking_environment["ft_moto_id"]

    # Cập nhật đơn giá cũ
    db_session.query(FeeRate).filter(FeeRate.fee_type_id == ft_moto_id).delete()
    rate_old = FeeRate(
        fee_type_id=ft_moto_id,
        unit_price=Decimal("60000.00"),
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 6, 30),
    )
    rate_new = FeeRate(
        fee_type_id=ft_moto_id,
        unit_price=Decimal("70000.00"),
        effective_from=date(2026, 7, 1),
        effective_to=None,
    )
    db_session.add_all([rate_old, rate_new])
    db_session.commit()

    # Kỳ tháng 5/2026 (trước 01/07/2026) -> áp giá cũ 60.000 đ
    res1 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-05-01", "name": "Kỳ 05/2026"},
        headers=admin_headers,
    )
    p1_id = res1.json()["id"]
    client.post(f"/api/v1/billing-periods/{p1_id}/generate", headers=admin_headers)

    res_inv1 = client.get(
        f"/api/v1/invoices?billing_period_id={p1_id}&household_id={setup_parking_environment['hh1_id']}",
        headers=admin_headers,
    )
    inv1_id = res_inv1.json()["items"][0]["id"]
    res_det1 = client.get(f"/api/v1/invoices/{inv1_id}", headers=admin_headers)
    moto1 = next(it for it in res_det1.json()["items"] if it["fee_type_id"] == ft_moto_id)
    assert moto1["unit_price"] == 60000
    assert moto1["net_amount"] == 120000  # 2 xe * 60.000 = 120.000 đ

    # Kỳ tháng 11/2026 (sau 01/07/2026) -> áp giá mới 70.000 đ
    res2 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ 11/2026"},
        headers=admin_headers,
    )
    p2_id = res2.json()["id"]
    client.post(f"/api/v1/billing-periods/{p2_id}/generate", headers=admin_headers)

    res_inv2 = client.get(
        f"/api/v1/invoices?billing_period_id={p2_id}&household_id={setup_parking_environment['hh1_id']}",
        headers=admin_headers,
    )
    inv2_id = res_inv2.json()["items"][0]["id"]
    res_det2 = client.get(f"/api/v1/invoices/{inv2_id}", headers=admin_headers)
    moto2 = next(it for it in res_det2.json()["items"] if it["fee_type_id"] == ft_moto_id)
    assert moto2["unit_price"] == 70000
    assert moto2["net_amount"] == 140000  # 2 xe * 70.000 = 140.000 đ


# ==============================================================================
# PHẦN 6: TRẠNG THÁI & RÀNG BUỘC ĐỘNG CƠ TÍNH PHÍ (GENERATE & CLOSE)
# ==============================================================================

def test_generate_non_existent_period_returns_404(client, admin_headers):
    """Tính phí kỳ không tồn tại -> 404 NOT_FOUND."""
    res = client.post("/api/v1/billing-periods/999999/generate", headers=admin_headers)
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_cannot_regenerate_when_period_closed(client, admin_headers, setup_parking_environment):
    """Kỳ thu đã chốt (CLOSED) -> Không thể tính lại (409 PERIOD_CLOSED)."""
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Chốt"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]

    # Chạy tính phí rồi chốt kỳ
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)
    res_close = client.post(f"/api/v1/billing-periods/{period_id}/close", headers=admin_headers)
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"

    # Chạy lại tính phí -> bị chặn
    res_re = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)
    assert res_re.status_code == 409
    assert res_re.json()["code"] == "PERIOD_CLOSED"


def test_cannot_regenerate_when_period_has_payments(client, admin_headers, db_session, setup_parking_environment):
    """Kỳ thu đã có cư dân thanh toán -> Chặn chạy lại tính phí (409 PERIOD_HAS_PAYMENTS)."""
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Đã Đóng Tiền"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    # Giả lập 1 hóa đơn đã được thanh toán một phần
    inv = db_session.scalar(select(Invoice).where(Invoice.billing_period_id == period_id))
    inv.paid_amount = Decimal("50000.00")
    inv.status = "PARTIAL"
    db_session.commit()

    # Thử tính lại -> Bị chặn 409
    res_re = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)
    assert res_re.status_code == 409
    assert res_re.json()["code"] == "PERIOD_HAS_PAYMENTS"


def test_idempotent_regeneration_when_no_payments(client, admin_headers, setup_parking_environment):
    """Kỳ thu chưa có payment -> Có thể chạy tính phí lại nhiều lần an toàn (idempotent)."""
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Chạy Lại"},
        headers=admin_headers,
    )
    period_id = res.json()["id"]

    # Chạy lần 1
    res1 = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)
    assert res1.status_code == 200
    assert res1.json()["invoices_created"] == 3

    # Chạy lần 2 (Re-run)
    res2 = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)
    assert res2.status_code == 200
    assert res2.json()["invoices_created"] == 3

    # Tổng số hóa đơn trong kỳ vẫn là 3, không bị nhân đôi
    res_inv = client.get(f"/api/v1/invoices?billing_period_id={period_id}", headers=admin_headers)
    assert res_inv.json()["total"] == 3


def test_close_billing_period_validations(client, admin_headers):
    """Kiểm tra các ràng buộc khi chốt kỳ thu (closeBillingPeriod)."""
    # 1. Chốt kỳ không tồn tại -> 404
    res = client.post("/api/v1/billing-periods/999999/close", headers=admin_headers)
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"

    # 2. Chốt kỳ đang ở DRAFT (chưa chạy tính phí) -> 409 PERIOD_NOT_GENERATED
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Chưa Tính Phí"},
        headers=admin_headers,
    )
    p_id = res_p.json()["id"]
    res_close_fail = client.post(f"/api/v1/billing-periods/{p_id}/close", headers=admin_headers)
    assert res_close_fail.status_code == 409
    assert res_close_fail.json()["code"] == "PERIOD_NOT_GENERATED"

    # 3. Chạy tính phí rồi chốt thành công
    client.post(f"/api/v1/billing-periods/{p_id}/generate", headers=admin_headers)
    res_close_ok = client.post(f"/api/v1/billing-periods/{p_id}/close", headers=admin_headers)
    assert res_close_ok.status_code == 200
    assert res_close_ok.json()["status"] == "CLOSED"

    # 4. Chốt lại kỳ đã chốt -> 409 PERIOD_CLOSED
    res_close_again = client.post(f"/api/v1/billing-periods/{p_id}/close", headers=admin_headers)
    assert res_close_again.status_code == 409
    assert res_close_again.json()["code"] == "PERIOD_CLOSED"


# ==============================================================================
# PHẦN 7: DANH SÁCH & CHI TIẾT HÓA ĐƠN (GET /invoices & GET /invoices/{id})
# ==============================================================================

def test_list_invoices_filters_and_pagination(client, admin_headers, setup_parking_environment):
    """Tra cứu danh sách hóa đơn với phân trang và bộ lọc theo kỳ, theo hộ, theo trạng thái."""
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Lọc Hóa Đơn"},
        headers=admin_headers,
    )
    period_id = res_p.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    # 1. Lọc theo kỳ thu
    res = client.get(f"/api/v1/invoices?billing_period_id={period_id}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 3

    # 2. Lọc theo hộ gia đình
    hh1_id = setup_parking_environment["hh1_id"]
    res_hh = client.get(f"/api/v1/invoices?household_id={hh1_id}", headers=admin_headers)
    assert res_hh.status_code == 200
    assert res_hh.json()["total"] == 1
    assert res_hh.json()["items"][0]["household_id"] == hh1_id

    # 3. Lọc theo trạng thái UNPAID
    res_unpaid = client.get(f"/api/v1/invoices?billing_period_id={period_id}&status=UNPAID", headers=admin_headers)
    assert res_unpaid.status_code == 200
    # Hộ 1 và Hộ 2 có xe -> UNPAID, Hộ 3 không có xe -> PAID
    assert res_unpaid.json()["total"] == 2

    # 4. Lọc theo trạng thái PAID
    res_paid = client.get(f"/api/v1/invoices?billing_period_id={period_id}&status=PAID", headers=admin_headers)
    assert res_paid.status_code == 200
    assert res_paid.json()["total"] == 1


def test_get_invoice_detail_not_found(client, admin_headers):
    """Tra cứu chi tiết hóa đơn không tồn tại -> 404 NOT_FOUND."""
    res = client.get("/api/v1/invoices/999999", headers=admin_headers)
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_generate_invoices_audit_log_recorded(client, admin_headers, db_session, setup_parking_environment):
    """Chạy động cơ tính phí phải ghi nhận AuditLog đầy đủ chi tiết."""
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Audit Generate"},
        headers=admin_headers,
    )
    period_id = res_p.json()["id"]

    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=admin_headers)

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "GENERATE_INVOICES",
            AuditLog.entity_id == str(period_id),
        )
    )
    assert audit is not None
    assert audit.new_value["households_processed"] == 3
    assert audit.new_value["invoices_created"] == 3
    assert audit.new_value["total_fee_amount"] == 1440000  # Hộ 1 (1.340k) + Hộ 2 (100k) = 1.440.000 đ
    assert "Chạy động cơ tính phí" in audit.reason



# ==============================================================================
# PHẦN 8: BỔ SUNG CÁC TEST CASES NÂNG CAO & BIÊN ĐỘ (EDGE CASES & ROBUSTNESS)
# ==============================================================================

def test_list_billing_periods_pagination_and_status_filter(client, admin_headers):
    """Phân trang và lọc trạng thái kỳ thu (DRAFT, OPEN, CLOSED)."""
    # Tạo 3 kỳ thu với 3 tháng khác nhau
    client.post("/api/v1/billing-periods", json={"period_month": "2026-08-01", "name": "Kỳ 08"}, headers=admin_headers)
    client.post("/api/v1/billing-periods", json={"period_month": "2026-09-01", "name": "Kỳ 09"}, headers=admin_headers)
    res3 = client.post("/api/v1/billing-periods", json={"period_month": "2026-10-01", "name": "Kỳ 10"}, headers=admin_headers)
    p3_id = res3.json()["id"]

    # Chạy generate kỳ 10 để sang OPEN
    client.post(f"/api/v1/billing-periods/{p3_id}/generate", headers=admin_headers)

    # 1. Phân trang: page=1, page_size=2
    res_page1 = client.get("/api/v1/billing-periods?page=1&page_size=2", headers=admin_headers)
    assert res_page1.status_code == 200
    data1 = res_page1.json()
    assert data1["total"] == 3
    assert len(data1["items"]) == 2
    assert data1["total_pages"] == 2

    # 2. Lọc status=DRAFT -> Kỳ 08, Kỳ 09
    res_draft = client.get("/api/v1/billing-periods?status=DRAFT", headers=admin_headers)
    assert res_draft.status_code == 200
    assert res_draft.json()["total"] == 2

    # 3. Lọc status=OPEN -> Kỳ 10
    res_open = client.get("/api/v1/billing-periods?status=OPEN", headers=admin_headers)
    assert res_open.status_code == 200
    assert res_open.json()["total"] == 1
    assert res_open.json()["items"][0]["name"] == "Kỳ 10"


def test_get_billing_period_by_id(client, admin_headers):
    """Tra cứu chi tiết một kỳ thu theo ID."""
    res_create = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Chi Tiết", "due_date": "2026-11-25"},
        headers=admin_headers,
    )
    p_id = res_create.json()["id"]

    res_get = client.get(f"/api/v1/billing-periods/{p_id}", headers=admin_headers)
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["id"] == p_id
    assert data["name"] == "Kỳ Chi Tiết"
    assert data["period_month"] == "2026-11-01"
    assert data["due_date"] == "2026-11-25"
    assert data["status"] == "DRAFT"


def test_create_period_empty_or_whitespace_name_rejected(client, admin_headers):
    """Tên kỳ thu để trống hoặc chỉ có khoảng trắng -> 400 VALIDATION_ERROR."""
    res1 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": ""},
        headers=admin_headers,
    )
    assert res1.status_code == 400
    assert res1.json()["code"] == "VALIDATION_ERROR"

    res2 = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "    "},
        headers=admin_headers,
    )
    assert res2.status_code == 400
    assert res2.json()["code"] == "VALIDATION_ERROR"


def test_parking_fee_vehicle_without_fee_rate_gracefully_skipped(client, admin_headers, db_session, setup_parking_environment):
    """Khoản thu gửi xe chưa được cấu hình đơn giá (FeeRate) -> Không bị crash hệ thống, bỏ qua khoản đó."""
    # Tạo loại xe mới nhưng cố tình không thêm FeeRate
    ft_truck = FeeType(
        code="FEE_US37_TRUCK",
        name="Phí xe tải",
        fee_group="PARKING",
        calc_method="PER_VEHICLE",
        unit_label="xe",
        vehicle_type="CAR",  # reuse car type
        status="ACTIVE",
    )
    # Xóa toàn bộ fee rates của CAR
    db_session.query(FeeRate).filter(FeeRate.fee_type_id == setup_parking_environment["ft_car_id"]).delete()
    db_session.commit()

    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Thiếu Đơn Giá"},
        headers=admin_headers,
    )
    p_id = res_p.json()["id"]

    # Chạy generate không được văng 500
    res_gen = client.post(f"/api/v1/billing-periods/{p_id}/generate", headers=admin_headers)
    assert res_gen.status_code == 200

    # Ô tô không có rate nên chỉ tính 2 xe máy = 140.000 đ
    hh1_id = setup_parking_environment["hh1_id"]
    res_inv = client.get(f"/api/v1/invoices?billing_period_id={p_id}&household_id={hh1_id}", headers=admin_headers)
    inv = res_inv.json()["items"][0]
    assert inv["total_due"] == 140000


def test_regenerate_after_registering_new_vehicle(client, admin_headers, db_session, setup_parking_environment):
    """
    Khi chưa có payment:
    - Lần 1: Hộ 1 có 2 xe máy + 1 ô tô = 1.340.000 đ
    - Đăng ký thêm 1 xe máy mới
    - Chạy lại generate -> hóa đơn được cập nhật thành 3 xe máy + 1 ô tô = 1.410.000 đ
    """
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ Thêm Xe Mới"},
        headers=admin_headers,
    )
    p_id = res_p.json()["id"]

    # Chạy lần 1
    client.post(f"/api/v1/billing-periods/{p_id}/generate", headers=admin_headers)
    hh1_id = setup_parking_environment["hh1_id"]
    res1 = client.get(f"/api/v1/invoices?billing_period_id={p_id}&household_id={hh1_id}", headers=admin_headers)
    assert res1.json()["items"][0]["total_due"] == 1340000

    # Đăng ký thêm 1 xe máy cho Hộ 1
    v_new = Vehicle(household_id=hh1_id, plate_number="29M1-99999-NEW", vehicle_type="MOTORBIKE", status="ACTIVE")
    db_session.add(v_new)
    db_session.commit()

    # Chạy lại tính phí
    client.post(f"/api/v1/billing-periods/{p_id}/generate", headers=admin_headers)

    res2 = client.get(f"/api/v1/invoices?billing_period_id={p_id}&household_id={hh1_id}", headers=admin_headers)
    inv2 = res2.json()["items"][0]
    # 3 xe máy (210.000) + 1 ô tô (1.200.000) = 1.410.000 đ
    assert inv2["total_due"] == 1410000

    res_det = client.get(f"/api/v1/invoices/{inv2['id']}", headers=admin_headers)
    moto_it = next(it for it in res_det.json()["items"] if it["fee_type_id"] == setup_parking_environment["ft_moto_id"])
    assert moto_it["quantity"] == 3.0
    assert moto_it["gross_amount"] == 210000


def test_rbac_invoices_endpoints_forbidden_for_resident(client, resident_headers, admin_headers, setup_parking_environment):
    """Cư dân không được quyền gọi API quản trị hóa đơn GET /invoices và GET /invoices/{id} (403 FORBIDDEN)."""
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ RBAC Hóa Đơn"},
        headers=admin_headers,
    )
    p_id = res_p.json()["id"]
    client.post(f"/api/v1/billing-periods/{p_id}/generate", headers=admin_headers)

    res_list = client.get("/api/v1/invoices", headers=resident_headers)
    assert res_list.status_code == 403
    assert res_list.json()["code"] == "FORBIDDEN"

    res_detail = client.get("/api/v1/invoices/1", headers=resident_headers)
    assert res_detail.status_code == 403
    assert res_detail.json()["code"] == "FORBIDDEN"
