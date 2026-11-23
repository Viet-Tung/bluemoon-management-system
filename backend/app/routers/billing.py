import math
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
# [SỬA] Xóa import thừa `Any`
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.billing import BillingPeriod, Invoice, InvoiceItem
from app.models.fee import FeeExemption, FeeRate, FeeType
from app.models.property import ApartmentOccupancy, Household
from app.models.user import AuditLog, User
from app.models.vehicle import Vehicle
# [SỬA] Xóa import thừa `Invoice as InvoiceSchema`
from app.schemas.billing import (
    BillingPeriod as BillingPeriodSchema,
    BillingPeriodCreate,
    BillingPeriodPage,
    BillingPeriodStatus,
    GenerateResult,
    InvoiceDetail,
    InvoicePage,
    InvoiceStatus,
)

router = APIRouter(tags=["Billing"])


# =====================================================================
# 1. KỲ THU PHÍ (BILLING PERIODS)
# =====================================================================

@router.get(
    "/billing-periods",
    response_model=BillingPeriodPage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách kỳ thu",
    description="Tra cứu danh sách kỳ thu có phân trang và lọc theo trạng thái (US-17). Quyền: ADMIN, ACCOUNTANT.",
    operation_id="listBillingPeriods",
)
def list_billing_periods(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Kích thước trang (1-100)"),
    status_filter: Optional[BillingPeriodStatus] = Query(
        default=None, alias="status", description="Lọc theo trạng thái (DRAFT, OPEN, CLOSED)"
    ),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> BillingPeriodPage:
    """Danh sách kỳ thu phí có phân trang (US-17)."""
    stmt = select(BillingPeriod)
    if status_filter is not None:
        stmt = stmt.where(BillingPeriod.status == status_filter.value)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    items = db.execute(
        stmt.order_by(BillingPeriod.period_month.desc(), BillingPeriod.id.desc())
        .offset(offset)
        .limit(page_size)
    ).scalars().all()

    return BillingPeriodPage(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/billing-periods",
    response_model=BillingPeriodSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo kỳ thu mới",
    description="Tạo kỳ tính phí hàng tháng mới (ngày 1 của tháng) (US-17). Quyền: ADMIN, ACCOUNTANT.",
    operation_id="createBillingPeriod",
)
def create_billing_period(
    req: BillingPeriodCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> BillingPeriodSchema:
    """Tạo kỳ thu mới (US-17)."""
    # 1. Kiểm tra trùng kỳ thu (tháng đã tồn tại)
    existing = db.execute(
        select(BillingPeriod).where(BillingPeriod.period_month == req.period_month)
    ).scalar_one_or_none()

    if existing:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_PERIOD",
            message=f"Kỳ thu phí tháng {req.period_month.strftime('%m/%Y')} đã tồn tại.",
            details=[
                {"field": "period_month", "message": f"Kỳ thu cho tháng {req.period_month} đã được tạo trước đó."}
            ],
        )

    # 2. Tạo bản ghi BillingPeriod
    period = BillingPeriod(
        period_month=req.period_month,
        name=req.name,
        due_date=req.due_date,
        status=BillingPeriodStatus.DRAFT.value,
        created_by=current_user.id,
    )
    db.add(period)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_PERIOD",
            message=f"Kỳ thu phí tháng {req.period_month.strftime('%m/%Y')} đã tồn tại.",
            details=[
                {"field": "period_month", "message": f"Kỳ thu cho tháng {req.period_month} đã được tạo trước đó."}
            ],
        )

    # 3. Ghi Audit Log (US-32)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_BILLING_PERIOD",
        entity_type="BILLING_PERIOD",
        entity_id=str(period.id),
        old_value=None,
        new_value={
            "id": period.id,
            "period_month": str(period.period_month),
            "name": period.name,
            "due_date": str(period.due_date) if period.due_date else None,
            "status": period.status,
        },
        reason=f"Tạo kỳ thu phí mới '{period.name}' cho tháng {period.period_month.strftime('%m/%Y')}.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(period)

    return period


