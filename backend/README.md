# ⚙️ Backend API Server - Chung Cư BlueMoon (Python FastAPI)

Thư mục này chứa toàn bộ mã nguồn xử lý nghiệp vụ (Business Logic), kết nối Cơ sở dữ liệu, phân quyền RBAC và cung cấp RESTful API cho giao diện Frontend.

---

## 🛠️ 1. Ngôn ngữ & Công nghệ sử dụng (Tech Stack)

* **Ngôn ngữ lập trình:** **Python 3.10+**
* **Web Framework:** **FastAPI** (Tốc độ cao, hỗ trợ bất đồng bộ, tự động sinh tài liệu **API Docs** tại đường dẫn `/docs` đúng theo yêu cầu bàn giao của đề bài).
* **ORM & Quản lý CSDL:** **SQLAlchemy 2.0** + **Alembic** (Quản lý phiên bản cấu trúc bảng).
* **Bảo mật & Xác thực (`NFR-001`, `EP-05`):**
  * `passlib[bcrypt]`: Băm mật khẩu người dùng bằng thuật toán `bcrypt`.
  * `python-jose[cryptography]`: Tạo và kiểm tra mã phiên đăng nhập `JWT Token`.
* **Xử lý Excel & In ấn PDF (`US-04`, `US-11`, `US-20`, `US-26`):**
  * `pandas` & `openpyxl`: Đọc file Excel khi Import danh sách hộ và xuất báo cáo thu phí/cư trú.
  * `reportlab` hoặc `weasyprint`: Xuất biên lai điện tử (`DOC-02`) và giấy báo phí ra định dạng PDF chuẩn tiếng Việt.

---

## 📂 2. Cấu trúc các file cần có trong thư mục `backend/`

Để 5 thành viên code song song mà không bị xung đột (Conflict), mỗi người chỉ viết code vào đúng file/thư mục phân hệ của mình:

```text
backend/
├── app/
│   ├── main.py                      # File khởi chạy ứng dụng FastAPI & cấu hình CORS
│   ├── core/                        # Cấu hình cốt lõi 
│   │   ├── config.py                # Đọc biến môi trường từ file .env (DB_URL, SECRET_KEY)
│   │   ├── database.py              # Kết nối CSDL PostgreSQL/MySQL & quản lý ACID Session
│   │   ├── security.py              # Hàm mã hóa bcrypt, tạo JWT, khóa tài khoản 15 phút (US-28)
│   │   └── rbac_middleware.py       # Kiểm tra quyền Admin/BQT/Kế toán/Thủ quỹ/Cư dân (US-31)
│   │
│   ├── models/                      # Định nghĩa các bảng CSDL (SQLAlchemy Models)
│   │   ├── user_model.py            # Bảng users, roles, audit_logs 
│   │   ├── household_model.py       # Bảng apartments, households, residents, temp_stays
│   │   ├── fee_model.py             # Bảng fee_categories, fee_rates, voluntary_campaigns 
│   │   ├── billing_model.py         # Bảng billing_periods, invoices, receipts
│   │   └── portal_model.py          # Bảng edit_requests
│   │
│   ├── schemas/                     # Kiểm tra dữ liệu đầu vào/đầu ra (Pydantic Schemas)
│   │   ├── auth_schema.py           # Kiểm tra form đăng nhập, đổi mật khẩu
│   │   ├── household_schema.py      # Kiểm tra diện tích > 0, CCCD 12 số hoặc trẻ < 14 tuổi
│   │   ├── fee_schema.py            # Kiểm tra đơn giá >= 0, ngày hiệu lực
│   │   ├── payment_schema.py        # Kiểm tra số tiền thu, hình thức Tiền mặt/Chuyển khoản
│   │   └── report_schema.py         # Chuẩn hóa dữ liệu trả về cho Dashboard & Báo cáo
│   │
│   ├── routers/                     # Nơi viết các API Endpoints (Chia đúng cho 5 thành viên)
│   │   ├── auth_router.py           # API Đăng nhập, Đổi MK, Quản lý User, Audit Log
│   │   ├── household_router.py      # API Căn hộ, Hộ, Nhân khẩu, Tạm trú, Import Excel
│   │   ├── fee_router.py            # API Danh mục khoản thu, Đơn giá, Quỹ tự nguyện
│   │   ├── billing_router.py        # API Tạo kỳ thu, Ghi nhận nộp tiền, In/Hủy biên lai
│   │   └── report_portal_router.py  # API Tìm kiếm <=1s, Thống kê, Dashboard, Cổng cư dân
│   │
│   └── utils/                       # Các hàm tiện ích dùng chung
│       ├── audit_logger.py          # Hàm ghi lịch sử thao tác bất biến vào bảng audit_logs (US-32)
│       ├── excel_handler.py         # Hàm đọc/xuất file Excel chuẩn biểu mẫu Công an (DOC-03)
│       ├── pdf_generator.py         # Hàm xuất Biên lai PDF (tự đóng dấu "BẢN SAO" khi in lần 2)
│       └── backup_cron.py           # Script tự động sao lưu CSDL lúc 02:00 sáng (US-45)
│
├── tests/                           # Chứa Unit Test kiểm thử các công thức tính phí
├── .env.example                     # File mẫu cấu hình môi trường
├── requirements.txt                 # Danh sách các thư viện Python cần cài đặt
└── README.md                        # Tài liệu hướng dẫn này
```

---

## 🚀 3. Hướng dẫn cài đặt và chạy Backend (Cho các thành viên)

Mở Terminal tại thư mục `backend/` và chạy lần lượt các lệnh sau:

```bash
# 1. Tạo môi trường ảo Python (Virtual Environment)
python -m venv venv

# 2. Kích hoạt môi trường ảo
# - Trên Windows:
venv\Scripts\activate
# - Trên macOS / Linux:
source venv/bin/activate

# 3. Cài đặt các thư viện cần thiết
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic passlib[bcrypt] python-jose[cryptography] pandas openpyxl reportlab python-multipart

# 4. Lưu danh sách thư viện vào file requirements.txt
pip freeze > requirements.txt

# 5. Chạy Server phát triển (Development Server)
uvicorn app.main:app --reload --port 8000
```

* Sau khi chạy thành công, mở trình duyệt truy cập:
  * **Trang API Docs tự động (Swagger UI):** `http://localhost:8000/docs` (Dùng để test trực tiếp mọi API mà chưa cần chờ Frontend).