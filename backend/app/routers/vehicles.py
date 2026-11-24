from datetime import date
from typing import Any, Dict, Optional
# [SỬA] Thêm Body để khai báo tường minh optional JSON body cho endpoint unregister
from fastapi import APIRouter, Body, Depends, Query, Request, status
from sqlalchemy import func, select
# [THÊM] Bắt lỗi vi phạm unique constraint ở tầng DB khi có request đồng thời
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles, sanitize_ip_address
from app.models.property import Household
from app.models.user import AuditLog, User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import (
    Vehicle as VehicleSchema,
    VehicleCreate,
    VehiclePage,
    VehicleStatus,
    VehicleType,
    VehicleUnregister,
    VehicleUpdate,
)

router = APIRouter(tags=["Vehicles"])


def _canonical_plate(plate: str) -> str:
    """Chuẩn hóa biển số để chống trùng/tìm kiếm: bỏ khoảng trắng, '-', '.' và viết hoa."""
    return "".join(plate.split()).replace("-", "").replace(".", "").upper()


def _sql_canonical_plate(col):
    """Biểu thức SQL chuẩn hóa biển số tương ứng với _canonical_plate."""
    return func.replace(
        func.replace(func.replace(func.upper(col), " ", ""), "-", ""),
        ".",
        "",
    )


@router.get(
    "",
    response_model=VehiclePage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách phương tiện",
    description="Tra cứu danh sách phương tiện có phân trang và bộ lọc theo hộ, trạng thái, loại xe, biển số (US-36). Phân quyền: ADMIN, ACCOUNTANT.",
    operation_id="listVehicles",
)
def list_vehicles(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Kích thước trang (1-100)"),
    household_id: Optional[int] = Query(default=None, description="Lọc theo ID hộ gia đình"),
    plate_number: Optional[str] = Query(default=None, description="Lọc theo biển số xe"),
    vehicle_type: Optional[VehicleType] = Query(default=None, description="Lọc theo loại xe"),
    status_filter: Optional[VehicleStatus] = Query(default=None, alias="status", description="Lọc theo trạng thái (ACTIVE, INACTIVE)"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> VehiclePage:
    """Tra cứu danh sách phương tiện có phân trang và bộ lọc (US-36)."""
    stmt = select(Vehicle)

    if household_id is not None:
        stmt = stmt.where(Vehicle.household_id == household_id)

    if status_filter is not None:
        stmt = stmt.where(Vehicle.status == status_filter.value)

    if vehicle_type is not None:
        stmt = stmt.where(Vehicle.vehicle_type == vehicle_type.value)

    if plate_number and plate_number.strip():
        clean_plate = _canonical_plate(plate_number)
        stmt = stmt.where(
            _sql_canonical_plate(Vehicle.plate_number).contains(clean_plate, autoescape=True)
        )

    # Đếm tổng số bản ghi
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    # Phân trang và sắp xếp giảm dần theo ID
    offset = (page - 1) * page_size
    items = db.scalars(
        stmt.order_by(Vehicle.id.desc()).offset(offset).limit(page_size)
    ).all()

    return VehiclePage(
        page=page,
        page_size=page_size,
        total=total,
        items=[VehicleSchema.model_validate(x) for x in items],
    )


@router.post(
    "",
    response_model=VehicleSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký phương tiện",
    description="Đăng ký phương tiện mới cho hộ gia đình (US-36). Chặn trùng biển số xe đang ACTIVE. Phân quyền: ADMIN.",
    operation_id="createVehicle",
)
def create_vehicle(
    req: VehicleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> VehicleSchema:
    """Đăng ký phương tiện mới cho hộ gia đình (US-36)."""
    # 1. Kiểm tra tồn tại của Hộ gia đình
    household = db.get(Household, req.household_id)
    if not household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình với ID {req.household_id}.",
            details=[{"field": "household_id", "message": f"Hộ gia đình ID {req.household_id} không tồn tại."}],
        )

    if household.status != "ACTIVE":
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=f"Hộ gia đình '{household.household_code}' đã ngừng hoạt động (INACTIVE), không thể đăng ký phương tiện.",
            details=[{"field": "household_id", "message": "Hộ gia đình đang ở trạng thái INACTIVE."}],
        )

    # 2. Kiểm tra trùng biển số xe đang ACTIVE (chuẩn hóa cả khoảng trắng, '-', '.')
    norm_plate = "".join(req.plate_number.split()).upper()
    canon_plate = _canonical_plate(req.plate_number)
    existing_vehicle = db.scalar(
        select(Vehicle).where(
            Vehicle.status == "ACTIVE",
            _sql_canonical_plate(Vehicle.plate_number) == canon_plate,
        )
    )
    if existing_vehicle:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_PLATE",
            message=f"Biển số xe '{req.plate_number}' đã được đăng ký và đang hoạt động trên hệ thống.",
            details=[{
                "field": "plate_number",
                "message": f"Biển số '{req.plate_number}' đã thuộc về xe ID {existing_vehicle.id} của hộ ID {existing_vehicle.household_id}."
            }],
        )

    # 3. Tạo bản ghi Vehicle
    reg_date = req.registered_date or date.today()
    vehicle = Vehicle(
        household_id=req.household_id,
        plate_number=norm_plate,
        vehicle_type=req.vehicle_type.value if hasattr(req.vehicle_type, "value") else str(req.vehicle_type),
        brand=req.brand,
        color=req.color,
        status="ACTIVE",
        registered_date=reg_date,
    )
    db.add(vehicle)
    # [SỬA] Bọc flush() trong try/except IntegrityError để chống race condition trả về 500
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_PLATE",
            message=f"Biển số xe '{norm_plate}' đã được đăng ký và đang hoạt động trên hệ thống.",
            details=[{"field": "plate_number", "message": f"Biển số '{norm_plate}' bị trùng lặp."}],
        )

    # 4. Ghi nhận Audit Log (US-32, US-44)
    client_ip = sanitize_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")
    new_state: Dict[str, Any] = {
        "id": vehicle.id,
        "household_id": req.household_id,
        "household_code": household.household_code,
        "plate_number": vehicle.plate_number,
        "vehicle_type": vehicle.vehicle_type,
        "brand": vehicle.brand,
        "color": vehicle.color,
        "status": "ACTIVE",
        "registered_date": str(vehicle.registered_date),
    }

    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_VEHICLE",
        entity_type="VEHICLE",
        entity_id=str(vehicle.id),
        old_value=None,
        new_value=new_state,
        reason=f"Đăng ký phương tiện '{vehicle.vehicle_type}' biển số '{vehicle.plate_number}' cho hộ '{household.household_code}'.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(vehicle)

    return VehicleSchema.model_validate(vehicle)