@router.get(
    "/billing-periods/{id}",
    response_model=BillingPeriodSchema,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết kỳ thu",
    description="Tra cứu chi tiết một kỳ thu phí theo ID (US-17). Quyền: ADMIN, ACCOUNTANT.",
    operation_id="getBillingPeriod",
)
def get_billing_period(
    id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> BillingPeriodSchema:
    """Chi tiết kỳ thu (US-17)."""
    period = db.get(BillingPeriod, id)
    if not period:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Không tìm thấy kỳ thu phí.",
            details=[{"field": "id", "message": f"Kỳ thu với ID {id} không tồn tại."}],
        )
    return period


# =====================================================================
# 2. ĐỘNG CƠ TÍNH PHÍ GỬI XE & TỔNG HỢP (US-37, US-17)
# =====================================================================

@router.post(
    "/billing-periods/{id}/generate",
    response_model=GenerateResult,
    status_code=status.HTTP_200_OK,
    summary="Chạy động cơ tính phí tự động cho toàn bộ hộ",
    description="Tự động tính phí gửi xe (US-37) và phí quản lý (US-17), snapshot đơn giá và lập giấy báo nộp tiền cho toàn bộ hộ. Quyền: ADMIN, ACCOUNTANT.",
    operation_id="generateInvoices",
)
def generate_invoices(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> GenerateResult:
    """Chạy động cơ tính phí gửi xe và lập giấy báo nộp phí (US-37, AC-37.1, US-17)."""
    # 1. Kiểm tra tồn tại của Kỳ thu
    period = db.get(BillingPeriod, id)
    if not period:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Không tìm thấy kỳ thu phí.",
            details=[{"field": "id", "message": f"Kỳ thu với ID {id} không tồn tại."}],
        )

    # 2. Kiểm tra nếu kỳ thu đã chốt (CLOSED) -> chặn không cho tính lại (409 PERIOD_CLOSED)
    if period.status == BillingPeriodStatus.CLOSED.value:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="PERIOD_CLOSED",
            message="Kỳ thu phí đã chốt, không thể tính lại phí.",
            details=[{"field": "status", "message": "Kỳ thu đang ở trạng thái CLOSED."}],
        )

    # 3. Kiểm tra xem kỳ này đã phát sinh biên lai thanh toán chưa -> chặn (409 PERIOD_HAS_PAYMENTS)
    has_payments = db.execute(
        select(Invoice.id).where(
            Invoice.billing_period_id == id,
            Invoice.paid_amount > Decimal("0"),
        )
    ).first()
    if has_payments:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="PERIOD_HAS_PAYMENTS",
            message="Kỳ thu phí đã có biên lai thanh toán, không thể tạo lại.",
            details=[
                {"field": "billing_period_id", "message": "Đã có hộ gia đình thanh toán phí trong kỳ thu này."}
            ],
        )

    # 4. Nếu đã có hóa đơn cũ trong kỳ (nhưng chưa có payment), xóa sạch để tái tạo lại (idempotent regeneration)
    old_inv_ids = select(Invoice.id).where(Invoice.billing_period_id == id)
    db.execute(delete(InvoiceItem).where(InvoiceItem.invoice_id.in_(old_inv_ids)))
    db.execute(delete(Invoice).where(Invoice.billing_period_id == id))
    db.flush()

    # 5. Lấy danh sách tất cả Hộ gia đình đang ACTIVE
    households = db.execute(
        select(Household).where(Household.status == "ACTIVE").order_by(Household.id)
    ).scalars().all()

    # 6. Chuẩn bị danh mục khoản thu ACTIVE
    fee_types = db.execute(
        select(FeeType).where(FeeType.status == "ACTIVE")
    ).scalars().all()

    parking_fee_types: Dict[str, FeeType] = {}
    area_fee_types: List[FeeType] = []
    for ft in fee_types:
        if ft.calc_method == "PER_VEHICLE" and ft.vehicle_type:
            parking_fee_types[ft.vehicle_type] = ft
        elif ft.calc_method == "PER_M2":
            area_fee_types.append(ft)

    # 7. Lấy đơn giá FeeRate có hiệu lực tại ngày period_month
    effective_rates: Dict[int, FeeRate] = {}
    for ft in fee_types:
        rate = db.execute(
            select(FeeRate)
            .where(
                FeeRate.fee_type_id == ft.id,
                FeeRate.effective_from <= period.period_month,
                or_(FeeRate.effective_to.is_(None), FeeRate.effective_to >= period.period_month),
            )
            .order_by(FeeRate.effective_from.desc(), FeeRate.id.desc())
        ).scalars().first()
        if rate:
            effective_rates[ft.id] = rate

    # 8. Vòng lặp tính toán chi tiết từng hộ
    created_invoices: List[Invoice] = []
    total_fee_amount = Decimal("0")

    for hh in households:
        # [SỬA] Chỉ lấy căn hộ đang ở trong kỳ (end_date IS NULL hoặc end_date >= period_month),
        # bỏ nhánh fallback lấy lại lịch sử cũ đã chuyển đi để tránh tính oan phí m²
        occupancy = db.execute(
            select(ApartmentOccupancy)
            .where(
                ApartmentOccupancy.household_id == hh.id,
                or_(
                    ApartmentOccupancy.end_date.is_(None),
                    ApartmentOccupancy.end_date >= period.period_month,
                ),
            )
            .order_by(ApartmentOccupancy.start_date.desc(), ApartmentOccupancy.id.desc())
        ).scalars().first()

        apartment_id: Optional[int] = None
        apartment_area = Decimal("0")
        has_apartment = False

        if occupancy and occupancy.apartment:
            apartment_id = occupancy.apartment_id
            apartment_area = Decimal(str(occupancy.apartment.area_m2))
            has_apartment = True

        # Lấy danh sách phương tiện ACTIVE của hộ gia đình (US-36, US-37)
        vehicles = db.execute(
            select(Vehicle).where(
                Vehicle.household_id == hh.id,
                Vehicle.status == "ACTIVE",
            )
        ).scalars().all()
        vehicle_counts = Counter(v.vehicle_type for v in vehicles)

        # Lấy chính sách miễn giảm ACTIVE của hộ có hiệu lực trong kỳ (US-15, US-16)
        exemptions = db.execute(
            select(FeeExemption).where(
                FeeExemption.household_id == hh.id,
                FeeExemption.status == "ACTIVE",
                FeeExemption.valid_from <= period.period_month,
                or_(FeeExemption.valid_to.is_(None), FeeExemption.valid_to >= period.period_month),
            )
        ).scalars().all()
        exemptions_map = {e.fee_type_id: e for e in exemptions}

        invoice_items: List[InvoiceItem] = []

        # =============================================================
        # A. TÍNH PHÍ GỬI XE THEO TỪNG LOẠI XE (US-37 - AC-37.1)
        # =============================================================
        for v_type in ("MOTORBIKE", "CAR", "BICYCLE"):
            count = vehicle_counts.get(v_type, 0)
            if count > 0:
                ft = parking_fee_types.get(v_type)
                if ft and ft.id in effective_rates:
                    rate = effective_rates[ft.id]
                    qty = Decimal(str(count))
                    price = Decimal(str(rate.unit_price))
                    gross = (qty * price).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                    discount = Decimal("0")

                    exemption = exemptions_map.get(ft.id)
                    if exemption:
                        if exemption.discount_type == "PERCENT":
                            pct = Decimal(str(exemption.discount_value))
                            discount = (gross * pct / Decimal("100")).quantize(
                                Decimal("1"), rounding=ROUND_HALF_UP
                            )
                            discount = min(gross, discount)
                        elif exemption.discount_type == "AMOUNT":
                            discount = min(
                                gross,
                                Decimal(str(exemption.discount_value)).quantize(
                                    Decimal("1"), rounding=ROUND_HALF_UP
                                ),
                            )

                    net = gross - discount
                    desc = f"{count} {ft.name} × {int(price):,} đ"

                    item = InvoiceItem(
                        fee_type_id=ft.id,
                        quantity=qty,
                        unit_price=price,
                        gross_amount=gross,
                        discount_amount=discount,
                        net_amount=net,
                        paid_amount=Decimal("0"),
                        description=desc,
                    )
                    invoice_items.append(item)

        # =============================================================
        # B. TÍNH CÁC KHOẢN PHÍ THEO DIỆN TÍCH M² (US-17)
        # =============================================================
        if has_apartment and apartment_area > Decimal("0"):
            for area_ft in area_fee_types:
                if area_ft.id not in effective_rates:
                    continue
                rate = effective_rates[area_ft.id]
                qty = apartment_area
                price = Decimal(str(rate.unit_price))
                gross = (qty * price).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                discount = Decimal("0")

                exemption = exemptions_map.get(area_ft.id)
                if exemption:
                    if exemption.discount_type == "PERCENT":
                        pct = Decimal(str(exemption.discount_value))
                        discount = (gross * pct / Decimal("100")).quantize(
                            Decimal("1"), rounding=ROUND_HALF_UP
                        )
                        discount = min(gross, discount)
                    elif exemption.discount_type == "AMOUNT":
                        discount = min(
                            gross,
                            Decimal(str(exemption.discount_value)).quantize(
                                Decimal("1"), rounding=ROUND_HALF_UP
                            ),
                        )

                net = gross - discount
                desc = f"{apartment_area:g} m² × {int(price):,} đ"

                item = InvoiceItem(
                    fee_type_id=area_ft.id,
                    quantity=qty,
                    unit_price=price,
                    gross_amount=gross,
                    discount_amount=discount,
                    net_amount=net,
                    paid_amount=Decimal("0"),
                    description=desc,
                )
                invoice_items.append(item)

        # =============================================================
        # TỔNG HỢP HÓA ĐƠN CHO HỘ TRONG KỲ (AC-17.1)
        # =============================================================
        hh_fee_amount = sum((it.gross_amount for it in invoice_items), Decimal("0"))
        hh_discount_amount = sum((it.discount_amount for it in invoice_items), Decimal("0"))

        # [SỬA] Chỉnh lại thụt lề chuẩn PEP8 cho biểu thức func.sum(...)
        prev_debt_stmt = (
            select(
                func.coalesce(
                    func.sum(
                        Invoice.fee_amount
                        - Invoice.discount_amount
                        - Invoice.credit_applied
                        - Invoice.paid_amount
                    ),
                    0,
                )
            )
            .join(BillingPeriod, Invoice.billing_period_id == BillingPeriod.id)
            .where(
                Invoice.household_id == hh.id,
                BillingPeriod.period_month < period.period_month,
            )
        )
        prev_debt_val = db.execute(prev_debt_stmt).scalar() or 0
        previous_debt = max(
            Decimal("0"),
            Decimal(str(prev_debt_val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP),
        )

        credit_applied = Decimal("0")
        total_due = max(
            Decimal("0"),
            hh_fee_amount - hh_discount_amount + previous_debt - credit_applied,
        )
        status_val = "PAID" if total_due == Decimal("0") else "UNPAID"

        inv = Invoice(
            billing_period_id=period.id,
            household_id=hh.id,
            apartment_id=apartment_id,
            apartment_area=apartment_area,
            fee_amount=hh_fee_amount,
            discount_amount=hh_discount_amount,
            previous_debt=previous_debt,
            credit_applied=credit_applied,
            total_due=total_due,
            paid_amount=Decimal("0"),
            status=status_val,
            items=invoice_items,
        )
        db.add(inv)
        created_invoices.append(inv)
        total_fee_amount += total_due

    # 9. Cập nhật trạng thái Kỳ thu -> OPEN và ghi nhận thời điểm tính phí
    now = datetime.now(timezone.utc)
    period.status = BillingPeriodStatus.OPEN.value
    period.generated_at = now
    period.updated_at = now

    # 10. Ghi Audit Log (US-32)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="GENERATE_INVOICES",
        entity_type="BILLING_PERIOD",
        entity_id=str(period.id),
        old_value=None,
        new_value={
            "period_id": period.id,
            "period_month": str(period.period_month),
            "households_processed": len(households),
            "invoices_created": len(created_invoices),
            "total_fee_amount": int(total_fee_amount),
        },
        reason=f"Chạy động cơ tính phí kỳ '{period.name}': xử lý {len(households)} hộ, tạo {len(created_invoices)} giấy báo, tổng tiền {int(total_fee_amount):,} đ.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()

    return GenerateResult(
        households_processed=len(households),
        invoices_created=len(created_invoices),
        total_fee_amount=int(total_fee_amount),
    )


@router.post(
    "/billing-periods/{id}/close",
    response_model=BillingPeriodSchema,
    status_code=status.HTTP_200_OK,
    summary="Chốt kỳ thu",
    description="Chốt kỳ thu phí (sau khi chốt không thể sửa đổi hay chạy lại tính phí) (US-17). Quyền: ADMIN, ACCOUNTANT.",
    operation_id="closeBillingPeriod",
)
def close_billing_period(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> BillingPeriodSchema:
    """Chốt kỳ thu phí (US-17)."""
    period = db.get(BillingPeriod, id)
    if not period:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Không tìm thấy kỳ thu phí.",
            details=[{"field": "id", "message": f"Kỳ thu với ID {id} không tồn tại."}],
        )

    if period.status == BillingPeriodStatus.CLOSED.value:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="PERIOD_CLOSED",
            message="Kỳ thu phí đã ở trạng thái chốt (CLOSED).",
            details=[{"field": "status", "message": "Kỳ thu này đã được chốt trước đó."}],
        )

    if period.status == BillingPeriodStatus.DRAFT.value or period.generated_at is None:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="PERIOD_NOT_GENERATED",
            message="Kỳ thu chưa được chạy tính phí, không thể chốt kỳ.",
            details=[{"field": "status", "message": "Vui lòng chạy tính phí trước khi chốt kỳ thu."}],
        )

    old_status = period.status
    now = datetime.now(timezone.utc)
    period.status = BillingPeriodStatus.CLOSED.value
    period.closed_at = now
    period.updated_at = now

    # Ghi Audit Log (US-32)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="CLOSE_BILLING_PERIOD",
        entity_type="BILLING_PERIOD",
        entity_id=str(period.id),
        old_value={"status": old_status},
        new_value={"status": period.status, "closed_at": now.isoformat()},
        reason=f"Chốt kỳ thu phí '{period.name}'.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(period)

    return period


