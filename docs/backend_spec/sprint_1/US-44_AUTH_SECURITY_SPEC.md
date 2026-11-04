# ĐẶC TẢ CHI TIẾT USER STORY: US-44 (KIẾN TRÚC & BẢO MẬT API)
> **Mã Story:** `US-44` | **Feature:** `F-08.1` Kiến trúc & Bảo mật | **WBS:** `2.1.1`, `2.1.3`  
> **Story Points:** `5 SP` | **Độ ưu tiên:** `Must (M)`  
> **Người thực hiện:** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Review):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-44-backend-auth-security-architecture`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.3), `docs/API_CONTRACT.md` (mục 1.2, 1.3), `database/01_schema.sql` (bảng `roles`, `users`, `audit_logs`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As a** Ban quản trị (Admin),  
> **I want** mật khẩu người dùng được băm bảo mật (thuật toán `bcrypt`), các endpoint được bảo vệ bởi middleware phân quyền RBAC và chặn truy cập trái phép ở tầng API,  
> **So that** dữ liệu cá nhân cư dân và tài chính chung cư được an toàn tuyệt đối, chống lại các cuộc tấn công đánh cắp phiên và leo quyền trái phép (IDOR).

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-44.1` (Mật khẩu an toàn):** 
  - Mật khẩu lưu trong cơ sở dữ liệu bắt buộc phải băm bằng thuật toán `bcrypt` với chi phí tính toán (Work factor / Salt rounds) $\ge 12$.
  - Tuyệt đối không lưu mật khẩu dạng bản rõ (plaintext) ở bất kỳ log, cache, hay bảng dữ liệu nào (`NFR-001`).
* **`AC-44.2` (Chống lỗ hổng IDOR - Insecure Direct Object Reference):**
  - Tài khoản mang vai trò `RESIDENT` (Cư dân) chỉ được phép xem và thao tác trên đúng dữ liệu của hộ gia đình mình (`current_user.household_id`).
  - Khi Cư dân cố ý thay đổi ID hộ trên URL (ví dụ: `GET /households/99` trong khi hộ của mình là `101`), hệ thống **bắt buộc trả về HTTP `404 NOT_FOUND`** (không dùng 403 để ngăn kẻ tấn công rà quét sự tồn tại của các hộ khác).
  - Tự động ghi nhật ký vi phạm vào bảng `audit_logs` với action `ACCESS_DENIED`.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT CHI TIẾT (TECHNICAL BLUEPRINT)

Trong phạm vi của `US-44`, các tệp tin sau sẽ được khởi tạo tại thư mục `backend/app/`:

```text
backend/app/
├── main.py                  # Entrypoint: Khởi tạo FastAPI, CORS, Global Exception Handlers
├── core/
│   ├── config.py            # Cấu hình hệ thống (Settings: JWT, DB, Bcrypt, Lockout)
│   ├── database.py          # SQLAlchemy 2.0 Engine, SessionLocal, Dependency get_db (ACID rollback)
│   ├── security.py          # Hàm băm bcrypt (rounds=12), tạo/giải mã JWT token
│   └── rbac_middleware.py   # RBAC Guard, IDOR Guard, Check must_change_password
├── models/
│   ├── base.py              # DeclarativeBase, TimestampMixin (created_at, updated_at)
│   └── user.py              # SQLAlchemy ORM: Role, User, AuditLog
└── schemas/
    └── common.py            # Pydantic v2: Error, ErrorDetail, PageMeta (Khớp 100% openapi.yaml)
```

---

## 3. CHI TIẾT CÁC THÀNH PHẦN MÃ NGUỒN CẦN TRIỂN KHAI

### 3.1. `app/core/config.py` — Đọc cấu hình môi trường
* Đọc các biến từ môi trường (`.env`):
  - `APP_NAME`: `"BlueMoon Management System API"`
  - `DATABASE_URL`: Kết nối PostgreSQL (`postgresql+psycopg://postgres:postgres@localhost:5432/bluemoon_db`)
  - `JWT_SECRET`: Khóa bí mật ký token (tối thiểu 32 ký tự ngẫu nhiên).
  - `JWT_ALGORITHM`: Mặc định `"HS256"`.
  - `ACCESS_TOKEN_EXPIRE_MINUTES`: Mặc định `480` phút (8 tiếng).
  - `BCRYPT_ROUNDS`: Mặc định `12` (thỏa mãn `AC-44.1`).

### 3.2. `app/core/security.py` — Băm mật khẩu & Quản lý JWT Token
* **Hàm băm mật khẩu:**
  ```python
  import bcrypt

  def get_password_hash(password: str) -> str:
      """Băm mật khẩu bằng bcrypt với salt rounds = 12 (AC-44.1)."""
      salt = bcrypt.gensalt(rounds=12)
      return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

  def verify_password(plain_password: str, hashed_password: str) -> bool:
      """Xác thực mật khẩu người dùng nhập với hash trong CSDL."""
      return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
  ```
* **Hàm JWT Token:**
  - `create_access_token(data: dict, expires_delta: timedelta | None) -> str`: Tạo JWT mang payload:
    `{"sub": str(user.id), "username": user.username, "role": user.role.code, "household_id": user.household_id, "must_change_password": user.must_change_password, "exp": ...}`
  - `decode_access_token(token: str) -> dict`: Giải mã token, nếu hết hạn hoặc sai signature quăng ngoại lệ `401 UNAUTHENTICATED`.
