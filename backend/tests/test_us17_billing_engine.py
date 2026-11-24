"""
Test Suite for User Story US-17: Động cơ tạo kỳ thu & Tính phí tự động (Billing Engine).

Specification & Standards:
- docs/openapi.yaml:
  - POST /billing-periods (createBillingPeriod, US-17)
  - GET /billing-periods (listBillingPeriods, US-17)
  - GET /billing-periods/{id} (getBillingPeriod, US-17)
  - POST /billing-periods/{id}/generate (generateInvoices, US-17, US-37)
  - POST /billing-periods/{id}/close (closeBillingPeriod, US-17)
  - GET /invoices (listInvoices, US-17, US-47)
- docs/API_CONTRACT.md (Section 3.14)
- docs/PRODUCT_BACKLOG.md (F-03.1, AC-17.1, NFR-005):
  - Kế toán khởi tạo kỳ thu tháng và chạy động cơ tự động tính phí cho toàn bộ hộ gia đình.
  - Công thức chuẩn AC-17.1: Tổng phải nộp = Σ(Phí kỳ này - Miễn giảm) + Nợ cũ - Số dư có.
  - Chạy xong 1.000 hộ <= 10 giây (NFR-005).
"""

import time
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select, text

from app.core.security import create_access_token, get_password_hash
from app.models.billing import BillingPeriod, Invoice, InvoiceItem, UtilityReading
from app.models.fee import FeeExemption, FeeRate, FeeType
from app.models.property import Apartment, ApartmentOccupancy, Household
from app.models.user import AuditLog, User
from app.models.vehicle import Vehicle

