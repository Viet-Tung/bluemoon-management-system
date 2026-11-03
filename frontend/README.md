# 💻 Frontend Web Application - Chung Cư BlueMoon

Thư mục này chứa mã nguồn giao diện người dùng (Single Page Application - SPA) phục vụ Ban Quản Trị (Admin, Kế toán, Thủ quỹ) và Cổng thông tin Cư dân chung cư BlueMoon.

---

## 🛠️ 1. Công nghệ & Thư viện sử dụng (Tech Stack)

* **Framework UI:** **React 18+** kết hợp **Vite** (Khởi động nhanh, build tối ưu cho môi trường Web hiện đại).
* **Ngôn ngữ:** **TypeScript / JavaScript (ES2022+)**
* **Styling & UI Components:**
  * **Tailwind CSS v3**: Tiện ích utility-first CSS responsive trên Desktop & Tablet (`NFR-006`).
  * **Lucide React / Heroicons**: Bộ icon trực quan cho hệ thống bảng điều khiển và quầy thu ngân.
* **Giao tiếp API & Quản lý trạng thái:**
  * **Axios**: HTTP Client gọi RESTful API sang Backend (`http://localhost:8000/api/v1`), cấu hình sẵn Interceptor tự động gắn `Authorization: Bearer <token>` và xử lý lỗi tập trung.
  * **React Router v6**: Điều hướng trang, phân chia tuyến đường bảo vệ (Protected Routes) theo vai trò RBAC (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`).
* **Biểu đồ & Xuất báo cáo:**
  * **Chart.js / Recharts**: Trực quan hóa số liệu doanh thu, tỷ lệ nộp phí và cơ cấu dân cư trên Dashboard BQT (`US-43`).

---

## 📂 2. Cấu trúc thư mục `frontend/`

```text
frontend/
├── public/                          # Tài nguyên tĩnh (Logo, favicon, template Excel mẫu)
│   └── templates/                   # File mẫu nhập cư dân DOC-01
├── src/
│   ├── assets/                      # Hình ảnh, icons, styles dùng chung
│   ├── components/                  # Các UI Component tái sử dụng
│   │   ├── common/                  # Button, Modal, Table, Pagination, Badge, Alert
│   │   ├── layout/                  # Sidebar, Header, Navbar theo từng vai trò (RBAC)
│   │   └── forms/                   # Input, Select, DatePicker, FileUpload
│   │
│   ├── pages/                       # Các màn hình chức năng chính
│   │   ├── auth/                    # Login, Đổi mật khẩu lần đầu (US-28, US-29)
│   │   ├── dashboard/               # Dashboard điều hành BQT (US-43)
│   │   ├── apartments/              # Quản lý Căn hộ, Hộ gia đình, Import Excel (US-01..04)
│   │   ├── residents/               # Quản lý Nhân khẩu, Biến động, Tạm trú/vắng (US-05..11)
│   │   ├── billing/                 # Danh mục khoản thu, Đơn giá, Kỳ thu phí (US-12..17)
│   │   ├── cashier/                 # Quầy thu ngân, Gạch nợ, In/Hủy biên lai (US-18..22)
│   │   ├── donations/               # Quỹ vận động tự nguyện (US-40..42)
│   │   ├── reports/                 # Báo cáo doanh thu, công nợ, dân cư (US-24..27)
│   │   └── portal/                  # Cổng cư dân tra cứu hộ, nợ & gửi đề nghị (US-33..35)
│   │
│   ├── services/                    # Tầng gọi API qua Axios
│   │   ├── api.ts                   # Cấu hình Axios instance & JWT Interceptor
│   │   ├── authService.ts           # API Đăng nhập, đổi mật khẩu
│   │   ├── householdService.ts      # API Căn hộ, nhân khẩu
│   │   ├── billingService.ts        # API Khoản thu, kỳ thu, thu ngân
│   │   └── reportService.ts         # API Thống kê, báo cáo
│   │
│   ├── routes/                      # Cấu hình tuyến đường & Guard kiểm tra Role
│   │   ├── AppRoutes.tsx
│   │   └── ProtectedRoute.tsx
│   │
│   ├── App.tsx                      # Component gốc của ứng dụng
│   └── main.tsx                     # Điểm khởi chạy React DOM
│
├── package.json                     # Danh sách thư viện và scripts
├── tailwind.config.js               # Cấu hình màu sắc, theme Tailwind
├── vite.config.ts                   # Cấu hình Vite & Proxy API
└── README.md                        # Tài liệu hướng dẫn này
```

---

## 🚀 3. Hướng dẫn cài đặt và chạy Frontend

Mở Terminal tại thư mục `frontend/` và thực hiện:

```bash
# 1. Cài đặt các gói phụ thuộc (Dependencies)
npm install

# 2. Khởi chạy máy chủ phát triển (Development Server)
npm run dev
```

* Ứng dụng Frontend mặc định chạy tại: `http://localhost:3000` (hoặc `http://localhost:5173`).
* Đảm bảo Backend (`http://localhost:8000`) đã khởi chạy để các API hoạt động đồng bộ.
