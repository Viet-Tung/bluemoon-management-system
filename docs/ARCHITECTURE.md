# KIẾN TRÚC HỆ THỐNG & THIẾT KẾ CƠ SỞ DỮ LIỆU (BLUEMOON v1.0)

Tài liệu này giúp 5 thành viên hiểu thống nhất về cấu trúc kỹ thuật, quy tắc nghiệp vụ cốt lõi (Domain Rules) và sơ đồ bảng dữ liệu trước khi bắt đầu code.

---

## 1\. KIẾN TRÚC PHẦN MỀM (MODULAR MONOLITH)

Để đáp ứng yêu cầu `NFR-009` (dễ dàng mở rộng sang v2.0 cho Phí gửi xe `EP-06` và Điện nước `EP-07`) đồng thời phù hợp với quy mô nhóm 5 sinh viên làm việc trong 4 tháng, hệ thống sử dụng kiến trúc **Phân tầng theo Module (Modular Layered Architecture)**:

```
[ Trình duyệt Web (Chrome / Edge - NFR-006) ]
                     │
                     ▼ (HTTPS / RESTful JSON API)
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (SPA / Web UI)                   │
│  [Auth UI] [Household UI] [Billing UI] [Cashier] [Portal]   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                BACKEND APPLICATION SERVER                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Middleware: JWT Auth -> RBAC Guard -> Audit Logger    │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │
│  │ Module 1  │ │ Module 2  │ │ Module 3  │ │  Module 4   │  │
│  │ Auth/User │ │ Household │ │  Billing  │ │Report/Portal│  │
│  └───────────┘ └───────────┘ └───────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│        RELATIONAL DATABASE (ACID Transactions)              │
│     + Cronjob Sao lưu tự động 02:00 sáng (NFR-002)          │
└─────────────────────────────────────────────────────────────┘
```

&nbsp;

---

## 2\. CÁC QUY TẮC NGHIỆP VỤ CỐT LÕI (DOMAIN RULES BẮT BUỘC TUÂN THỦ)

Khi viết code ở Backend và Frontend, cả 5 thành viên phải tuân thủ nghiêm ngặt các quy tắc đã chốt trong sheet `Quyết định & Thuật ngữ`:

1. **Tách biệt `Căn hộ` (Apartment) và `Hộ gia đình` (Household) (`T-01`, `T-02`):**  
   - `apartments` lưu thông tin vật lý cố định của tòa nhà: Mã căn (VD: `B1204`), Tầng, Diện tích ($\text{m}^2$).  
   - `households` lưu hộ gia đình đang ở trong căn hộ đó. Khi đổi chủ/chuyển nhượng (`US-02`), ta đóng hồ sơ hộ cũ (`status = 'MOVED_OUT'`) và tạo `household` mới gắn vào `apartment_id` đó để lịch sử tài chính của hộ cũ không bị lẫn sang chủ mới.  
2. **Công thức tính phí kỳ thu mới (`US-17`, `AC-17.1`, `AC-19.5`):** $$\text{Tổng phải nộp kỳ này} = \sum (\text{Đơn giá khoản thu} \times \text{Hệ số diện tích hoặc Hộ} - \text{Miễn giảm}) + \text{Nợ cũ lũy kế} - \text{Số dư có (Credit Balance)}$$  
3. **Không xóa vật lý (No Hard Delete) với dữ liệu lịch sử:**  
   - Nhân khẩu chuyển đi/qua đời (`US-07`), Khoản thu đã phát sinh giao dịch (`AC-13.2`), Biên lai thu nhầm bị hủy (`US-22`) đều **chỉ được cập nhật cột `status`**, tuyệt đối không dùng lệnh `DELETE FROM`.  
4. **Đảm bảo tính toàn vẹn giao dịch (ACID Transaction \- `NFR-008`):**  
   - Khi Thủ quỹ bấm "Ghi nhận nộp tiền" (`US-19`), các bước: *(1) Tạo bản ghi biên lai $\rightarrow$ (2) Cập nhật số tiền đã nộp ở từng khoản nợ $\rightarrow$ (3) Cộng/trừ `credit_balance` của hộ* phải nằm trong cùng 1 Database Transaction.

---

## 3\. THIẾT KẾ CÁC BẢNG CƠ SỞ DỮ LIỆU CỐT LÕI

### 3.1. Nhóm bảng Người dùng & Nhật ký (Phụ trách: Thành viên 1\)