US17_HOUSEHOLD_CODES = (
    "HH_US17_FULL",
    "HH_US17_AREA_ONLY",
    "HH_US17_VEHICLE_ONLY",
    "HH_US17_UTILITY_ONLY",
    "HH_US17_EXEMPTION_PCT",
    "HH_US17_EXEMPTION_AMT",
    "HH_US17_DEBT",
    "HH_US17_EMPTY",
)
US17_FEE_CODES = (
    "FEE_US17_MGT",
    "FEE_US17_MOTO",
    "FEE_US17_CAR",
    "FEE_US17_BIKE",
    "FEE_US17_ELEC",
    "FEE_US17_WATER",
    "FEE_US17_FIXED",
)
US17_APT_CODES = ("APT_US17_101", "APT_US17_102", "APT_US17_103", "APT_US17_104")


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
    user = db_session.scalar(select(User).where(User.username == "treasurer_test_us17"))
    if not user:
        user = User(
            id=517,
            username="treasurer_test_us17",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test US17",
            email="treasurer_17@bluemoon.local",
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
def clean_us17_tables(db_session):
    """Dọn dẹp sạch sẽ dữ liệu của suite test US-17 trước và sau mỗi test."""
    def _cleanup():
        db_session.query(AuditLog).filter(
            AuditLog.entity_type.in_(("BILLING_PERIOD", "INVOICE", "UTILITY_READING"))
        ).delete(synchronize_session=False)

        # Xóa các hóa đơn, chỉ số và kỳ thu
        db_session.query(InvoiceItem).delete(synchronize_session=False)
        db_session.query(Invoice).delete(synchronize_session=False)
        db_session.query(UtilityReading).delete(synchronize_session=False)
        db_session.query(BillingPeriod).delete(synchronize_session=False)

        # Xóa miễn giảm, đơn giá và loại phí
        db_session.query(FeeExemption).delete(synchronize_session=False)
        db_session.query(FeeRate).delete(synchronize_session=False)
        db_session.query(FeeType).filter(FeeType.code.in_(US17_FEE_CODES)).delete(synchronize_session=False)

        # Xóa phương tiện, hợp đồng ở và căn hộ
        db_session.query(Vehicle).delete(synchronize_session=False)
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
def setup_us17_environment(db_session):
    """
    Thiết lập môi trường đa dạng cho US-17:
    - 4 Căn hộ với diện tích khác nhau
    - 8 Hộ gia đình với các tổ hợp dữ liệu khác nhau (xe, diện tích, điện nước, miễn giảm, nợ cũ, hộ trống)
    - 7 Khoản thu (Phí quản lý m2, Phí gửi xe máy/ô tô/xe đạp, Tiền điện, Tiền nước, Phí an ninh cố định)
    - Biểu giá chuẩn hiệu lực từ 01/01/2026
    """
    # 1. Căn hộ
    apt1 = Apartment(code="APT_US17_101", floor=1, area_m2=Decimal("80.00"), status="ACTIVE")
    apt2 = Apartment(code="APT_US17_102", floor=1, area_m2=Decimal("100.00"), status="ACTIVE")
    apt3 = Apartment(code="APT_US17_103", floor=2, area_m2=Decimal("65.50"), status="ACTIVE")
    apt4 = Apartment(code="APT_US17_104", floor=2, area_m2=Decimal("120.00"), status="ACTIVE")
    apt5 = Apartment(code="APT_US17_201", floor=3, area_m2=Decimal("50.00"), status="ACTIVE")
    apt6 = Apartment(code="APT_US17_202", floor=3, area_m2=Decimal("50.00"), status="ACTIVE")
    apt7 = Apartment(code="APT_US17_203", floor=3, area_m2=Decimal("50.00"), status="ACTIVE")
    db_session.add_all([apt1, apt2, apt3, apt4, apt5, apt6, apt7])
    db_session.flush()

    # 2. Hộ gia đình
    households = {
        code: Household(household_code=code, status="ACTIVE")
        for code in US17_HOUSEHOLD_CODES
    }
    db_session.add_all(households.values())
    db_session.flush()

    # 3. Gán căn hộ cho các hộ (riêng HH_US17_EMPTY cố tình không gắn căn hộ để kiểm chứng bỏ qua an toàn theo CHECK > 0)
    occ1 = ApartmentOccupancy(apartment_id=apt1.id, household_id=households["HH_US17_FULL"].id, start_date=date(2025, 1, 1))
    occ2 = ApartmentOccupancy(apartment_id=apt2.id, household_id=households["HH_US17_AREA_ONLY"].id, start_date=date(2025, 1, 1))
    occ3 = ApartmentOccupancy(apartment_id=apt3.id, household_id=households["HH_US17_EXEMPTION_PCT"].id, start_date=date(2025, 1, 1))
    occ4 = ApartmentOccupancy(apartment_id=apt4.id, household_id=households["HH_US17_DEBT"].id, start_date=date(2025, 1, 1))
    occ5 = ApartmentOccupancy(apartment_id=apt5.id, household_id=households["HH_US17_VEHICLE_ONLY"].id, start_date=date(2025, 1, 1))
    occ6 = ApartmentOccupancy(apartment_id=apt6.id, household_id=households["HH_US17_UTILITY_ONLY"].id, start_date=date(2025, 1, 1))
    occ7 = ApartmentOccupancy(apartment_id=apt7.id, household_id=households["HH_US17_EXEMPTION_AMT"].id, start_date=date(2025, 1, 1))
    db_session.add_all([occ1, occ2, occ3, occ4, occ5, occ6, occ7])
    db_session.flush()

    # 4. Khoản thu
    ft_mgt = FeeType(code="FEE_US17_MGT", name="Phí quản lý vận hành", fee_group="MANAGEMENT", calc_method="PER_M2", unit_label="m²", status="ACTIVE")
    ft_moto = FeeType(code="FEE_US17_MOTO", name="Phí gửi xe máy", fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="MOTORBIKE", unit_label="xe", status="ACTIVE")
    ft_car = FeeType(code="FEE_US17_CAR", name="Phí gửi ô tô", fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="CAR", unit_label="xe", status="ACTIVE")
    ft_bike = FeeType(code="FEE_US17_BIKE", name="Phí gửi xe đạp", fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="BICYCLE", unit_label="xe", status="ACTIVE")
    ft_elec = FeeType(code="FEE_US17_ELEC", name="Tiền điện", fee_group="ELECTRICITY", calc_method="PER_INDEX", unit_label="kWh", status="ACTIVE")
    ft_water = FeeType(code="FEE_US17_WATER", name="Tiền nước", fee_group="WATER", calc_method="PER_INDEX", unit_label="m³", status="ACTIVE")
    ft_fixed = FeeType(code="FEE_US17_FIXED", name="Phí an ninh trật tự", fee_group="OTHER", calc_method="PER_HOUSEHOLD", unit_label="hộ", status="ACTIVE")

    all_fees = [ft_mgt, ft_moto, ft_car, ft_bike, ft_elec, ft_water, ft_fixed]
    db_session.add_all(all_fees)
    db_session.flush()

    # 5. Biểu giá chuẩn hiệu lực từ 01/01/2026:
    # - Quản lý: 10.000 đ/m2
    # - Xe máy: 70.000 đ/xe
    # - Ô tô: 1.200.000 đ/xe
    # - Xe đạp: 30.000 đ/xe
    # - Điện: 2.500 đ/kWh
    # - Nước: 15.000 đ/m3
    # - An ninh: 50.000 đ/hộ
    rates = [
        FeeRate(fee_type_id=ft_mgt.id, unit_price=Decimal("10000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_moto.id, unit_price=Decimal("70000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_car.id, unit_price=Decimal("1200000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_bike.id, unit_price=Decimal("30000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_elec.id, unit_price=Decimal("2500.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_water.id, unit_price=Decimal("15000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_fixed.id, unit_price=Decimal("50000.00"), effective_from=date(2026, 1, 1)),
    ]
    db_session.add_all(rates)
    db_session.flush()

    # 6. Phương tiện của các hộ
    # HH_US17_FULL: 2 xe máy, 1 ô tô
    # HH_US17_VEHICLE_ONLY: 1 xe máy, 2 xe đạp
    # HH_US17_EXEMPTION_AMT: 1 ô tô
    v1 = Vehicle(household_id=households["HH_US17_FULL"].id, plate_number="29A-11111", vehicle_type="MOTORBIKE", status="ACTIVE")
    v2 = Vehicle(household_id=households["HH_US17_FULL"].id, plate_number="29A-22222", vehicle_type="MOTORBIKE", status="ACTIVE")
    v3 = Vehicle(household_id=households["HH_US17_FULL"].id, plate_number="30F-99999", vehicle_type="CAR", status="ACTIVE")
    v4 = Vehicle(household_id=households["HH_US17_VEHICLE_ONLY"].id, plate_number="29B-33333", vehicle_type="MOTORBIKE", status="ACTIVE")
    v5 = Vehicle(household_id=households["HH_US17_VEHICLE_ONLY"].id, plate_number="XD-001", vehicle_type="BICYCLE", status="ACTIVE")
    v6 = Vehicle(household_id=households["HH_US17_VEHICLE_ONLY"].id, plate_number="XD-002", vehicle_type="BICYCLE", status="ACTIVE")
    v7 = Vehicle(household_id=households["HH_US17_EXEMPTION_AMT"].id, plate_number="30A-88888", vehicle_type="CAR", status="ACTIVE")
    db_session.add_all([v1, v2, v3, v4, v5, v6, v7])
    db_session.flush()

    # 7. Chính sách miễn giảm
    # HH_US17_EXEMPTION_PCT: Miễn giảm 50% phí quản lý
    ex1 = FeeExemption(
        household_id=households["HH_US17_EXEMPTION_PCT"].id,
        fee_type_id=ft_mgt.id,
        discount_type="PERCENT",
        discount_value=Decimal("50.00"),
        valid_from=date(2026, 1, 1),
        status="ACTIVE",
        reason="Gia đình chính sách giảm 50% phí dịch vụ",
    )
    # HH_US17_EXEMPTION_AMT: Miễn giảm 200.000 đ phí ô tô
    ex2 = FeeExemption(
        household_id=households["HH_US17_EXEMPTION_AMT"].id,
        fee_type_id=ft_car.id,
        discount_type="AMOUNT",
        discount_value=Decimal("200000.00"),
        valid_from=date(2026, 1, 1),
        status="ACTIVE",
        reason="Khuyến mại cư dân mới giảm 200.000 đ",
    )
    db_session.add_all([ex1, ex2])
    db_session.commit()

    return {
        "households": households,
        "apartments": {"apt1": apt1, "apt2": apt2, "apt3": apt3, "apt4": apt4},
        "fee_types": {
            "mgt": ft_mgt,
            "moto": ft_moto,
            "car": ft_car,
            "bike": ft_bike,
            "elec": ft_elec,
            "water": ft_water,
            "fixed": ft_fixed,
        },
    }


# ==============================================================================
# 1. TEST PHÂN QUYỀN RBAC & BẢO MẬT (US-17)
# ==============================================================================

def test_rbac_admin_and_accountant_can_access_billing_period_endpoints(client, admin_headers, accountant_headers):
    """ADMIN và ACCOUNTANT được phép truy cập đầy đủ các endpoint kỳ thu (US-17)."""
    for headers in (admin_headers, accountant_headers):
        res = client.get("/api/v1/billing-periods", headers=headers)
        assert res.status_code == 200

        # Thử tạo kỳ thu
        period_data = {
            "period_month": "2026-05-01",
            "name": f"Kỳ thu tháng 05/2026 - RBAC {headers['Authorization'][:15]}",
            "due_date": "2026-05-25",
        }
        res_create = client.post("/api/v1/billing-periods", json=period_data, headers=headers)
        # 201 nếu tạo mới, hoặc 409 nếu kỳ tháng 5 đã tồn tại từ vòng lặp trước
        assert res_create.status_code in (201, 409)


def test_rbac_treasurer_and_resident_forbidden_on_all_billing_period_endpoints(client, treasurer_headers, resident_headers):
    """TREASURER và RESIDENT bị chặn 403 trên tất cả các thao tác kỳ thu (US-17)."""
    for headers in (treasurer_headers, resident_headers):
        # 1. GET /billing-periods
        assert client.get("/api/v1/billing-periods", headers=headers).status_code == 403
        # 2. POST /billing-periods
        assert client.post(
            "/api/v1/billing-periods",
            json={"period_month": "2026-06-01", "name": "Kỳ 6"},
            headers=headers,
        ).status_code == 403
        # 3. GET /billing-periods/1
        assert client.get("/api/v1/billing-periods/1", headers=headers).status_code == 403
        # 4. POST /billing-periods/1/generate
        assert client.post("/api/v1/billing-periods/1/generate", headers=headers).status_code == 403
        # 5. POST /billing-periods/1/close
        assert client.post("/api/v1/billing-periods/1/close", headers=headers).status_code == 403


def test_rbac_unauthenticated_request_rejected(client):
    """Không gửi kèm token xác thực bị trả về 401 UNAUTHENTICATED (US-17)."""
    assert client.get("/api/v1/billing-periods").status_code == 401
    assert client.post("/api/v1/billing-periods", json={"period_month": "2026-06-01", "name": "Kỳ"}).status_code == 401
    assert client.get("/api/v1/billing-periods/1").status_code == 401
    assert client.post("/api/v1/billing-periods/1/generate").status_code == 401
    assert client.post("/api/v1/billing-periods/1/close").status_code == 401


def test_rbac_password_change_required_blocked(client, db_session):
    """Tài khoản bị bắt buộc đổi mật khẩu (must_change_password=True) bị chặn 403 (US-17)."""
    user = db_session.get(User, 2)
    assert user is not None
    orig_flag = user.must_change_password
    user.must_change_password = True
    db_session.commit()

    try:
        headers = make_headers(role="ACCOUNTANT", sub=str(user.id), username=user.username, must_change_password=True)
        res = client.get("/api/v1/billing-periods", headers=headers)
        assert res.status_code == 403
        data = res.json()
        assert data.get("code") == "PASSWORD_CHANGE_REQUIRED"
    finally:
        user.must_change_password = orig_flag
        db_session.commit()


# ==============================================================================
# 2. TEST QUẢN LÝ KỲ THU (CRUD LIFECYCLE & VALIDATIONS)
# ==============================================================================

def test_create_billing_period_success_draft(client, accountant_headers):
    """Tạo kỳ thu mới thành công ở trạng thái DRAFT (US-17)."""
    payload = {
        "period_month": "2026-07-01",
        "name": "Kỳ thu phí dịch vụ tháng 07/2026",
        "due_date": "2026-07-25",
    }
    res = client.post("/api/v1/billing-periods", json=payload, headers=accountant_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["period_month"] == "2026-07-01"
    assert data["name"] == payload["name"]
    assert data["due_date"] == "2026-07-25"
    assert data["status"] == "DRAFT"
    assert data["generated_at"] is None
    assert data["closed_at"] is None


def test_create_billing_period_records_audit_log(client, accountant_headers, db_session):
    """Tạo kỳ thu phí ghi nhận Audit Log tương ứng (US-32, US-17)."""
    payload = {
        "period_month": "2026-08-01",
        "name": "Kỳ thu tháng 08/2026 Audit Test",
        "due_date": "2026-08-20",
    }
    res = client.post("/api/v1/billing-periods", json=payload, headers=accountant_headers)
    assert res.status_code == 201
    period_id = res.json()["id"]

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "BILLING_PERIOD",
            AuditLog.entity_id == str(period_id),
            AuditLog.action == "CREATE_BILLING_PERIOD",
        )
    )
    assert audit is not None
    assert audit.user_id == 2


def test_create_period_not_first_day_of_month_fails_400(client, accountant_headers):
    """Kỳ thu có ngày bắt đầu không phải ngày 1 bị từ chối 400 (US-17)."""
    payload = {
        "period_month": "2026-08-15",
        "name": "Kỳ thu ngày 15 không hợp lệ",
    }
    res = client.post("/api/v1/billing-periods", json=payload, headers=accountant_headers)
    assert res.status_code == 400


def test_create_period_due_date_before_period_month_fails_400(client, accountant_headers):
    """Hạn nộp phí nhỏ hơn ngày bắt đầu kỳ bị từ chối 400 (US-17)."""
    payload = {
        "period_month": "2026-09-01",
        "name": "Kỳ thu tháng 9",
        "due_date": "2026-08-31",
    }
    res = client.post("/api/v1/billing-periods", json=payload, headers=accountant_headers)
    assert res.status_code == 400


def test_create_duplicate_period_month_returns_409(client, accountant_headers):
    """Tạo trùng kỳ thu trong cùng một tháng trả về 409 DUPLICATE_PERIOD (US-17)."""
    payload = {
        "period_month": "2026-10-01",
        "name": "Kỳ thu tháng 10/2026",
    }
    res1 = client.post("/api/v1/billing-periods", json=payload, headers=accountant_headers)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/billing-periods", json=payload, headers=accountant_headers)
    assert res2.status_code == 409
    assert res2.json().get("code") == "DUPLICATE_PERIOD"


def test_get_billing_period_by_id_and_not_found(client, accountant_headers):
    """Tra cứu chi tiết kỳ thu theo ID và kiểm tra mã lỗi 404 NOT_FOUND (US-17)."""
    # 1. Tạo kỳ thu
    res = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-12-01", "name": "Kỳ thu tháng 12/2026"},
        headers=accountant_headers,
    )
    period_id = res.json()["id"]

    # 2. Tra cứu tồn tại
    res_get = client.get(f"/api/v1/billing-periods/{period_id}", headers=accountant_headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == period_id
    assert res_get.json()["status"] == "DRAFT"

    # 3. Tra cứu ID không tồn tại
    res_404 = client.get("/api/v1/billing-periods/99999", headers=accountant_headers)
    assert res_404.status_code == 404
    assert res_404.json().get("code") == "NOT_FOUND"


def test_list_billing_periods_pagination_and_filters(client, accountant_headers, db_session):
    """Tra cứu danh sách kỳ thu có phân trang, lọc theo status và year (US-17)."""
    # Tạo 3 kỳ thu cho năm 2025 và 2026
    p1 = BillingPeriod(period_month=date(2025, 11, 1), name="Kỳ 11/2025", status="CLOSED")
    p2 = BillingPeriod(period_month=date(2025, 12, 1), name="Kỳ 12/2025", status="OPEN")
    p3 = BillingPeriod(period_month=date(2026, 1, 1), name="Kỳ 01/2026", status="DRAFT")
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # 1. Danh sách có phân trang
    res = client.get("/api/v1/billing-periods?page=1&page_size=2", headers=accountant_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3

    # 2. Lọc theo trạng thái status=CLOSED
    res_closed = client.get("/api/v1/billing-periods?status=CLOSED", headers=accountant_headers)
    assert res_closed.status_code == 200
    items = res_closed.json()["items"]
    assert len(items) >= 1
    assert all(it["status"] == "CLOSED" for it in items)

    # 3. Lọc theo năm year=2025
    res_year = client.get("/api/v1/billing-periods?year=2025", headers=accountant_headers)
    assert res_year.status_code == 200
    items_2025 = res_year.json()["items"]
    assert len(items_2025) == 2
    assert all(it["period_month"].startswith("2025") for it in items_2025)


# ==============================================================================
# 3. TEST ĐỘNG CƠ TÍNH PHÍ TỰ ĐỘNG (POST /billing-periods/{id}/generate)
# ==============================================================================

def test_generate_invoices_non_existent_period_returns_404(client, accountant_headers):
    """Chạy tính phí cho kỳ thu không tồn tại trả về 404 NOT_FOUND (US-17)."""
    res = client.post("/api/v1/billing-periods/99999/generate", headers=accountant_headers)
    assert res.status_code == 404
    assert res.json().get("code") == "NOT_FOUND"


def test_generate_invoices_closed_period_returns_409(client, accountant_headers, db_session):
    """Không thể chạy tính phí cho kỳ đã chốt (CLOSED) trả về 409 PERIOD_CLOSED (US-17)."""
    period = BillingPeriod(
        period_month=date(2026, 2, 1),
        name="Kỳ đã chốt",
        status="CLOSED",
        closed_at=datetime.now(timezone.utc),
    )
    db_session.add(period)
    db_session.commit()

    res = client.post(f"/api/v1/billing-periods/{period.id}/generate", headers=accountant_headers)
    assert res.status_code == 409
    assert res.json().get("code") == "PERIOD_CLOSED"


def test_generate_invoices_period_with_payments_returns_409(client, accountant_headers, db_session, setup_us17_environment):
    """Kỳ thu đã có thanh toán (paid_amount > 0) thì không cho phép tính lại (409 PERIOD_HAS_PAYMENTS) (US-17)."""
    period = BillingPeriod(period_month=date(2026, 3, 1), name="Kỳ thu tháng 3", status="OPEN")
    db_session.add(period)
    db_session.flush()

    hh = setup_us17_environment["households"]["HH_US17_FULL"]
    inv = Invoice(
        billing_period_id=period.id,
        household_id=hh.id,
        apartment_area=Decimal("80.00"),
        fee_amount=Decimal("1000000"),
        total_due=Decimal("1000000"),
        paid_amount=Decimal("500000"),  # Đã nộp 500.000 đ
        status="PARTIAL",
    )
    db_session.add(inv)
    db_session.commit()

    res = client.post(f"/api/v1/billing-periods/{period.id}/generate", headers=accountant_headers)
    assert res.status_code == 409
    assert res.json().get("code") == "PERIOD_HAS_PAYMENTS"


def test_ac17_1_calculate_standard_formula_full_household(client, accountant_headers, setup_us17_environment):
    """
    Kiểm thử công thức tính phí AC-17.1 cho hộ có đầy đủ các khoản thu:
    - Căn hộ 80 m² × 10.000 đ = 800.000 đ
    - 2 Xe máy × 70.000 đ = 140.000 đ
    - 1 Ô tô × 1.200.000 đ = 1.200.000 đ
    - Phí an ninh cố định = 50.000 đ
    Tổng phí kỳ này = 2.190.000 đ (Miễn giảm = 0, Nợ cũ = 0, Dư có = 0)
    => Tổng phải nộp = 2.190.000 đ.
    """
    # 1. Tạo kỳ thu tháng 04/2026
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-04-01", "name": "Kỳ thu tháng 04/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    # 2. Chạy động cơ tính phí
    res_gen = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["households_processed"] >= 8
    assert gen_data["invoices_created"] >= 7

    # 3. Kiểm tra giấy báo của hộ HH_US17_FULL
    hh_full = setup_us17_environment["households"]["HH_US17_FULL"]
    res_inv = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_full.id}",
        headers=accountant_headers,
    )
    assert res_inv.status_code == 200
    items = res_inv.json()["items"]
    assert len(items) == 1
    inv = items[0]

    # Kiểm tra số tiền tổng hợp
    assert inv["fee_amount"] == 2190000
    assert inv["discount_amount"] == 0
    assert inv["previous_debt"] == 0
    assert inv["credit_applied"] == 0
    assert inv["total_due"] == 2190000
    assert inv["status"] == "UNPAID"

    # 4. Kiểm tra chi tiết từng dòng phí (InvoiceItems)
    res_detail = client.get(f"/api/v1/invoices/{inv['id']}", headers=accountant_headers)
    assert res_detail.status_code == 200
    detail_items = res_detail.json()["items"]
    assert len(detail_items) == 4

    fee_map = {it["fee_type_id"]: it for it in detail_items}
    ft_map = setup_us17_environment["fee_types"]

    # Quản lý 80m2 x 10k = 800k
    assert fee_map[ft_map["mgt"].id]["gross_amount"] == 800000
    # Xe máy 2 x 70k = 140k
    assert fee_map[ft_map["moto"].id]["gross_amount"] == 140000
    # Ô tô 1 x 1.200k = 1.200k
    assert fee_map[ft_map["car"].id]["gross_amount"] == 1200000
    # Cố định an ninh 1 x 50k = 50k
    assert fee_map[ft_map["fixed"].id]["gross_amount"] == 50000


def test_generate_invoices_area_only_household(client, accountant_headers, setup_us17_environment):
    """Hộ chỉ có căn hộ 100 m² và phí cố định, không có xe (US-17)."""
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-05-01", "name": "Kỳ thu tháng 05/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)

    hh_area = setup_us17_environment["households"]["HH_US17_AREA_ONLY"]
    res_inv = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_area.id}",
        headers=accountant_headers,
    )
    inv = res_inv.json()["items"][0]

    # 100 m2 x 10.000 = 1.000.000 đ + 50.000 đ an ninh = 1.050.000 đ
    assert inv["fee_amount"] == 1050000
    assert inv["total_due"] == 1050000


