# ĐẶC TẢ CHI TIẾT USER STORY: US-45 (SAO LƯU & PHỤC HỒI CSDL)
> **Mã Story:** `US-45` | **Feature:** `F-08.2` Sao lưu & Phục hồi | **WBS:** `2.1.1`  
> **Story Points:** `3 SP` | **Độ ưu tiên:** `Should (S)`  
> **Người thực hiện:** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Review):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-45-backend-system-backups`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.1, WBS 2.1.1), `docs/API_CONTRACT.md` (Chương 3.3.2, 3.3.3), `docs/openapi.yaml` (path `/system/backups`), `database/01_schema.sql` (bảng `backup_jobs`, `users`, `audit_logs`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As an** Quản trị viên hệ thống (Admin / Ban Quản Trị),  
> **I want** hệ thống hỗ trợ sao lưu dữ liệu CSDL (tự động theo lịch và kích hoạt thủ công chạy nền) kèm theo dõi lịch sử sao lưu,  
> **So that** phòng ngừa rủi ro mất mát dữ liệu tài chính, đảm bảo tính liên tục vận hành và thời gian phục hồi nhanh chóng khi xảy ra sự cố.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-45.1` (Lập lịch tự động sao lưu CSDL lúc 02:00 sáng, RTO $\le 2\text{h}$, lưu 30 ngày):**
  - **Lập lịch tự động hàng ngày:** Tiến trình cronjob tự động chạy vào lúc **02:00 sáng** hàng ngày (biểu thức cron: `0 2 * * *`). Bản ghi sao lưu tự động có trường `requested_by = NULL` (theo chú thích chuẩn tại `database/01_schema.sql`).
  - **Chính sách lưu trữ (Retention Policy):** Hệ thống duy trì các bản sao lưu trong vòng **30 ngày**. Các bản sao lưu quá 30 ngày tự động được dọn dẹp để tối ưu dung lượng lưu trữ.
  - **Mục tiêu thời gian phục hồi (RTO):** Quy trình phục hồi CSDL đảm bảo hoàn thành trong thời gian $\le 2$ giờ (`NFR-002`).
  - **Kích hoạt sao lưu thủ công (`POST /system/backups`):**
    * Cho phép Quản trị viên (`ADMIN`) chủ động yêu cầu sao lưu CSDL bất kỳ lúc nào.
    * Phản hồi bất đồng bộ mã HTTP **`202 Accepted`** kèm thông tin tác vụ `BackupJob` (`status = "QUEUED"`), tiến trình sao lưu được đưa vào hàng đợi xử lý nền.
    * Ghi nhận đầy đủ thông tin kiểm toán vào bảng `audit_logs` (`action = "CREATE_BACKUP"`, `entity_type = "SYSTEM"`).
  - **Tra cứu lịch sử sao lưu (`GET /system/backups`):**
    * Chỉ cho phép vai trò **`ADMIN`** truy cập qua RBAC Guard (`require_roles("ADMIN")`).
    * Phân trang chuẩn theo `PageMeta`: `page` (mặc định 1, $\ge 1$) và `page_size` (mặc định 20, $1 \le \text{page\_size} \le 100$).
    * Danh sách trả về được sắp xếp giảm dần theo thời gian yêu cầu: `requested_at DESC, id DESC`.
    * Chặn các vai trò không có thẩm quyền (`ACCOUNTANT`, `TREASURER`, `RESIDENT`) với mã HTTP `403 FORBIDDEN`.
    * Chặn truy cập chưa xác thực với mã HTTP `401 UNAUTHENTICATED`.
    * Chặn người dùng chưa đổi mật khẩu lần đầu với mã HTTP `403 FORBIDDEN` kèm mã lỗi `PASSWORD_CHANGE_REQUIRED`.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── core/
