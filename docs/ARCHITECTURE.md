# KIẾN TRÚC HỆ THỐNG & THIẾT KẾ CƠ SỞ DỮ LIỆU (BLUEMOON v1.0)

Tài liệu này giúp 5 thành viên hiểu thống nhất về cấu trúc kỹ thuật, quy tắc nghiệp vụ cốt lõi (Domain Rules) và sơ đồ bảng dữ liệu trước khi bắt đầu code.

---

## 1. KIẾN TRÚC PHẦN MỀM (MODULAR MONOLITH)

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

---

## 2. CÁC QUY TẮC NGHIỆP VỤ CỐT LÕI (DOMAIN RULES BẮT BUỘC TUÂN THỦ)

Khi viết code ở Backend và Frontend, cả 5 thành viên phải tuân thủ nghiêm ngặt các quy tắc đã chốt trong sheet `Quyết định & Thuật ngữ`:

1. **Tách biệt `Căn hộ` (Apartment) và `Hộ gia đình` (Household) (`T-01`, `T-02`):**  
   - `apartments` lưu thông tin vật lý cố định của tòa nhà: Mã căn (VD: `B1204`), Tầng, Diện tích ($\text{m}^2$).  
   - `households` lưu hộ gia đình đang ở trong căn hộ đó. Khi đổi chủ/chuyển nhượng (`US-02`), ta đóng hồ sơ hộ cũ (`status = 'MOVED_OUT'`) và tạo `household` mới gắn vào `apartment_id` đó để lịch sử tài chính của hộ cũ không bị lẫn sang chủ mới.  
2. **Công thức tính phí kỳ thu mới (`US-17`, `AC-17.1`, `AC-19.5`):** $$\text{Tổng phải nộp kỳ này} = \sum (\text{Đơn giá khoản thu} \times \text{Hệ số diện tích hoặc Hộ} - \text{Miễn giảm}) + \text{Nợ cũ lũy kế} - \text{Số dư có (Credit Balance)}$$  
3. **Không xóa vật lý (No Hard Delete) với dữ liệu lịch sử:**  
   - Nhân khẩu chuyển đi/qua đời (`US-07`), Khoản thu đã phát sinh giao dịch (`AC-13.2`), Biên lai thu nhầm bị hủy (`US-22`) đều **chỉ được cập nhật cột `status`**, tuyệt đối không dùng lệnh `DELETE FROM`.  
4. **Đảm bảo tính toàn vẹn giao dịch (ACID Transaction - `NFR-008`):**  
   - Khi Thủ quỹ bấm "Ghi nhận nộp tiền" (`US-19`), các bước: *(1) Tạo bản ghi biên lai $\rightarrow$ (2) Cập nhật số tiền đã nộp ở từng khoản nợ $\rightarrow$ (3) Cộng/trừ `credit_balance` của hộ* phải nằm trong cùng 1 Database Transaction.

---

## 3. THIẾT KẾ CƠ SỞ DỮ LIỆU CHUẨN (28 BẢNG - KHỚP 01_SCHEMA.SQL)

Toàn bộ lược đồ CSDL PostgreSQL chi tiết 28 bảng, các ràng buộc toàn vẹn, views, triggers và dữ liệu mẫu đã được thống nhất tại:
👉 **[Tài liệu Đặc tả Cơ sở Dữ liệu BlueMoon (DATABASE_DESIGN.md)](DATABASE_DESIGN.md)** và mã nguồn DDL tại [database/01_schema.sql](../database/01_schema.sql).

### 3.1. Phân nhóm 28 bảng theo Module nghiệp vụ