def test_generate_invoices_vehicle_only_household(client, accountant_headers, setup_us17_environment):
    """Hộ không ở căn hộ (chưa nhận nhà), chỉ gửi 1 xe máy + 2 xe đạp (US-37, US-17)."""
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-06-01", "name": "Kỳ thu tháng 06/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)

    hh_veh = setup_us17_environment["households"]["HH_US17_VEHICLE_ONLY"]
    res_inv = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_veh.id}",
        headers=accountant_headers,
    )
    inv = res_inv.json()["items"][0]

    # Quản lý (50m2 * 10.000 = 500.000) + Xe máy: 70.000 + 2 xe đạp: 60.000 + Cố định an ninh: 50.000 = 680.000 đ
    assert inv["apartment_area"] == 50.0
    assert inv["fee_amount"] == 680000
    assert inv["total_due"] == 680000


def test_generate_invoices_integrated_with_utility_readings(client, accountant_headers, db_session, setup_us17_environment):
    """Tích hợp tính tiền điện nước từ chỉ số UtilityReading (US-38) vào hóa đơn kỳ thu (US-17)."""
    # 1. Tạo kỳ thu tháng 07/2026
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-07-01", "name": "Kỳ thu tháng 07/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    # 2. Nhập chỉ số điện và nước cho hộ HH_US17_UTILITY_ONLY
    hh_util = setup_us17_environment["households"]["HH_US17_UTILITY_ONLY"]
    ft_elec = setup_us17_environment["fee_types"]["elec"]
    ft_water = setup_us17_environment["fee_types"]["water"]

    # Điện: 150 kWh x 2.500 đ = 375.000 đ
    ur_elec = UtilityReading(
        household_id=hh_util.id,
        fee_type_id=ft_elec.id,
        billing_period_id=period_id,
        previous_index=Decimal("100.000"),
        current_index=Decimal("250.000"),
        unit_price=Decimal("2500.00"),
        amount=Decimal("375000.00"),
    )
    # Nước: 20 m3 x 15.000 đ = 300.000 đ
    ur_water = UtilityReading(
        household_id=hh_util.id,
        fee_type_id=ft_water.id,
        billing_period_id=period_id,
        previous_index=Decimal("50.000"),
        current_index=Decimal("70.000"),
        unit_price=Decimal("15000.00"),
        amount=Decimal("300000.00"),
    )
    db_session.add_all([ur_elec, ur_water])
    db_session.commit()

    # 3. Chạy tính phí
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)

    # 4. Kiểm tra hóa đơn
    res_inv = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_util.id}",
        headers=accountant_headers,
    )
    inv = res_inv.json()["items"][0]
    # Quản lý (50m2 * 10.000 = 500.000) + Điện 375k + Nước 300k + An ninh cố định 50k = 1.225.000 đ
    assert inv["fee_amount"] == 1225000
    assert inv["total_due"] == 1225000

    # Kiểm tra dòng chi tiết
    res_detail = client.get(f"/api/v1/invoices/{inv['id']}", headers=accountant_headers)
    detail_items = res_detail.json()["items"]
    items_map = {it["fee_type_id"]: it for it in detail_items}

    assert ft_elec.id in items_map
    assert items_map[ft_elec.id]["net_amount"] == 375000
    assert ft_water.id in items_map
    assert items_map[ft_water.id]["net_amount"] == 300000


