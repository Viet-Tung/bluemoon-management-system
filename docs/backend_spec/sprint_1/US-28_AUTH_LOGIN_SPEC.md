# ĐẶC TẢ CHI TIẾT USER STORY: US-28 (ĐĂNG NHẬP & QUẢN LÝ PHIÊN)
> **Mã Story:** `US-28` | **Feature:** `F-08.1` Kiến trúc & Bảo mật | **WBS:** `2.1.2`  
> **Story Points:** `4 SP` | **Độ ưu tiên:** `Must (M)`  
> **Người thực hiện:** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Review):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-28-backend-auth-login`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.3), `docs/API_CONTRACT.md` (mục 2.1), `docs/openapi.yaml` (`/auth/login`, `/auth/logout`, `/auth/me`), `database/01_schema.sql` (bảng `users`, `roles`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As a** Người dùng hệ thống (Admin, Kế toán, Thủ quỹ, Cư dân),  
> **I want** đăng nhập an toàn bằng tên người dùng và mật khẩu, nhận phiên làm việc dạng JWT Token, và được bảo vệ tài khoản khỏi các cuộc tấn công dò quét brute-force,  
> **So that** tôi có thể truy cập đúng các chức năng tương ứng với vai trò của mình và giữ an toàn cho thông tin cá nhân.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-28.1` (Đăng nhập đúng & Cấp quyền chuẩn):**
  - Đăng nhập đúng thông tin tài khoản: Hệ thống cấp JWT Access Token có thời hạn 8 giờ (`28.800` giây), ký HS256 với đầy đủ claims (`sub`, `username`, `role`, `household_id`, `must_change_password`).
  - Phản hồi HTTP `200 OK` với thân JSON khớp schema `LoginResponse` theo `docs/openapi.yaml`.
  - Tự động cập nhật `last_login_at = now` và reset `failed_login_count = 0`, `locked_until = None`.
  - Tên đăng nhập **không phân biệt chữ hoa chữ thường** (`func.lower(User.username)`) và tự động loại bỏ khoảng trắng thừa đầu cuối.
* **`AC-28.2` (Khóa tài khoản tự động - Brute-force Protection):**
  - Nhập sai mật khẩu liên tiếp $\ge 5$ lần (`MAX_FAILED_LOGIN_ATTEMPTS`): Hệ thống tự động khóa tài khoản trong 15 phút (`ACCOUNT_LOCKOUT_MINUTES`), cập nhật `locked_until = now + 15m`.
  - Trả về mã lỗi HTTP `423 LOCKED` với Error Envelope:
    ```json
    {
      "code": "ACCOUNT_LOCKED",
      "message": "Tài khoản đã bị tạm khóa 15 phút do nhập sai mật khẩu 5 lần liên tiếp.",
      "details": []
    }
    ```
  - Trong thời gian bị khóa (`locked_until > now`), mọi yêu cầu đăng nhập tiếp theo đều bị chặn với HTTP `423 ACCOUNT_LOCKED` kể cả khi nhập đúng mật khẩu.
  - Khi thời gian khóa 15 phút đã trôi qua (`locked_until <= now`), hệ thống tự động gỡ khóa khi đăng nhập thành công.
* **Kiểm soát tài khoản vô hiệu hóa:**
  - Nếu tài khoản có `is_active = False` $\rightarrow$ Trả về HTTP `403 FORBIDDEN` với mã `ACCOUNT_DISABLED`.
* **Đăng xuất (`POST /auth/logout`):**
  - Yêu cầu Bearer Token hợp lệ $\rightarrow$ Trả về HTTP `204 No Content`.
* **Thông tin cá nhân (`GET /auth/me`):**
  - Yêu cầu Bearer Token hợp lệ $\rightarrow$ Trả về HTTP `200 OK` chứa thông tin Profile người dùng và cấu trúc Role lồng nhau.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT CHI TIẾT (TECHNICAL BLUEPRINT)

Trong phạm vi của `US-28`, các tệp tin sau được triển khai và cấu hình:

```text
backend/app/
├── main.py                  # Đăng ký auth_router tại tiền tố /api/v1/auth
├── routers/
│   ├── __init__.py          # Export auth_router
│   └── auth.py              # Hiện thực POST /login, POST /logout, GET /me
└── schemas/
    ├── __init__.py          # Export LoginRequest, LoginResponse, RoleResponse, UserResponse
    └── auth.py              # Pydantic v2 schemas chuẩn OpenAPI 3.0.3
backend/tests/
└── test_us28_auth.py        # 114 Black-box test cases độc lập
```

---

## 3. CHI TIẾT CÁC ENDPOINTS VÀ LOGIC NGHIỆP VỤ

### 3.1. `POST /api/v1/auth/login` (Public)
* **Request Body:**
  ```json
  {
    "username": "admin_test",
    "password": "AdminPass123!"
  }
  ```
