from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import require_roles
from app.models.user import Role, User
from app.schemas.auth import RoleResponse

router = APIRouter(tags=["Users"])


@router.get(
    "",
    response_model=List[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Danh sách vai trò",
    description="Lấy danh sách các vai trò trong hệ thống (US-31). Phân quyền: ADMIN.",
)
def list_roles(
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> List[RoleResponse]:
    """Danh sách 4 vai trò chuẩn trong hệ thống (ADMIN, ACCOUNTANT, TREASURER, RESIDENT)."""
    roles = db.scalars(select(Role).order_by(Role.id.asc())).all()
    return [RoleResponse.model_validate(r) for r in roles]