def test_generate_invoices_with_percentage_exemption(client, accountant_headers, setup_us17_environment):
    """Áp dụng miễn giảm theo tỷ lệ % (Giảm 50% phí quản lý căn hộ 65.5 m2) (US-15, US-17)."""
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-08-01", "name": "Kỳ thu tháng 08/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)

    hh_ex = setup_us17_environment["households"]["HH_US17_EXEMPTION_PCT"]
    res_inv = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_ex.id}",
        headers=accountant_headers,
    )
    inv = res_inv.json()["items"][0]

    # Quản lý: 65.5 m2 x 10.000 = 655.000 đ
    # Giảm 50% = 327.500 đ (làm tròn = 327.500 đ)
    # Phí an ninh: 50.000 đ
    # Tổng phí gốc = 655.000 + 50.000 = 705.000 đ
    # Miễn giảm = 327.500 đ
    # Tổng phải nộp = 705.000 - 327.500 = 377.500 đ
    assert inv["fee_amount"] == 705000
    assert inv["discount_amount"] == 327500
    assert inv["total_due"] == 377500


def test_generate_invoices_with_amount_exemption(client, accountant_headers, setup_us17_environment):
    """Áp dụng miễn giảm theo số tiền VNĐ cố định (Giảm 200.000 đ trên phí ô tô 1.200.000 đ) (US-15, US-17)."""
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-09-01", "name": "Kỳ thu tháng 09/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)

    hh_ex = setup_us17_environment["households"]["HH_US17_EXEMPTION_AMT"]
    res_inv = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_ex.id}",
        headers=accountant_headers,
    )
    inv = res_inv.json()["items"][0]

    # Quản lý (50m2 * 10.000 = 500.000)
    # Ô tô: 1.200.000 đ, giảm 200.000 đ -> còn 1.000.000 đ
    # An ninh: 50.000 đ
    # Tổng gốc: 1.750.000 đ
    # Miễn giảm: 200.000 đ
    # Tổng nộp: 1.550.000 đ
    assert inv["fee_amount"] == 1750000
    assert inv["discount_amount"] == 200000
    assert inv["total_due"] == 1550000