- **`users`**: `id`, `username` (UNIQUE), `password_hash`, `full_name`, `role` (`ADMIN`, `ACCOUNTANT`, `CASHIER`, `RESIDENT`), `household_id` (NULL cho nhân viên, FK cho cư dân), `must_change_password` (BOOLEAN), `failed_attempts` (INT), `locked_until` (TIMESTAMP), `status`.  
- **`audit_logs`**: `id`, `user_id`, `action`, `entity_name`, `entity_id`, `old_value` (JSON), `new_value` (JSON), `created_at`.

### 3.2. Nhóm bảng Căn hộ, Hộ & Nhân khẩu (Phụ trách: Vũ Trung Kiên \- TV2)

- **`apartments`**: `id`, `apartment_code` (UNIQUE, VD: `A0502`), `floor` (INT), `area_m2` (DECIMAL(6,2)), `status`.  
- **`households`**: `id`, `apartment_id` (FK), `household_code` (UNIQUE), `move_in_date`, `move_out_date`, `credit_balance` (DECIMAL(12,0) DEFAULT 0 \- *Lưu số dư có khi nộp thừa*), `status` (`ACTIVE`, `MOVED_OUT`).  
- **`residents`**: `id`, `household_id` (FK), `full_name`, `dob`, `gender`, `cccd` (NULLABLE cho trẻ $<14$ tuổi), `phone`, `relation_to_head` (`CHU_HO`, `VO_CHONG`, `CON`, `KHAC`), `residence_type` (`THUONG_TRU`, `TAM_TRU`), `status` (`ACTIVE`, `MOVED_OUT`, `DECEASED`).  
- **`temporary_records`**: `id`, `resident_id` (FK), `record_type` (`TAM_TRU`, `TAM_VANG`), `start_date`, `end_date`, `reason`, `status`.

### 3.3. Nhóm bảng Khoản thu & Kỳ thu (Phụ trách: Lê Trường Giang \- TV3)

- **`fee_types`**: `id`, `fee_code` (UNIQUE), `fee_name`, `calculation_method` (`PER_M2`, `FIXED_PER_HOUSEHOLD`, `VOLUNTARY`), `current_unit_price` (DECIMAL(12,0)), `is_mandatory` (BOOLEAN), `status`.  
- **`fee_price_histories`**: `id`, `fee_type_id` (FK), `unit_price`, `effective_from`, `effective_to`, `changed_by` (FK).  
- **`billing_periods`**: `id`, `period_code` (VD: `2026-11`), `month`, `year`, `due_date`, `status` (`OPEN`, `CLOSED`).  
- **`household_bills`** *(Chi tiết từng khoản phải nộp của từng hộ trong kỳ)*: `id`, `billing_period_id` (FK), `household_id` (FK), `fee_type_id` (FK), `unit_price_snapshot`, `quantity` (Diện tích $\text{m}^2$ hoặc $1$), `discount_amount`, `total_amount`, `paid_amount`, `status` (`UNPAID`, `PARTIAL`, `PAID`).

### 3.4. Nhóm bảng Biên lai & Quỹ tự nguyện (Phụ trách: Nguyễn Việt Tùng \- TV4)

- **`receipts`**: `id`, `receipt_number` (UNIQUE, VD: `BL-202611-0001`), `household_id` (FK), `billing_period_id` (FK), `cashier_id` (FK), `payment_method` (`CASH`, `BANK_TRANSFER`), `amount_received`, `overpaid_to_credit`, `print_count` (INT DEFAULT 1), `status` (`VALID`, `CANCELLED`), `cancel_reason`, `created_at`.  
- **`receipt_allocations`** *(Bảng trung gian gạch nợ cho từng khoản)*: `id`, `receipt_id` (FK), `household_bill_id` (FK), `allocated_amount`.  
- **`voluntary_campaigns`** & **`voluntary_donations`**: Lưu các đợt vận động quỹ tự nguyện và danh sách đóng góp của các hộ.

### 3.5. Nhóm bảng Cổng cư dân & Tìm kiếm (Phụ trách: Lê Nguyễn Nhật Huy \- TV5)

- **`edit_requests`**: `id`, `household_id` (FK), `requested_by` (FK), `request_content` (JSON/TEXT), `attachment_url`, `status` (`PENDING`, `APPROVED`, `REJECTED`), `reject_reason`, `reviewed_by` (FK), `reviewed_at`.  
- Đánh **Database Index** trên các cột: `apartments(apartment_code)`, `residents(full_name, cccd, phone)`, `receipts(receipt_number)` để đảm bảo tốc độ tìm kiếm $\le 1\text{s}$ (`NFR-005`).