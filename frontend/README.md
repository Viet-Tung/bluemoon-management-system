# 🗄️ Cơ Sở Dữ Liệu (Database) - Chung Cư BlueMoon

Thư mục này chứa toàn bộ các file kịch bản SQL (`schema.sql`), dữ liệu mẫu (`seed_data.sql`) và kịch bản sao lưu tự động (`backup.sh`) để đảm bảo tính toàn vẹn dữ liệu tài chính và cư trú của chung cư BlueMoon.

---

## 🛠️ 1. Ngôn ngữ & Hệ quản trị CSDL sử dụng

* **Ngôn ngữ truy vấn:** **SQL (Structured Query Language)**.
* **Hệ quản trị CSDL (DBMS):** **PostgreSQL 15+** (hoặc **MySQL 8.0+**).
  * *Lý do lựa chọn:* Hỗ trợ giao dịch **ACID** tuyệt đối (`NFR-008`), đảm bảo khi 20 người dùng truy cập đồng thời đầu tháng (`NFR-010`) không bao giờ xảy ra lỗi trừ tiền hai lần hoặc trùng số biên lai.
  * Hỗ trợ tìm kiếm tiếng Việt không phân biệt dấu cực nhanh ($\le 1\text{s}$ cho 5.000 nhân khẩu theo `NFR-005`) nhờ tiện ích `unaccent` (PostgreSQL) hoặc Collation `utf8mb4_0900_ai_ci` (MySQL).

---

## 📂 2. Danh sách các file cần có trong thư mục `database/`

```text
database/
├── 01_schema.sql                    # Lệnh CREATE TABLE cho toàn bộ 14 bảng + Khóa ngoại + Index
├── 02_seed_initial_data.sql         # Tạo sẵn 5 tài khoản mẫu (Admin, BQT, Kế toán, Thủ quỹ, Cư dân) & các khoản phí cơ bản
├── 03_seed_1000_households.py       # Script Python sinh tự động 1.000 căn hộ & 5.000 nhân khẩu để test hiệu năng (NFR-005)
├── 04_backup_restore.sh             # Script sao lưu CSDL tự động lúc 02:00 sáng và giữ trong 30 ngày (US-45, NFR-003)
├── erd_diagram.png                  # Ảnh sơ đồ thực thể liên kết (ERD) để chèn vào báo cáo kỹ thuật
└── README.md                        # Tài liệu hướng dẫn này
```

---

## 🧱 3. Danh sách 14 Bảng dữ liệu cốt lõi trong `01_schema.sql`

### Nhóm 1: Phân quyền & Nhật ký hệ thống 
1. **`roles`**: Danh mục 5 vai trò (`ADMIN`, `BQT`, `ACCOUNTANT`, `CASHIER`, `RESIDENT`).
2. **`users`**: Tài khoản đăng nhập (`id`, `username`, `password_hash`, `role_id`, `household_id`, `failed_attempts`, `locked_until`, `is_active`).
3. **`audit_logs`**: Nhật ký thao tác bất biến (`id`, `user_id`, `action`, `table_name`, `record_id`, `old_data`, `new_data`, `created_at`). *Lưu ý: Không cấp quyền `UPDATE/DELETE` trên bảng này (`AC-32.2`).*

### Nhóm 2: Căn hộ, Hộ cư trú & Nhân khẩu 
4. **`apartments`**: Đơn vị tài sản vật lý (`id`, `apartment_code` UNIQUE, `floor`, `area_m2` $> 0$, `address`, `status`).
5. **`households`**: Hộ gia đình đang cư trú tại căn hộ (`id`, `apartment_id`, `owner_name`, `phone`, `credit_balance` DEFAULT 0, `move_in_date`, `move_out_date`, `status`).
6. **`residents`**: Nhân khẩu trong hộ (`id`, `household_id`, `full_name`, `dob`, `gender`, `cccd` UNIQUE NULLABLE, `missing_cccd_reason`, `relation_to_owner`, `residency_type`, `is_active`).
7. **`resident_movements`**: Lịch sử biến động nhân khẩu (`id`, `resident_id`, `movement_type`: Chuyển đến / Chuyển đi / Sinh / Mất, `effective_date`, `note`).
8. **`temp_residencies`**: Hồ sơ Tạm trú / Tạm vắng (`id`, `resident_id`, `type`, `start_date`, `end_date`, `status`).

### Nhóm 3: Danh mục Khoản thu & Quỹ tự nguyện 
9. **`fee_categories`**: Danh mục khoản thu (`id`, `fee_code`, `fee_name`, `is_mandatory`, `calc_method`: `PER_M2` / `PER_PERSON` / `FIXED`, `billing_cycle`, `is_active`).
10. **`fee_rates`**: Lịch sử đơn giá (`id`, `fee_category_id`, `unit_price`, `effective_from`, `effective_to`).
11. **`household_discounts`**: Chính sách miễn giảm theo hộ (`id`, `household_id`, `fee_category_id`, `discount_percent`, `reason`, `valid_from`, `valid_to`).
12. **`voluntary_campaigns` & `voluntary_donations`**: Đợt vận động đóng góp tự nguyện và số tiền ủng hộ của từng hộ.

### Nhóm 4: Kỳ thu, Hóa đơn, Biên lai & Cổng cư dân 
13. **`billing_periods` & `invoices` & `invoice_items`**: Kỳ thu hàng tháng, tổng công nợ từng hộ (đã cộng nợ cũ và trừ `credit_balance`) và chi tiết từng dòng phí ($m^2 \times \text{đơn giá}$).
14. **`transactions`, `receipts` & `edit_requests`**: Giao dịch nộp tiền, biên lai điện tử (`receipt_no` UNIQUE tăng dần, `print_count`) và yêu cầu chỉnh sửa thông tin từ cư dân (`Chờ duyệt` / `Đã xử lý` / `Từ chối`).

---

## ⚡ 4. Các chỉ mục (Indexes) bắt buộc phải tạo để đạt hiệu năng $\le 1\text{s}$

Trong file `01_schema.sql`, bắt buộc phải có các dòng đánh Index sau để đáp ứng `US-18`, `US-23` và `NFR-005`:

```sql
-- Tăng tốc tìm kiếm căn hộ và chủ hộ tại quầy thu tiền (<= 1 giây)
CREATE UNIQUE INDEX idx_apartments_code ON apartments(apartment_code);
CREATE INDEX idx_households_owner ON households(owner_name);

-- Tăng tốc tìm kiếm nhân khẩu theo họ tên và CCCD
CREATE INDEX idx_residents_name ON residents(full_name);
CREATE UNIQUE INDEX idx_residents_cccd ON residents(cccd) WHERE cccd IS NOT NULL;

-- Tăng tốc thống kê công nợ theo kỳ thu và trạng thái thanh toán
CREATE INDEX idx_invoices_period_status ON invoices(billing_period_id, payment_status);
```