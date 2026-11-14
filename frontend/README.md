# 🏢 BlueMoon Management System - Frontend Web Application

> **Dự án:** Phần mềm Quản lý Cư dân và Thu phí Chung cư BlueMoon (Quy mô ~1.000 căn hộ, ~5.000 nhân khẩu)  
> **Đơn vị thực hiện:** Nhóm 18 - CNTT&TT, ĐHBK Hà Nội (SoICT / HUST)  
> **Lập trình viên Front-End:** `TV3: Nguyễn Thanh Hải` & `TV4: Lê Nguyễn Nhật Huy`  
> **Tiêu chuẩn thiết kế:** Bộ quy chuẩn UI/UX từ `evondevKit / ui-ux`

---

## 🛠️ 1. Công nghệ sử dụng (Tech Stack)

* **Thư viện giao diện chính:** **React 19 + TypeScript**
* **Build tool & Dev Server:** **Vite 8** (Chạy tại port 3000, cấu hình proxy tự động `/api` sang Backend port 8000)
* **Styling & Design Tokens:** **Tailwind CSS v4** + Hệ thống Token chuẩn `evondev UI/UX` (BlueMoon Palette: `#1E40AF` Primary, Slate Neutrals, Semantic Badges)
* **Routing:** **React Router v7** (Cơ chế Role-Based Private Route)
* **Iconography:** **Lucide React** (Bộ biểu tượng hiện đại, đồng bộ)
* **Quản lý State & Toast:** React Context API (`AuthContext`, `ToastContext`)

---

## 🧭 2. Danh mục Phân hệ & Màn hình giao diện đã hoàn thiện (100% Khớp Backlog)