1. **Phân hệ Quản trị nền tảng & Bảo mật (5 bảng):**  
   - `roles`: 4 vai trò chuẩn (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`).  
   - `users`: Định danh người dùng, mật khẩu băm bcrypt, khóa 15 phút khi sai 5 lần.  
   - `audit_logs`: Nhật ký bất biến lưu vết các thao tác sửa/hủy nhạy cảm.  
   - `backup_jobs`: Quản lý nhật ký sao lưu CSDL tự động 02:00 sáng và thủ công (`US-45`).  
   - `document_counters`: Bộ đếm sinh số chứng từ tự tăng (`receipt_no`, `voucher_no`).

2. **Phân hệ Căn hộ, Cư trú & Cổng cư dân (9 bảng):**  
   - `apartments`: Căn hộ vật lý cố định (Mã căn, Tầng, Diện tích $\text{m}^2$).  
   - `households`: Hộ gia đình cư trú độc lập (chuyển nhượng không xóa căn hộ).  
   - `apartment_occupancies`: Lịch sử lưu trú/chuyển nhượng căn hộ theo thời gian.  
   - `residents`: Nhân khẩu chi tiết trong hộ (Họ tên, Ngày sinh, CCCD, Chủ hộ).  
   - `temporary_residences`: Hồ sơ tạm trú có thời hạn.  
   - `temporary_absences`: Hồ sơ tạm vắng của nhân khẩu thường trú.  
   - `residency_events`: Biến động cư trú dùng kết xuất báo cáo Công an (`DOC-03`).  
   - `profile_change_requests`: Đề nghị chỉnh sửa thông tin từ Cổng cư dân (`US-34`).  
   - `vehicles`: Phương tiện gửi xe (Ô tô, Xe máy) theo hộ.

3. **Phân hệ Biểu phí & Nhà cung cấp (4 bảng):**  
   - `service_providers`: Nhà cung cấp dịch vụ thu hộ (Điện, Nước, Rác).  
   - `fee_types`: Danh mục khoản thu bắt buộc (theo $\text{m}^2$, theo hộ).  
   - `fee_rates`: Lịch sử đơn giá từng khoản thu kèm ngày bắt đầu hiệu lực.  
   - `fee_exemptions`: Chính sách miễn giảm phí cho hộ chính sách/ưu tiên.

4. **Phân hệ Tính phí, Quầy thu tiền & Gạch nợ (8 bảng):**  
   - `billing_periods`: Kỳ tính phí hàng tháng (tháng, hạn nộp, trạng thái đóng/mở).  
   - `utility_readings`: Chỉ số tiêu thụ điện nước do nhà cung cấp gửi (`US-38`).  
   - `invoices`: Giấy báo nộp phí từng hộ trong kỳ (snapshot diện tích, nợ cũ, số dư có).  
   - `invoice_items`: Chi tiết từng dòng phí trong giấy báo nộp phí (`US-47`).  
   - `payments`: Biên lai điện tử nộp tiền (hỗ trợ `idempotency_key` chống bấm đúp).  
   - `payment_allocations`: Chi tiết gạch nợ từng dòng phí khi nộp một phần (`AC-19.2`).  
   - `household_credit_ledger`: Sổ cái theo dõi tiền thừa (số dư có) khi nộp thừa (`AC-19.5`).  
   - `provider_settlements`: Đối soát và nộp tiền thu hộ cho nhà cung cấp (`US-39`).

5. **Phân hệ Quỹ vận động tự nguyện (2 bảng):**  
   - `donation_campaigns`: Đợt vận động tự nguyện (Quỹ vì người nghèo, Khuyến học...).  
   - `donations`: Phiếu xác nhận đóng góp (tách biệt hoàn toàn khỏi công nợ bắt buộc).

### 3.2. Chỉ mục hiệu năng bắt buộc (Indexes $\le 1\text{s}$)
Bắt buộc có các chỉ mục B-tree và Trigram trong `01_schema.sql` để đáp ứng `NFR-005` và `US-23`:
* `idx_apartments_code` trên `apartments(code)`
* `idx_households_code` trên `households(household_code)`
* `idx_residents_name_trgm` dùng extension `pg_trgm` trên `residents(full_name)`
* `idx_residents_cccd` trên `residents(cccd)` (Partial Unique Index)
* `idx_payments_receipt_no` trên `payments(receipt_no)`