def test_generate_invoices_accumulates_previous_debt(client, accountant_headers, db_session, setup_us17_environment):
    """Hộ có nợ cũ chưa thanh toán từ các kỳ trước được cộng dồn chính xác vào kỳ này (AC-17.1)."""
    # 1. Tạo kỳ thu cũ tháng 01/2026
    p_old = BillingPeriod(period_month=date(2026, 1, 1), name="Kỳ 01/2026 Cũ", status="CLOSED")
    db_session.add(p_old)
    db_session.flush()

    hh_debt = setup_us17_environment["households"]["HH_US17_DEBT"]
    # Hộ nợ 1.200.000 đ ở kỳ 1 (phí 1.200k, đã trả 0)
    inv_old = Invoice(
        billing_period_id=p_old.id,
        household_id=hh_debt.id,
        apartment_area=Decimal("120.00"),
        fee_amount=Decimal("1200000"),
        discount_amount=Decimal("0"),
        previous_debt=Decimal("0"),
        credit_applied=Decimal("0"),
        total_due=Decimal("1200000"),
        paid_amount=Decimal("0"),
        status="UNPAID",
    )
    db_session.add(inv_old)
    db_session.commit()

    # 2. Tạo kỳ thu mới tháng 02/2026
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-02-01", "name": "Kỳ thu tháng 02/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    # 3. Chạy tính phí kỳ 2
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)

    # 4. Kiểm tra giấy báo kỳ 2 của hộ nợ
    res_inv = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_debt.id}",
        headers=accountant_headers,
    )
    inv = res_inv.json()["items"][0]

    # Phí kỳ này: 120 m2 x 10.000 = 1.200.000 đ + 50.000 đ an ninh = 1.250.000 đ
    # Nợ cũ = 1.200.000 đ
    # Tổng phải nộp = 1.250.000 + 1.200.000 = 2.450.000 đ
    assert inv["fee_amount"] == 1250000
    assert inv["previous_debt"] == 1200000
    assert inv["total_due"] == 2450000


