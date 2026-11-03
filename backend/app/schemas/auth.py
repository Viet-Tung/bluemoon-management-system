from typing import Optional
from pydantic import BaseModel, ConfigDict


class TokenPayload(BaseModel):
    """Payload được mã hóa bên trong JWT Access Token."""
    model_config = ConfigDict(extra="ignore")

    sub: str
    username: str
    role: str
    household_id: Optional[int] = None
    must_change_password: bool = False
    exp: Optional[int] = None
    iat: Optional[int] = None