| Nhóm chức năng | Đường dẫn (Route) | User Story ánh xạ | Vai trò truy cập | Đặc tả tính năng chính |
| :--- | :--- | :--- | :--- | :--- |
| **Xác thực & Bảo mật** | `/login` | `US-28`, `US-44` | Mọi người dùng | Đăng nhập JWT, đếm sai 5 lần tự khóa 15m (`ACCOUNT_LOCKED`), phím tắt điền nhanh 4 vai trò demo |
| **Đổi mật khẩu** | Modal `/change-password` | `US-29`, `AC-29.1` | Mọi người dùng | Bắt buộc đổi lần đầu (`must_change_password`), kiểm tra độ mạnh $\ge 8$ ký tự, chữ hoa, thường, số |
| **Dashboard Điều hành** | `/dashboard` | `US-43`, `US-09` | Admin, Kế toán, Thủ quỹ | KPI tổng quan tài chính, biểu đồ tiến độ thu, cảnh báo tạm trú/vắng sắp hết hạn $\le 15$ ngày |
| **Căn hộ & Hộ gia đình** | `/apartments` | `US-01`, `US-03` | Admin, Kế toán | Danh sách 1.000 căn, lọc theo tầng, thêm căn hộ mới, chuyển nhượng căn hộ giữ nguyên lịch sử tài chính |
| **Nhân khẩu & Cư trú** | `/residents` | `US-05..US-10` | Admin, Kế toán | Thêm nhân khẩu vào hộ, miễn CCCD cho trẻ $< 14$ tuổi (`AC-05.3`), quản lý Thường trú/Tạm trú/Tạm vắng |
| **Quầy Thu Ngân** | `/cashier` | `US-18`, `US-19`, `US-20` | Thủ quỹ, Admin | Giao diện Split-Screen tìm kiếm $\le 1\text{s}$, gạch nợ từng phần, nộp thừa tự vào số dư có credit, in biên lai |
| **Biểu phí & Đơn giá** | `/fee-catalog` | `US-12, 13, 14, 15` | Kế toán, Admin | Khoản thu theo $m^2$, xe, công tơ; ngừng áp dụng No hard delete (`AC-13.1`), chính sách miễn giảm theo hộ |
| **Kỳ thu & Tính phí** | `/billing` | `US-17`, `US-47` | Kế toán, Admin | Khởi tạo kỳ thu mới, động cơ tính phí tự động 1.000 hộ trong $\le 10\text{s}$, xuất giấy báo nộp phí hàng loạt |
| **Theo dõi Công nợ** | `/debts` | `US-21`, `US-22` | Kế toán, Admin | Bảng theo dõi nợ theo kỳ, chức năng hủy biên lai sai sót (bắt buộc nhập lý do, hoàn trả nợ, ghi Audit Log) |
| **Quỹ Vận Động Tự Nguyện**| `/donations` | `US-40, 41, 42` | Thủ quỹ, Kế toán, Admin | Tạo đợt vận động (Vì người nghèo, Khuyến học), thu tiền in phiếu QT, bảo mật mức đóng, báo cáo mẫu Phường |
| **Cổng Cư Dân - Hồ sơ** | `/portal/household` | `US-33`, `US-34` | Cư dân (RESIDENT) | Tra cứu hồ sơ căn hộ, danh sách thành viên, gửi đề nghị sửa đổi thông tin đính kèm ảnh minh chứng |
| **Cổng Cư Dân - Tài chính**| `/portal/finances` | `US-35` | Cư dân (RESIDENT) | Tra cứu hóa đơn chi tiết từng khoản, số dư có hiện tại, lịch sử thanh toán và tải/in biên lai điện tử |
| **Duyệt Đề Nghị Cư Dân** | `/admin/change-requests`| `US-34` | Ban Quản Trị | Xem ảnh minh chứng, duyệt yêu cầu cập nhật DB tự động hoặc từ chối (bắt buộc nhập lý do - `AC-34.3`) |
| **Quản trị Tài khoản** | `/admin/users` | `US-30`, `US-31` | Ban Quản Trị | Danh sách tài khoản nhân sự/cư dân, khóa/mở khóa tức thì, phân 4 quyền RBAC chuẩn |
| **Nhật ký Audit Log** | `/admin/audit-logs` | `US-32` | Ban Quản Trị | Xem lịch sử kiểm toán bất biến (Người dùng, hành động, thời gian, IP, xem chi tiết JSON Old/New) |
| **Sao Lưu CSDL** | `/admin/backups` | `US-45` | Ban Quản Trị | Lịch sao lưu tự động 02:00 sáng hàng ngày (30 ngày, RTO $\le 2\text{h}$), kích hoạt sao lưu thủ công |

---

## 🎨 3. Mẫu Biên Lai Điện Tử Chuẩn (`DOC-02` - US-20)

Hệ thống tích hợp sẵn component in ấn [WatermarkReceipt.tsx](src/components/common/WatermarkReceipt.tsx):
- Sinh mã biên lai tự tăng duy nhất dạng `BL00000001`.
- Khi in lại từ lần thứ 2 trở đi (`print_count > 1`): **Tự động đóng dấu chéo chữ mờ "BẢN SAO"** theo tiêu chuẩn kế toán (`AC-20.2`).
- Khi giao dịch bị hủy (`status === 'CANCELLED'`): **Đóng dấu chữ đỏ "ĐÃ HỦY GIAO DỊCH"** kèm hiển thị lý do hủy (`AC-22.1`).

---

## 🚀 4. Hướng dẫn khởi chạy ứng dụng

```bash
# 1. Di chuyển vào thư mục frontend
cd frontend

# 2. Cài đặt các gói phụ thuộc (nếu chưa cài)
npm install

# 3. Chạy môi trường phát triển (Development Server)
npm run dev
```

Truy cập ứng dụng tại: **`http://localhost:3000`**

### Tài khoản thử nghiệm mặc định (Có sẵn nút bấm chuyển nhanh trên Header):
- **Trưởng BQT (Admin):** `admin_bqt` / `BlueMoon@2026`
- **Kế toán:** `ketoan_01` / `BlueMoon@2026`
- **Thủ quỹ:** `thuquy_01` / `BlueMoon@2026`
- **Cư dân (Căn B1204):** `cudan_b1204` / `BlueMoon@2026`
