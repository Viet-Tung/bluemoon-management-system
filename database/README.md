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

## 🚀 4. Hướng dẫn chạy PostgreSQL bằng Docker

Từ thư mục gốc dự án:

```bash
cp .env.example .env
# Cập nhật POSTGRES_DB, POSTGRES_USER và POSTGRES_PASSWORD trong .env

# Kiểm tra cấu hình Compose
docker compose config

# Tạo và khởi động PostgreSQL
docker compose up -d postgres

# Kiểm tra trạng thái và health check
docker compose ps
docker compose logs postgres
```

Container bind PostgreSQL tới `127.0.0.1:5432`, dùng named volume `postgres-data`, và mount `01_schema.sql` vào `/docker-entrypoint-initdb.d/` của official PostgreSQL image.

Lần khởi tạo volume đầu tiên, PostgreSQL sẽ tự:

1. Tạo database theo `POSTGRES_DB`.
2. Tạo user theo `POSTGRES_USER`.
3. Chạy `database/01_schema.sql` để tạo bảng, index, trigger, function, view và seed metadata.

Không cần chạy `psql -f database/01_schema.sql` thủ công sau lần khởi tạo đầu tiên. Khi container restart với cùng named volume, entrypoint không chạy lại file init.

Kiểm tra kết nối:

```bash
docker compose exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;"'
```

Nếu schema thay đổi sau lần khởi tạo đầu tiên, dùng migration hoặc kiểm tra/cập nhật bằng `psql` có kiểm soát. Không chạy lại toàn bộ `01_schema.sql` mặc định để tránh thay đổi ngoài ý muốn.

## 5. Sao lưu và phục hồi

Tạo backup và copy ra thư mục dự án:

```bash
docker compose exec postgres sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c -f /tmp/bluemoon.dump'
docker compose cp postgres:/tmp/bluemoon.dump ./bluemoon.dump
```

Khi thực hiện restore, copy backup vào container trước và dùng database mới hoặc database đã xác nhận backup:

```bash
docker compose cp ./bluemoon.dump postgres:/tmp/bluemoon.dump
docker compose exec postgres sh -lc 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/bluemoon.dump'
```

Không dùng `docker compose down -v`; thao tác đó xóa named volume `postgres-data` và toàn bộ dữ liệu PostgreSQL Docker.
