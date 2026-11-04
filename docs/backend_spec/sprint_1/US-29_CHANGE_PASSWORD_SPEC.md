# ĐẶC TẢ CHI TIẾT USER STORY: US-29 (ĐỔI MẬT KHẨU CÁ NHÂN)
> **Mã Story:** `US-29` | **Feature:** `F-08.1` Kiến trúc & Bảo mật | **WBS:** `2.1.2`  
> **Story Points:** `2 SP` | **Độ ưu tiên:** `Must (M)`  
> **Người thực hiện:** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Review):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-29-backend-auth-change-password`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.3), `docs/API_CONTRACT.md` (mục 2.1), `docs/openapi.yaml` (`/auth/change-password`), `database/01_schema.sql` (bảng `users`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As a** Người dùng hệ thống (Admin, Kế toán, Thủ quỹ, Cư dân),  
> **I want** chủ động đổi mật khẩu tài khoản cá nhân của mình bằng cách nhập mật khẩu hiện tại và mật khẩu mới đạt chuẩn an toàn,  
> **So that** tôi bảo vệ an toàn tài khoản cá nhân, đặc biệt hoàn thành nghĩa vụ đổi mật khẩu tạm ngay trong lần đăng nhập đầu tiên.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-29.1` (Đổi mật khẩu an toàn & Bắt buộc lần đầu):**
  - **Quyền truy cập:** Dành cho tất cả người dùng đã xác thực (Bearer Token). Đặc biệt, cho phép thực thi thành công ngay cả khi tài khoản đang ở trạng thái `must_change_password = True` (hoặc `PASSWORD_CHANGE_REQUIRED`).
  - **Xác thực mật khẩu cũ:**
    * So khớp bằng thuật toán constant-time `verify_password`.
    * Nếu mật khẩu cũ không chính xác $\rightarrow$ Bắt buộc trả về HTTP `400 Bad Request` với mã lỗi `WRONG_OLD_PASSWORD` (tuyệt đối không dùng mã `401` để tránh client tự động logout người dùng).
  - **Chính sách mật khẩu mới:**
    * Mật khẩu mới bắt buộc thỏa mãn hàm `validate_password_strength`: độ dài tối thiểu $\ge 8$ ký tự, chứa ít nhất 1 chữ hoa, 1 chữ thường và 1 chữ số.
    * Nếu không thỏa mãn $\rightarrow$ Trả về HTTP `400 Bad Request` với mã `VALIDATION_ERROR` kèm chi tiết lỗi `details`.
  - **Cập nhật dữ liệu & Hoàn tất:**
    * Mật khẩu mới được băm bằng `get_password_hash` (`bcrypt` rounds $\ge 12$).
    * Cập nhật `user.password_hash = new_hash`.
    * Gỡ bỏ cờ bắt buộc đổi: `user.must_change_password = False`.
    * Ghi nhận thời điểm đổi: `user.password_changed_at = datetime.now(timezone.utc)`.
    * Phản hồi HTTP `204 No Content` khi thành công.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT CHI TIẾT (TECHNICAL BLUEPRINT)

Trong phạm vi của `US-29`, các tệp tin sau được triển khai và cấu hình:

```text
backend/app/
├── routers/
│   └── auth.py                  # Hiện thực endpoint POST /change-password
└── schemas/
    ├── __init__.py              # Export ChangePasswordRequest
    └── auth.py                  # Khai báo schema ChangePasswordRequest
backend/tests/
└── test_us29_change_password.py # Bộ kiểm thử black-box tự động (>= 50 test cases)
.github/
└── pull_request_template.md     # Template chuẩn hóa Pull Request cho dự án
```

---

## 3. CHI TIẾT ENDPOINT VÀ LOGIC NGHIỆP VỤ

### `POST /api/v1/auth/change-password` (Yêu cầu Token)
* **Header:** `Authorization: Bearer <access_token>`
* **Request Body (`ChangePasswordRequest`):**
  ```json
  {
    "old_password": "CurrentPass123!",
    "new_password": "NewStrongPass456#"
  }
  ```
* **Quy trình xử lý nghiệp vụ:**
  1. Xác thực người dùng hiện tại qua dependency `get_current_user` (kiểm tra token JWT, tính hợp lệ, trạng thái active).
  2. So khớp mật khẩu cũ `req.old_password` với `current_user.password_hash` bằng `verify_password`:
     - Nếu không khớp: Ném `AppAPIException(status_code=400, code="WRONG_OLD_PASSWORD", message="Mật khẩu cũ không chính xác.")`.
  3. Kiểm tra độ mạnh của `req.new_password` bằng `validate_password_strength`:
     - Nếu không hợp lệ: Ném `AppAPIException(status_code=400, code="VALIDATION_ERROR", message=error_msg, details=[...])`.
  4. Băm mật khẩu mới: `new_hash = get_password_hash(req.new_password)`.
  5. Cập nhật thực thể người dùng:
     - `current_user.password_hash = new_hash`
     - `current_user.must_change_password = False`
     - `current_user.password_changed_at = datetime.now(timezone.utc)`
  6. Commit transaction CSDL.
  7. Phản hồi HTTP `204 No Content`.

---

## 4. MA TRẬN PHẢN HỒI LỖI (ERROR CODE SPECIFICATION)

| HTTP Status | Mã lỗi (`code`) | Tình huống áp dụng | Schema chi tiết |
| :---: | :--- | :--- | :--- |
| **204** | *(None)* | Đổi mật khẩu thành công. | *(Thân rỗng)* |
| **400** | `WRONG_OLD_PASSWORD` | Mật khẩu cũ nhập không chính xác (tránh 401). | `Error` |
| **400** | `VALIDATION_ERROR` | Mật khẩu mới $< 8$ ký tự, thiếu hoa, thường, số, hoặc body rỗng. | `Error` (kèm `details`) |
| **401** | `UNAUTHENTICATED` | Thiếu token, token sai format, hết hạn, hoặc user inactive. | `Error` |
| **500** | `INTERNAL_SERVER_ERROR` | Lỗi máy chủ hoặc giao dịch CSDL không mong muốn. | `Error` |

---

## 5. MA TRẬN KIỂM THỬ TỰ ĐỘNG (TEST SUITE MATRIX)

Tệp kiểm thử `backend/tests/test_us29_change_password.py` bao phủ toàn diện:
1. **Happy Paths:** Đổi mật khẩu thành công cho mọi vai trò (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`).
2. **Cờ `must_change_password`:** Xác nhận tài khoản bị yêu cầu đổi mật khẩu có thể gọi API thành công và cờ được chuyển thành `False`.
3. **Mật khẩu cũ sai:** Kiểm tra trả về đúng HTTP 400 `WRONG_OLD_PASSWORD`, không kích hoạt lockout tài khoản.
4. **Mật khẩu mới không đạt chuẩn:** Kiểm tra tất cả các điều kiện vi phạm chính sách mật khẩu (độ dài, hoa, thường, số) trả về HTTP 400 `VALIDATION_ERROR`.
5. **Kiểm soát xác thực:** Không có token, token hỏng, token hết hạn, user bị vô hiệu hóa trả về HTTP 401 `UNAUTHENTICATED`.
6. **Toàn vẹn sau khi đổi:** Đăng nhập lại bằng mật khẩu mới thành công; mật khẩu cũ không còn đăng nhập được.