# =====================================================================
# 3. GIẤY BÁO NỘP PHÍ (INVOICES)
# =====================================================================

@router.get(
    "/invoices",
    response_model=InvoicePage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách giấy báo nộp phí",
    description="Tra cứu danh sách giấy báo nộp phí có phân trang, bộ lọc theo kỳ, theo hộ, theo trạng thái (US-17, US-47). Quyền: ADMIN, ACCOUNTANT.",
    operation_id="listInvoices",
)
def list_invoices(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Kích thước trang (1-100)"),
    billing_period_id: Optional[int] = Query(default=None, description="Lọc theo ID kỳ thu"),
    household_id: Optional[int] = Query(default=None, description="Lọc theo ID hộ gia đình"),
    status_filter: Optional[InvoiceStatus] = Query(
        default=None, alias="status", description="Lọc theo trạng thái thanh toán (UNPAID, PARTIAL, PAID)"
    ),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> InvoicePage:
    """Tra cứu danh sách giấy báo nộp phí (US-17, US-47)."""
    stmt = select(Invoice)

    if billing_period_id is not None:
        stmt = stmt.where(Invoice.billing_period_id == billing_period_id)

    if household_id is not None:
        stmt = stmt.where(Invoice.household_id == household_id)

    if status_filter is not None:
        stmt = stmt.where(Invoice.status == status_filter.value)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    items = db.execute(
        stmt.order_by(Invoice.id.desc())
        .offset(offset)
        .limit(page_size)
    ).scalars().all()

    return InvoicePage(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/invoices/{id}",
    response_model=InvoiceDetail,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết giấy báo nộp phí (kèm từng khoản phí)",
    description="Tra cứu chi tiết một giấy báo nộp phí kèm danh sách từng dòng phí chi tiết (US-47, US-37). Quyền: ADMIN, ACCOUNTANT.",
    operation_id="getInvoice",
)
def get_invoice(
    id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> InvoiceDetail:
    """Chi tiết giấy báo nộp phí kèm danh sách từng khoản phí (US-47)."""
    invoice = db.execute(
        select(Invoice)
        .where(Invoice.id == id)
        .options(selectinload(Invoice.items).joinedload(InvoiceItem.fee_type))
    ).scalar_one_or_none()

    if not invoice:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Không tìm thấy giấy báo nộp phí.",
            details=[{"field": "id", "message": f"Giấy báo với ID {id} không tồn tại."}],
        )

    return invoice