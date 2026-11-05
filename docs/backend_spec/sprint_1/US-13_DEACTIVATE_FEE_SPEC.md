# ĐẶC TẢ CHI TIẾT USER STORY: US-13 (NGỪNG ÁP DỤNG KHOẢN THU)
> **Mã Story:** `US-13` | **Feature:** `F-03.1` Danh mục khoản thu | **WBS:** `2.3.2`  
> **Story Points:** `2 SP` | **Độ ưu tiên:** `Must (M)`  
> **Tác giả (Author):** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Reviewer):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-13-backend-deactivate-fee`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.2.3), `docs/API_CONTRACT.md` (mục 3.11.4), `docs/openapi.yaml` (path `/fee-types/{id}/deactivate`), `database/01_schema.sql` (bảng `fee_types`, `audit_logs`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As an** Kế toán (ACCOUNTANT) hoặc Ban Quản Trị (ADMIN),  
> **I want** ngừng áp dụng một khoản thu không còn sử dụng mà không làm mất lịch sử dữ liệu,  
> **So that** hệ thống loại trừ khoản thu khỏi danh sách áp biểu giá cho các kỳ hóa đơn tương lai trong khi vẫn bảo toàn 100% chứng từ, hóa đơn và lịch sử thu phí trong quá khứ.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-13.1` (Cấm xóa vật lý khoản thu; chỉ chuyển trạng thái sang `INACTIVE`):**
  - **Cơ chế chuyển trạng thái (`POST /fee-types/{id}/deactivate`):**
    + Chuyển trạng thái `status` của bản ghi trong bảng `fee_types` từ `ACTIVE` sang `INACTIVE`.
    + Tuyệt đối cấm xóa vật lý (No hard delete): Không sử dụng câu lệnh `DELETE FROM fee_types`, bảo đảm toàn vẹn khóa ngoại và liên kết dữ liệu với các hóa đơn, bảng kê lịch sử.
    + Phương thức `DELETE` trên tài nguyên `/fee-types/{id}` không được cung cấp và bị từ chối với HTTP `405 Method Not Allowed`.
  - **Tính bất biến & Toàn vẹn dữ liệu:**
    + Toàn bộ thông tin cấu hình gốc của khoản thu (`code`, `name`, `fee_group`, `calc_method`, `unit_label`, `vehicle_type`, `cycle`, `due_day`, `is_pass_through`, `description`, `created_at`) được giữ nguyên vẹn 100%.
    + Trường `updated_at` được tự động cập nhật phản ánh thời điểm ngừng áp dụng.
  - **Tính lũy đẳng (Idempotency):**
    + Khi gọi deactivate trên khoản thu đã ở trạng thái `INACTIVE`, hệ thống vẫn trả về HTTP `200 OK`, bảo toàn trạng thái `INACTIVE` và không phát sinh lỗi xung đột.
  - **Tác động đến bộ lọc danh mục:**
    + Khoản thu sau khi ngừng áp dụng không xuất hiện trong danh sách lọc `GET /fee-types?status=ACTIVE`.
    + Khoản thu xuất hiện đầy đủ trong danh sách lọc `GET /fee-types?status=INACTIVE` và danh sách tổng `GET /fee-types`.
    + Truy vấn chi tiết theo mã định danh `GET /fee-types/{id}` vẫn trả về bản ghi bình thường với `status="INACTIVE"`.
  - **Nhật ký kiểm toán (`AuditLog` - AC-32.1):**
    + Thao tác ngừng áp dụng được ghi vết tự động vào bảng `audit_logs` với `action="DEACTIVATE_FEE"`, `entity_type="FEE_TYPE"`, `entity_id=str(fee_type.id)`, `old_value={"status": old_status}`, `new_value={"status": "INACTIVE"}`, kèm `user_id`, `ip_address`, `user_agent`.
  - **Xử lý ngoại lệ & Phân quyền (RBAC Guard):**
    + Không tìm thấy ID bản ghi trả về HTTP `404 NOT_FOUND` (`code: NOT_FOUND`).
    + Tham số ID sai định dạng số trả về HTTP `400 VALIDATION_ERROR` hoặc `422`.
    + Chỉ cho phép vai trò `ADMIN` và `ACCOUNTANT`. Các vai trò khác (`TREASURER`, `RESIDENT`, vai trò không hợp lệ) bị chặn với HTTP `403 FORBIDDEN` (`code: FORBIDDEN`).
    + Thiếu token hoặc token không hợp lệ / hết hạn trả về HTTP `401 UNAUTHENTICATED` (`code: UNAUTHENTICATED`).
    + Tài khoản có cờ bắt buộc đổi mật khẩu (`must_change_password=True`) bị chặn với HTTP `403 PASSWORD_CHANGE_REQUIRED` (`code: PASSWORD_CHANGE_REQUIRED`).

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── models/
│   ├── __init__.py                  # Export FeeType model
│   └── fee.py                       # SQLAlchemy model FeeType (bảng fee_types)
├── schemas/
│   ├── __init__.py                  # Export Pydantic v2 schemas
│   └── fee.py                       # FeeType, FeeStatus, Enums
├── routers/
│   ├── __init__.py                  # Export fee_types_router
│   └── fee_types.py                 # Endpoint POST /fee-types/{id}/deactivate
backend/tests/
└── test_us13_deactivate_fee.py      # Bộ 70 test cases Black-box độc lập kiểm thử toàn diện US-13
```

---

## 3. CHI TIẾT HTTP REST ENDPOINT (STRICT API CONTRACT CONFORMANCE)

### 3.1. `POST /api/v1/fee-types/{id}/deactivate` (Ngừng áp dụng khoản thu)
* **Aliases:** Hỗ trợ cả `/fee-types/{id}/deactivate` và `/api/v1/fee-types/{id}/deactivate`.
* **Operation ID:** `deactivateFeeType`
* **Quyền gọi (Roles):** `ADMIN`, `ACCOUNTANT`
* **Path Parameter:**
  - `id`: int (Bắt buộc, kiểu int64, ID định danh khoản thu cần ngừng áp dụng)
* **Request Body:** Không yêu cầu body. Hỗ trợ bỏ trống hoặc gửi JSON `{}`.
* **Mã phản hồi HTTP:**
  - `200 OK`: Trả về schema `FeeType` với trường `status="INACTIVE"`.
  - `400 VALIDATION_ERROR`: Path parameter `id` sai kiểu dữ liệu (chuỗi ký tự, số thực...).
  - `401 UNAUTHENTICATED`: Thiếu header `Authorization`, token sai, bearer token rỗng hoặc token hết hạn.
  - `403 FORBIDDEN`: Gọi bởi tài khoản vai trò `TREASURER`, `RESIDENT` hoặc role không được cấp quyền.
  - `403 PASSWORD_CHANGE_REQUIRED`: Tài khoản chưa thực hiện đổi mật khẩu lần đầu (`must_change_password=True`).
  - `404 NOT_FOUND`: Không tìm thấy khoản thu với ID tương ứng.
  - `405 METHOD_NOT_ALLOWED`: Gọi bằng các HTTP method không được khai báo (`GET`, `PUT`, `PATCH`, `DELETE`).
  - `500 INTERNAL_SERVER_ERROR`: Lỗi hệ thống.

---

## 4. QUẢN LÝ DỮ LIỆU & TÍNH TOÀN VẸN GIAO DỊCH (ACID & INVARIANTS)

1. **Nguyên tắc Không xóa vật lý (No Hard Delete - AC-13.1):**
   - Không tồn tại thao tác xóa dòng trong cơ sở dữ liệu đối với bảng `fee_types`.
   - Trạng thái `INACTIVE` đóng vai trò cờ ngắt logic (soft-disable), bảo đảm tính toàn vẹn tham chiếu lịch sử tới các bảng hóa đơn, bảng kê chi tiết phát sinh trong các kỳ trước.
2. **Nguyên tử hóa & Nhật ký kiểm toán (ACID Transaction Integrity & Audit Trail):**
   - Việc cập nhật `status = 'INACTIVE'` và bản ghi `AuditLog` (`DEACTIVATE_FEE`) được đóng gói trong cùng một transaction cơ sở dữ liệu (`db.commit()`), bảo đảm đồng bộ hoàn toàn.
3. **Bảo toàn tính bất biến cấu hình (Configuration Immutability):**
   - Việc chuyển trạng thái không làm sai lệch bất kỳ thuộc tính nào của danh mục phí (`code`, `calc_method`, `unit_label`, `cycle`, `due_day`), bảo toàn tính nhất quán phục vụ kiểm toán tài chính.

---

## 5. MA TRẬN KẾT QUẢ KIỂM THỬ BLACK-BOX ĐỘC LẬP (TEST MATRIX)

Bộ kiểm thử được thiết kế độc lập bởi QA Engineer tại `backend/tests/test_us13_deactivate_fee.py`:

| Nhóm kịch bản kiểm thử | Số lượng test cases | Trạng thái thực thi |
| :--- | :---: | :---: |
| **Xác thực & Phân quyền RBAC Guard** (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`, Token hết hạn, `PASSWORD_CHANGE_REQUIRED`) | **14** | **PASSED (14/14)** |
| **Happy Path, Bất biến Nghiệp vụ & AC-13.1** (Chuyển `INACTIVE`, No Hard Delete, kiểm tra bất biến 10 thuộc tính, Idempotency) | **16** | **PASSED (16/16)** |
| **Bao quát các nhóm phí, chu kỳ & phương pháp tính** (Quản lý, xe máy/ô tô/xe đạp, điện/nước, thu hộ, theo hộ/người, chu kỳ tháng/quý/năm, biên `due_day`) | **14** | **PASSED (14/14)** |
| **Biên & Kiểm tra tham số Path Parameter** (`404 NOT_FOUND`, ID = 0, ID âm, ID số lớn, chuỗi chữ cái, số thực, ký tự đặc biệt, SQL injection safe) | **10** | **PASSED (10/10)** |
| **Chuẩn HTTP Protocol, Phương thức & Body** (Chặn `GET`, `PUT`, `DELETE`, `PATCH` $\rightarrow$ 405; Body rỗng, Body thừa trường, hỗ trợ cả 2 URL paths) | **8** | **PASSED (8/8)** |
| **Cách ly trạng thái & Tích hợp lọc danh mục** (Cách ly giữa các khoản thu, `GET /fee-types`, lọc `status=ACTIVE` loại trừ, lọc `status=INACTIVE` bao gồm, cấu trúc Error schema) | **8** | **PASSED (8/8)** |
| **TỔNG CỘNG** | **70** | **100% PASSED (70/70)** |
