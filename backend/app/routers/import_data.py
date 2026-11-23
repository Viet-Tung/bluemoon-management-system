from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.user import User
from app.schemas.import_data import ImportResult
from app.services.import_service import import_residents_excel

router = APIRouter(tags=["Import"])


@router.post(
    "/import/excel",
    response_model=ImportResult,
    status_code=status.HTTP_200_OK,
    summary="Import dữ liệu từ Excel",
    description="Nhập danh sách căn hộ, hộ gia đình và nhân khẩu hàng loạt từ file Excel mẫu DOC-01 (US-04). Chạy trong 1 giao dịch ACID: lỗi thì rollback toàn bộ và trả về 422 IMPORT_FAILED. Phân quyền: ADMIN.",
)
async def import_excel(
    request: Request,
    file: UploadFile = File(..., description="File Excel mẫu .xlsx"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> ImportResult:
    # 1. Kiểm tra đuôi file mở rộng
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Hệ thống chỉ chấp nhận định dạng file Excel (.xlsx).",
            details=[{"field": "file", "message": "File phải có định dạng .xlsx."}],
        )

    # 2. Đọc nội dung file
    file_bytes = await file.read()
    if not file_bytes:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Tệp tải lên rỗng, vui lòng kiểm tra lại nội dung file.",
            details=[{"field": "file", "message": "Kích thước tệp bằng 0 bytes."}],
        )

    # Giới hạn kích thước file tối đa 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    if len(file_bytes) > MAX_FILE_SIZE:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Kích thước tệp vượt quá giới hạn tối đa cho phép (10MB).",
            details=[{"field": "file", "message": f"Kích thước tệp ({len(file_bytes)} bytes) vượt quá 10MB."}],
        )

    # 3. Thực thi nghiệp vụ import và giao dịch ACID trong Service
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = import_residents_excel(
        file_bytes=file_bytes,
        db=db,
        current_user_id=current_user.id,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    return result