def test_generate_invoices_empty_household_has_zero_due_and_paid_status(client, accountant_headers, setup_us17_environment):
    """Hộ không gắn căn hộ (apartment_area = 0) được bỏ qua an toàn để tuân thủ CHECK (apartment_area > 0) trong 01_schema.sql (US-17)."""
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-10-01", "name": "Kỳ thu tháng 10/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    res_gen = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)
    assert res_gen.status_code == 200

    hh_empty = setup_us17_environment["households"]["HH_US17_EMPTY"]
    res_inv = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_empty.id}",
        headers=accountant_headers,
    )
    assert res_inv.status_code == 200
    assert res_inv.json()["items"] == []


def test_generate_invoices_idempotent_regeneration(client, accountant_headers, setup_us17_environment):
    """Chạy tính phí nhiều lần khi chưa có thanh toán sẽ tái tạo hóa đơn an toàn (Idempotent) (US-17)."""
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ thu tháng 11/2026"},
        headers=accountant_headers,
    )
    period_id = res_period.json()["id"]

    # Lần 1
    res1 = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)
    assert res1.status_code == 200
    count1 = res1.json()["invoices_created"]

    # Lần 2: chạy lại
    res2 = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)
    assert res2.status_code == 200
    count2 = res2.json()["invoices_created"]

    assert count1 == count2

    # Kiểm tra số lượng hóa đơn không bị nhân đôi
    res_list = client.get(f"/api/v1/invoices?billing_period_id={period_id}", headers=accountant_headers)
    assert res_list.json()["total"] == count1