* **Hàm kiểm tra độ mạnh mật khẩu (`AC-29.1`):**
  - Mật khẩu $\ge 8$ ký tự, có ít nhất: 1 chữ hoa, 1 chữ thường, 1 chữ số.

### 3.3. `app/core/rbac_middleware.py` — Phân quyền & Chống IDOR
* **Dependency `get_current_user`:**
  - Đọc header `Authorization: Bearer <token>`.
  - Giải mã token lấy `user_id`. Query `User` từ database kèm `role`.
  - Kiểm tra nếu `not user.is_active` $\rightarrow$ Ném ngoại lệ `401 UNAUTHENTICATED` (Tài khoản đã bị khóa).
* **Dependency Factory `require_roles(*allowed_roles: str)`:**
  - Kiểm tra `current_user.role.code in allowed_roles`.
  - Nếu vi phạm $\rightarrow$ Ném `403 FORBIDDEN`, ghi Audit Log hành động `ACCESS_DENIED`.
* **Hàm kiểm tra IDOR `check_household_access(target_household_id: int, current_user: User)`:**
  - Nếu `current_user.role.code == 'RESIDENT'`:
    * Kiểm tra: `if current_user.household_id != target_household_id:`
      - Ghi Audit Log: `action='ACCESS_DENIED'`, `reason='IDOR attempt on household ' + str(target_household_id)`.
      - **Ném HTTP `404 NOT_FOUND`** (đúng theo `AC-44.2`).
  - Nếu là nhân sự (`ADMIN`, `ACCOUNTANT`, `TREASURER`): Cho phép truy cập bình thường.
* **Hàm kiểm tra `check_password_change_required`:**
  - Nếu `current_user.must_change_password is True` và URL gọi tới không phải `/auth/change-password` hoặc `/auth/logout`:
    $\rightarrow$ Ném HTTP `403 PASSWORD_CHANGE_REQUIRED`.

### 3.4. `app/models/base.py` & `app/models/user.py` — ORM Cụm Identity
* Khai báo `Base(DeclarativeBase)` và `TimestampMixin`.
* Khai báo bảng `roles` (mapping cột `id`, `code`, `name`, `description`).
* Khai báo bảng `users` (mapping toàn bộ 15 cột, liên kết FK `role_id -> roles.id`, cột `household_id` lỏng lẻo).
* Khai báo bảng `audit_logs` (mapping toàn bộ 11 cột, lưu vết `old_value`, `new_value` dạng `JSONB`).

### 3.5. `app/schemas/common.py` — DTO Lỗi & Phân trang chuẩn hóa
* `Error`: Bắt buộc gồm 2 trường `code: str` và `message: str`, trường tùy chọn `details: list[ErrorDetail]`.
* `ErrorDetail`: Gồm `field: str | None`, `message: str`, `row: int | None`.
* `PageMeta`: Gồm `page: int`, `page_size: int`, `total: int`.

### 3.6. `app/main.py` — Khởi chạy ứng dụng & Bắt lỗi toàn cục
* Cấu hình CORS middleware với danh sách origins an toàn.
* Đăng ký Global Exception Handlers:
  - `HTTPException`: Trả về JSON chuẩn `Error(code=..., message=..., details=...)`.
  - `RequestValidationError` (Pydantic): Chuyển đổi toàn bộ lỗi validate của Pydantic về mã `400 VALIDATION_ERROR` kèm chi tiết field lỗi trong mảng `details`.
  - `Exception` (Unhandled): Bắt mọi lỗi 500 bất ngờ, log ra terminal và trả về `500 INTERNAL_SERVER_ERROR`.
* Endpoint kiểm tra sức khỏe: `GET /api/v1/health` $\rightarrow$ `{"status": "ok", "app": "BlueMoon Management System API"}`.

---

## 4. KỊCH BẢN KIỂM THỬ NGHIỆM THU (TEST PLAN CHO US-44)

Sau khi hoàn thành code, kỹ sư `TV1` tự kiểm thử (Self-test) và cung cấp bằng chứng cho `TV2` theo checklist:

1. **Test `AC-44.1` (Bcrypt Hash):**
   - Gọi hàm `get_password_hash("Admin@123")`.
   - Kết quả trả về chuỗi bắt đầu bằng `$2b$12$...` (xác nhận work factor = 12).
   - Thử xác thực với mật khẩu đúng $\rightarrow$ `True`; mật khẩu sai $\rightarrow$ `False`.
2. **Test `AC-44.2` (Chống IDOR):**
   - Tạo token giả lập Cư dân thuộc hộ `ID = 101`.
   - Gọi hàm `check_household_access(target_household_id=102, current_user=resident)`.
   - Xác nhận hệ thống bắn mã lỗi `404 NOT_FOUND` (không phải 403).
   - Kiểm tra bảng `audit_logs` có dòng ghi nhận `ACCESS_DENIED`.
3. **Test Format Lỗi (Error Envelope):**
   - Gửi request sai cú pháp lên server.
   - Xác nhận response body trả về đúng 100% định dạng JSON: `{"code": "VALIDATION_ERROR", "message": "...", "details": [...]}`.
4. **Test App Health:**
   - Khởi chạy server: `uvicorn app.main:app --port 8000`.
   - Gọi `GET /api/v1/health` $\rightarrow$ Nhận mã `200 OK`.