│   ├── rbac_middleware.py       # RBAC Guard kiểm tra role ADMIN & PASSWORD_CHANGE_REQUIRED
│   └── database.py              # Phiên làm việc CSDL SQLAlchemy
├── models/
│   ├── base.py                  # DeclarativeBase & TimestampMixin
│   └── user.py                  # Khai báo model BackupJob, AuditLog, User, Role
├── routers/
│   ├── __init__.py              # Export system_router
│   └── system.py                # Endpoints: POST /system/backups, GET /system/backups
├── schemas/
│   ├── __init__.py              # Export BackupJob, BackupJobPage, BackupStatus
│   ├── common.py                # PageMeta, Error, ErrorDetail
│   └── system.py                # Schemas: BackupJob, BackupJobPage, BackupStatus
├── services/
│   └── backup_service.py        # Logic nghiệp vụ: tạo backup, cronjob 02:00 AM, dọn dẹp 30 ngày
└── main.py                      # Đăng ký system_router tại /api/v1/system và /system
backend/tests/
└── test_us45_system_backups.py  # Bộ kiểm thử tự động Black-box độc lập (>= 50 test cases)
```

---

## 3. CHI TIẾT ENDPOINTS VÀ LOGIC NGHIỆP VỤ

### 3.1. `POST /system/backups` — Kích hoạt sao lưu thủ công
* **Operation ID:** `createBackup`
* **Quyền gọi (RBAC):** `ADMIN`
* **Mã phản hồi:**
  - `202 Accepted`: Yêu cầu đã được tiếp nhận thành công, tiến trình sao lưu chạy nền. Body trả về đối tượng `BackupJob`:
    ```json
    {
      "id": 1,
      "status": "QUEUED",
      "requested_by": 1,
      "requested_at": "2026-11-05T05:00:00Z",
      "finished_at": null,
      "size_bytes": null
    }
    ```
  - `401 Unauthorized`: Thiếu token, token không hợp lệ hoặc đã hết hạn (`UNAUTHENTICATED`).
  - `403 Forbidden`: Sai vai trò (`FORBIDDEN`) hoặc tài khoản chưa đổi mật khẩu lần đầu (`PASSWORD_CHANGE_REQUIRED`).
* **Hành vi nghiệp vụ:**
  - Tạo bản ghi mới trong bảng `backup_jobs` với `status = "QUEUED"` và `requested_by = current_user.id`.
  - Tự động ghi nhận một dòng kiểm toán vào `audit_logs` với `action = "CREATE_BACKUP"`, `entity_type = "SYSTEM"`, `entity_id = str(job.id)`.

### 3.2. `GET /system/backups` — Truy xuất lịch sử sao lưu CSDL
* **Operation ID:** `listBackups`
* **Quyền gọi (RBAC):** `ADMIN`
* **Tham số Query:**
  - `page`: Số trang (mặc định 1, `ge=1`).
  - `page_size`: Kích thước trang (mặc định 20, `ge=1, le=100`).
  - `status`: (Tùy chọn) Lọc theo trạng thái (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`).
* **Mã phản hồi:**
  - `200 OK`: Trả về danh sách lịch sử sao lưu dạng `BackupJobPage`:
    ```json
    {
      "page": 1,
      "page_size": 20,
      "total": 1,
      "items": [
        {
          "id": 1,
          "status": "QUEUED",
          "requested_by": 1,
          "requested_at": "2026-11-05T05:00:00Z",
          "finished_at": null,
          "size_bytes": null
        }
      ]
    }
    ```
  - `400 Bad Request`: `page < 1` hoặc `page_size < 1` hoặc `page_size > 100` (`VALIDATION_ERROR`).
  - `401 Unauthorized`: Chưa đăng nhập hoặc token sai (`UNAUTHENTICATED`).
  - `403 Forbidden`: Sai vai trò hoặc chưa đổi mật khẩu lần đầu (`FORBIDDEN`, `PASSWORD_CHANGE_REQUIRED`).

---

## 4. QUY TRÌNH KIỂM THỬ BLACK-BOX & TIÊU CHUẨN DOD
- Bộ test black-box độc lập được thiết kế và thực thi trong môi trường SQLite in-memory `StaticPool`.
- Kiểm thử bao quát 100% các nhóm kịch bản:
  1. `Happy Paths`: Kích hoạt sao lưu thành công (202), tra cứu danh sách (200), phân trang chính xác, sắp xếp giảm dần theo thời gian.
  2. `RBAC & Authorization`: Chặn toàn bộ vai trò không có thẩm quyền, xử lý token hết hạn, token không hợp lệ, xử lý người dùng bị đánh dấu `must_change_password`.
  3. `Validation & Boundaries`: Xử lý giá trị phân trang không hợp lệ (`page=0`, `page=-1`, `page_size=0`, `page_size=101`), xử lý lọc theo trạng thái.
  4. `Automated Backup & Retention Logic (AC-45.1)`: Kiểm tra cấu hình cron 02:00 AM, kiểm tra tạo backup tự động (`requested_by = NULL`), kiểm tra dọn dẹp các bản ghi quá 30 ngày.
  5. `Audit Log Verification`: Đảm bảo mọi lượt kích hoạt sao lưu thủ công đều được ghi nhận vào `audit_logs` đầy đủ thông tin.