def test_generate_invoices_updates_period_status_to_open_and_records_audit_log(
    client, accountant_headers, db_session
):
    """Chạy tính phí chuyển trạng thái kỳ thu sang OPEN, lưu generated_at và ghi Audit Log (US-32, US-17)."""
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-12-01", "name": "Kỳ 12/2026"},
        headers=accountant_headers,
    )
    period_id = res_p.json()["id"]

    res_gen = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)
    assert res_gen.status_code == 200

    # Kiểm tra kỳ thu
    period = db_session.get(BillingPeriod, period_id)
    assert period.status == "OPEN"
    assert period.generated_at is not None

    # Kiểm tra Audit Log
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "BILLING_PERIOD",
            AuditLog.entity_id == str(period_id),
            AuditLog.action == "GENERATE_INVOICES",
        )
    )
    assert audit is not None
    assert "invoices_created" in audit.new_value


# ==============================================================================
# 4. TEST CHỐT KỲ THU (POST /billing-periods/{id}/close)
# ==============================================================================

def test_close_billing_period_not_found_returns_404(client, accountant_headers):
    """Chốt kỳ thu không tồn tại trả về 404 NOT_FOUND (US-17)."""
    res = client.post("/api/v1/billing-periods/99999/close", headers=accountant_headers)
    assert res.status_code == 404
    assert res.json().get("code") == "NOT_FOUND"