* **Quy trình xử lý nghiệp vụ:**
  1. Chuẩn hóa tên đăng nhập: `username = req.username.strip().lower()`.
  2. Truy vấn người dùng theo `lower(username)`:
     - Nếu không tìm thấy: Ném HTTP `401 UNAUTHENTICATED` với `code: "INVALID_CREDENTIALS"` (thông điệp chung chống rà quét user).
  3. Kiểm tra trạng thái khóa (`locked_until`):
     - Nếu `locked_until > now`: Ném HTTP `423 LOCKED` với `code: "ACCOUNT_LOCKED"`.
     - Nếu `locked_until <= now` (hết hạn khóa): Tự động reset `locked_until = None`, `failed_login_count = 0`.
  4. Kiểm tra trạng thái hoạt động:
     - Nếu `not user.is_active`: Ném HTTP `403 FORBIDDEN` với `code: "ACCOUNT_DISABLED"`.
  5. Xác thực mật khẩu qua `verify_password(req.password, user.password_hash)`:
     - **Nếu sai:**
       * Tăng `user.failed_login_count += 1`.
       * Nếu `failed_login_count >= 5`: Gán `user.locked_until = now + timedelta(minutes=15)` $\rightarrow$ Ném HTTP `423 ACCOUNT_LOCKED`.
       * Nếu $< 5$: Ném HTTP `401 INVALID_CREDENTIALS` kèm số lần thử còn lại (`5 - failed_login_count`).
     - **Nếu đúng:**
       * Reset `user.failed_login_count = 0`, `user.locked_until = None`.
       * Cập nhật `user.last_login_at = now`.
       * Sinh JWT Access Token có hạn 480 phút (8 tiếng).
       * Trả về HTTP `200 OK` kèm `LoginResponse`.

### 3.2. `POST /api/v1/auth/logout` (Yêu cầu Token)
* **Headers:** `Authorization: Bearer <token>`
* **Xử lý:** Dependency `get_current_user` xác thực token hợp lệ và tài khoản đang hoạt động.
* **Response:** HTTP `204 No Content`.

### 3.3. `GET /api/v1/auth/me` (Yêu cầu Token)
* **Headers:** `Authorization: Bearer <token>`
* **Response:** HTTP `200 OK` khớp `UserResponse`:
  ```json
  {
    "id": 1,
    "username": "admin_test",
    "full_name": "Quản Trị Viên Test",
    "email": "admin@bluemoon.local",
    "phone": null,
    "role": {
      "id": 1,
      "code": "ADMIN",
      "name": "Ban quản trị",
      "description": null
    },
    "household_id": null,
    "is_active": true,
    "must_change_password": false,
    "locked_until": null,
    "last_login_at": "2026-11-03T16:20:00Z"
  }
  ```

---

## 4. CHIẾN LƯỢC KIỂM THỬ HỘP ĐEN (BLACK-BOX TEST PLAN)

Dự án áp dụng phương pháp Black-Box Testing toàn diện: không đọc mã nguồn bên trong, chỉ kiểm thử dựa trên hợp đồng I/O và các tình huống biên cực đoan.

Bộ kiểm thử được phân bố thành **114 test cases** độc lập tại `backend/tests/test_us28_auth.py`:
1. **Happy Paths (4 tests):** Xác thực thành công cho cả 4 vai trò (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`).
2. **Case-Insensitive & Whitespace (15 tests):** Viết hoa, viết thường, xen kẽ, khoảng trắng đầu/cuối, tab, newline.
3. **Sai thông tin & Chống rà quét (20 tests):** Sai mật khẩu, tài khoản không tồn tại.
4. **Bảo mật trước Injection (15 tests):** SQL Injection (`' OR '1'='1`), XSS (`<script>`), SSTI (`{{7*7}}`), Log4j (`${jndi:...}`), Unicode lạ, null byte `\x00`.
5. **Dữ liệu đầu vào không hợp lệ (16 tests):** Thiếu trường, kiểu sai (int, float, bool, list, dict), chuỗi 10.000 ký tự $\rightarrow$ HTTP 400 `VALIDATION_ERROR`.
6. **Khóa tài khoản 15 phút - AC-28.2 (12 tests):** Chuỗi 5 lần sai, cố đăng nhập khi đang khóa, tự động mở sau thời hạn, reset bộ đếm khi đăng nhập đúng.
7. **Tài khoản vô hiệu hóa (4 tests):** `is_active = False` $\rightarrow$ HTTP 403 `ACCOUNT_DISABLED`.
8. **Đăng xuất an toàn (17 tests):** Thành công với token, gọi lặp lại (idempotent), thiếu/sai header $\rightarrow$ 401.
9. **Thông tin cá nhân (15 tests):** Lấy profile từng role, token sai/hỏng/hết hạn $\rightarrow$ 401.
