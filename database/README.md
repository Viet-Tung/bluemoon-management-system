# 🗄️ Cơ Sở Dữ Liệu (Database) - Chung Cư BlueMoon

Thư mục này quản lý toàn bộ tài nguyên Cơ sở dữ liệu của dự án Chung Cư BlueMoon: kịch bản tạo bảng (`01_schema.sql`), dữ liệu mẫu (`seed_data`), và tài liệu hướng dẫn vận hành CSDL.

---

## 📖 1. Tài liệu đặc tả kỹ thuật chi tiết

Toàn bộ tài liệu giải thích chi tiết cấu trúc 28 bảng, quy tắc nghiệp vụ, ràng buộc toàn vẹn, hướng dẫn cho Frontend & Backend được lưu trữ tại:
👉 **[Tài liệu Đặc tả Cơ sở Dữ liệu BlueMoon (DATABASE_DESIGN.md)](../docs/DATABASE_DESIGN.md)**

---

## 🛠️ 2. Công nghệ & Yêu cầu môi trường

* **Hệ quản trị CSDL (DBMS):** **PostgreSQL 15+** (Khuyến nghị phiên bản 16).
* **Extensions bắt buộc:**
  * `btree_gist`: Hỗ trợ ràng buộc loại trừ thời gian (`EXCLUDE USING gist`) chống chồng chéo ngày cư trú và đơn giá.
  * `pg_trgm`: Tăng tốc độ tìm kiếm gần đúng theo họ tên cư dân $\le 1\text{s}$ (`NFR-005`, `US-23`).

---

## 📂 3. Cấu trúc thư mục `database/`

```text
database/
├── 01_schema.sql                    # Kịch bản DDL tạo toàn bộ 28 bảng, 5 view, triggers và seed metadata
├── 02_seed_initial_data.sql         # Dữ liệu tài khoản thử nghiệm và cấu hình phí mặc định
├── 03_seed_1000_households.py       # Script sinh dữ liệu kiểm thử 1.000 căn hộ & 5.000 nhân khẩu (NFR-005)
├── 04_backup_restore.sh             # Script cronjob sao lưu tự động hàng ngày lúc 02:00 sáng (US-45)
└── README.md                        # Hướng dẫn này
```

---

## 🚀 4. Hướng dẫn khởi tạo CSDL trên máy Local

### Bước 1: Tạo Database trong PostgreSQL
Mở terminal hoặc pgAdmin và chạy lệnh:
```sql
CREATE DATABASE bluemoon_db WITH OWNER postgres ENCODING 'UTF8';
```

### Bước 2: Chạy kịch bản khởi tạo bảng (Schema DDL)
Chạy trực tiếp file `01_schema.sql` vào database vừa tạo:
```bash
psql -U postgres -d bluemoon_db -f database/01_schema.sql
```

*Lưu ý:* File `01_schema.sql` đã tích hợp sẵn cơ chế **Idempotent** (`IF NOT EXISTS`, `DROP TRIGGER IF EXISTS`, `ON CONFLICT DO NOTHING`), an toàn khi chạy lại nhiều lần.