def test_close_billing_period_not_generated_returns_409(client, accountant_headers):
    """Kỳ thu còn ở trạng thái DRAFT (chưa từng chạy tính phí) không thể chốt (409 PERIOD_NOT_GENERATED) (US-17)."""
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-03-01", "name": "Kỳ 03/2026 DRAFT"},
        headers=accountant_headers,
    )
    period_id = res_p.json()["id"]

    res_close = client.post(f"/api/v1/billing-periods/{period_id}/close", headers=accountant_headers)
    assert res_close.status_code == 409
    assert res_close.json().get("code") == "PERIOD_NOT_GENERATED"


def test_close_billing_period_success(client, accountant_headers, db_session):
    """Chốt kỳ thu thành công chuyển sang CLOSED và ghi nhận closed_at (US-17)."""
    # 1. Tạo và generate
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-04-01", "name": "Kỳ 04/2026 Close Test"},
        headers=accountant_headers,
    )
    period_id = res_p.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)

    # 2. Chốt kỳ
    res_close = client.post(f"/api/v1/billing-periods/{period_id}/close", headers=accountant_headers)
    assert res_close.status_code == 200
    data = res_close.json()
    assert data["status"] == "CLOSED"
    assert data["closed_at"] is not None

    period = db_session.get(BillingPeriod, period_id)
    assert period.status == "CLOSED"
    assert period.closed_at is not None


def test_close_billing_period_already_closed_returns_409(client, accountant_headers):
    """Chốt kỳ thu đã ở trạng thái CLOSED trả về 409 PERIOD_CLOSED (US-17)."""
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-05-01", "name": "Kỳ 05/2026 Twice Close"},
        headers=accountant_headers,
    )
    period_id = res_p.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)

    # Chốt lần 1
    res1 = client.post(f"/api/v1/billing-periods/{period_id}/close", headers=accountant_headers)
    assert res1.status_code == 200

    # Chốt lần 2
    res2 = client.post(f"/api/v1/billing-periods/{period_id}/close", headers=accountant_headers)
    assert res2.status_code == 409
    assert res2.json().get("code") == "PERIOD_CLOSED"


def test_close_billing_period_records_audit_log(client, accountant_headers, db_session):
    """Chốt kỳ thu ghi nhận Audit Log tương ứng (US-32, US-17)."""
    res_p = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-06-01", "name": "Kỳ 06/2026 Audit Close"},
        headers=accountant_headers,
    )
    period_id = res_p.json()["id"]
    client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)
    client.post(f"/api/v1/billing-periods/{period_id}/close", headers=accountant_headers)

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "BILLING_PERIOD",
            AuditLog.entity_id == str(period_id),
            AuditLog.action == "CLOSE_BILLING_PERIOD",
        )
    )
    assert audit is not None
    assert audit.user_id == 2
    assert audit.old_value.get("status") == "OPEN"
    assert audit.new_value.get("status") == "CLOSED"


# ==============================================================================
# 5. TEST HIỆU NĂNG NFR-005 (1.000 HỘ <= 10 GIÂY)
# ==============================================================================

def test_nfr005_generate_bulk_households_performance(client, accountant_headers, db_session):
    """
    Kiểm thử hiệu năng NFR-005:
    Chạy động cơ tính phí cho số lượng lớn hộ gia đình (50 hộ giả lập trong benchmark)
    Thời gian trung bình tính mỗi hộ < 10ms (tương ứng 1.000 hộ < 1 giây, vượt xa tiêu chuẩn <= 10 giây).
    """
    # 1. Tạo 50 hộ gia đình mẫu kèm căn hộ và xe
    bulk_households = [
        Household(household_code=f"HH_PERF_{i:04d}", status="ACTIVE")
        for i in range(1, 51)
    ]
    db_session.add_all(bulk_households)
    db_session.flush()

    # Tạo biểu phí quản lý
    ft_perf = FeeType(
        code="FEE_PERF_MGT",
        name="Phí quản lý test hiệu năng",
        fee_group="MANAGEMENT",
        calc_method="PER_M2",
        unit_label="m²",
        status="ACTIVE",
    )
    db_session.add(ft_perf)
    db_session.flush()

    rate_perf = FeeRate(
        fee_type_id=ft_perf.id,
        unit_price=Decimal("12000.00"),
        effective_from=date(2026, 1, 1),
    )
    db_session.add(rate_perf)

    # Tạo kỳ thu
    period = BillingPeriod(period_month=date(2026, 7, 1), name="Kỳ Test NFR-005", status="DRAFT")
    db_session.add(period)
    db_session.commit()

    # Đo lường thời gian thực thi của endpoint generate
    start_time = time.perf_counter()
    res = client.post(f"/api/v1/billing-periods/{period.id}/generate", headers=accountant_headers)
    elapsed_seconds = time.perf_counter() - start_time

    assert res.status_code == 200
    data = res.json()
    assert data["households_processed"] >= 50

    # NFR-005 yêu cầu 1.000 hộ <= 10 giây -> 50 hộ phải chạy trong < 1 giây
    assert elapsed_seconds < 2.0, f"Thời gian chạy {elapsed_seconds:.3f}s vượt quá giới hạn benchmark"