@router.patch(
    "/{id:int}",
    response_model=VehicleSchema,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật phương tiện",
    description="Cập nhật thông tin phương tiện đã đăng ký (US-36). Chặn trùng biển số với xe ACTIVE khác. Phân quyền: ADMIN.",
    operation_id="updateVehicle",
)
def update_vehicle(
    id: int,
    req: VehicleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> VehicleSchema:
    """Cập nhật thông tin phương tiện (US-36)."""
    vehicle = db.get(Vehicle, id)
    if not vehicle:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy phương tiện với ID {id}."
        )

    old_state: Dict[str, Any] = {
        "plate_number": vehicle.plate_number,
        "vehicle_type": vehicle.vehicle_type,
        "brand": vehicle.brand,
        "color": vehicle.color,
    }

    update_data = req.model_dump(exclude_unset=True)

    # 1. Kiểm tra trùng lặp nếu cập nhật biển số xe
    if "plate_number" in update_data and update_data["plate_number"] is not None:
        new_plate = update_data["plate_number"]
        norm_new_plate = "".join(new_plate.split()).upper()
        canon_new_plate = _canonical_plate(new_plate)
        canon_curr_plate = _canonical_plate(vehicle.plate_number)
        if canon_new_plate != canon_curr_plate:
            dup_vehicle = db.scalar(
                select(Vehicle).where(
                    Vehicle.id != vehicle.id,
                    Vehicle.status == "ACTIVE",
                    _sql_canonical_plate(Vehicle.plate_number) == canon_new_plate,
                )
            )
            if dup_vehicle:
                raise AppAPIException(
                    status_code=status.HTTP_409_CONFLICT,
                    code="DUPLICATE_PLATE",
                    message=f"Biển số xe '{norm_new_plate}' đã được đăng ký và đang hoạt động trên hệ thống.",
                    details=[{
                        "field": "plate_number",
                        "message": f"Biển số '{norm_new_plate}' đã thuộc về xe ID {dup_vehicle.id}."
                    }],
                )
        vehicle.plate_number = norm_new_plate

    # 2. Cập nhật các trường khác nếu có
    if "vehicle_type" in update_data and update_data["vehicle_type"] is not None:
        vt = update_data["vehicle_type"]
        vehicle.vehicle_type = vt.value if hasattr(vt, "value") else str(vt)

    if "brand" in update_data:
        vehicle.brand = update_data["brand"]

    if "color" in update_data:
        vehicle.color = update_data["color"]

    # [SỬA] Flush trước để bắt IntegrityError nếu 2 request cùng đổi sang 1 biển số đồng thời
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_PLATE",
            message=f"Biển số xe '{vehicle.plate_number}' đã được đăng ký và đang hoạt động trên hệ thống.",
            details=[{"field": "plate_number", "message": f"Biển số '{vehicle.plate_number}' bị trùng lặp."}],
        )

    # 3. Ghi nhận Audit Log
    client_ip = sanitize_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")
    new_state: Dict[str, Any] = {
        "plate_number": vehicle.plate_number,
        "vehicle_type": vehicle.vehicle_type,
        "brand": vehicle.brand,
        "color": vehicle.color,
    }

    audit = AuditLog(
        user_id=current_user.id,
        action="UPDATE_VEHICLE",
        entity_type="VEHICLE",
        entity_id=str(vehicle.id),
        old_value=old_state,
        new_value=new_state,
        reason=f"Cập nhật thông tin phương tiện ID {vehicle.id} (Biển số: {vehicle.plate_number}).",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(vehicle)

    return VehicleSchema.model_validate(vehicle)


@router.post(
    "/{id:int}/unregister",
    response_model=VehicleSchema,
    status_code=status.HTTP_200_OK,
    summary="Hủy đăng ký phương tiện",
    description="Hủy đăng ký gửi xe của hộ gia đình (US-36). Chuyển trạng thái sang INACTIVE. Trả về 409 ALREADY_INACTIVE nếu đã hủy trước đó. Phân quyền: ADMIN.",
    operation_id="unregisterVehicle",
)
def unregister_vehicle(
    id: int,
    request: Request,
    # [SỬA] Dùng Body(default=None) để chấp nhận cả request có body JSON lẫn request rỗng body
    req: Optional[VehicleUnregister] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> VehicleSchema:
    """Hủy đăng ký phương tiện (US-36)."""
    vehicle = db.get(Vehicle, id)
    if not vehicle:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy phương tiện với ID {id}."
        )

    # Chặn nếu đã bị hủy đăng ký trước đó -> 409 ALREADY_INACTIVE
    if vehicle.status == "INACTIVE":
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="ALREADY_INACTIVE",
            message=f"Phương tiện với ID {id} đã ở trạng thái ngừng gửi (INACTIVE).",
            details=[{"field": "status", "message": "Phương tiện đã được hủy đăng ký trước đó."}],
        )

    unreg_date = req.unregistered_date if (req and req.unregistered_date) else date.today()

    # [THÊM] Chặn ngày hủy đăng ký nhỏ hơn ngày đăng ký ban đầu (tránh lệch logic tính phí US-17)
    if unreg_date < vehicle.registered_date:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=f"Ngày hủy đăng ký ({unreg_date}) không được nhỏ hơn ngày đăng ký ({vehicle.registered_date}).",
            details=[{
                "field": "unregistered_date",
                "message": f"Ngày hủy phải lớn hơn hoặc bằng ngày đăng ký ({vehicle.registered_date}).",
            }],
        )

    old_status = vehicle.status
    vehicle.status = "INACTIVE"
    vehicle.unregistered_date = unreg_date

    # Ghi nhận Audit Log (AC-36.1, US-32)
    client_ip = sanitize_ip_address(request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="UNREGISTER_VEHICLE",
        entity_type="VEHICLE",
        entity_id=str(vehicle.id),
        old_value={"status": old_status, "unregistered_date": None},
        new_value={"status": "INACTIVE", "unregistered_date": str(vehicle.unregistered_date)},
        reason=f"Hủy đăng ký phương tiện ID {vehicle.id} (Biển số: {vehicle.plate_number}) của hộ ID {vehicle.household_id}.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(vehicle)

    return VehicleSchema.model_validate(vehicle)