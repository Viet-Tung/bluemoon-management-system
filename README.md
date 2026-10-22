# 🏢 Hệ Thống Quản Lý Cư Dân và Thu Phí Chung Cư BlueMoon

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg) ![Course](https://img.shields.io/badge/SoICT%2F_HUST-Intro_to_SE-red.svg) ![Team](https://img.shields.io/badge/Team-Nh%C3%B3m_18-success.svg)

> **Dự án môn học:** Nhập môn Công nghệ Phần mềm (Introduction to Software Engineering) \- Trường CNTT\&TT, Đại học Bách Khoa Hà Nội.  
> **Khách hàng mục tiêu:** Ban Quản Trị (BQT), Kế toán, Thủ quỹ và Cư dân tòa nhà chung cư BlueMoon (Quy mô \~1.000 căn hộ, \~5.000 nhân khẩu).

---

## 📖 1\. Giới thiệu bài toán

Hiện tại, Ban quản trị chung cư BlueMoon đang quản lý thông tin hộ khẩu, biến động nhân khẩu và thu phí hàng tháng bằng nhiều file Excel rời rạc và biên lai giấy. Việc này dẫn đến:

- Tốn nhiều thời gian nhân công thức tính phí theo diện tích ($\text{m}^2$) và tổng hợp công nợ.  
- Dễ xảy ra sai sót khi thu một phần, nộp thừa, hoặc đổi chủ căn hộ.  
- Khó tra cứu tức thì khi cư dân đến nộp phí hoặc khi Công an phường yêu cầu báo cáo cư trú.

**Phần mềm Quản lý Chung cư BlueMoon** được xây dựng nhằm số hóa 100% quy trình quản lý nhân khẩu, tự động hóa tính phí định kỳ, quản lý biên lai điện tử và cung cấp cổng tra cứu minh bạch cho cư dân.

---

## ✨ 2\. Các phân hệ chức năng chính (Phạm vi v1.0)

Hệ thống bao gồm **3 Module cốt lõi** (ánh xạ từ 8 Epics, 31 Features và 47 User Stories):

1. **🔐 Module Quản lý người dùng & Nền tảng (`EP-05`, `EP-08`):**  
   - Đăng nhập, bắt buộc đổi mật khẩu lần đầu, tự động khóa tạm thời 15 phút khi nhập sai 5 lần.  
   - Phân quyền theo vai trò (RBAC): `Trưởng BQT (Admin)`, `Kế toán`, `Thủ quỹ`, `Cư dân`.  
   - Ghi nhận nhật ký thao tác nhạy cảm (`Audit Log`) và tự động sao lưu CSDL hằng ngày lúc 02:00 sáng.  
2. **👨‍👩‍👧‍👦 Module Quản lý hộ gia đình & Cổng cư dân (`EP-01`, `EP-09`):**  
   - Quản lý tách biệt thực thể **Căn hộ** (diện tích, tầng) và **Hộ gia đình** (nhóm nhân khẩu đang cư trú) hỗ trợ nghiệp vụ chuyển nhượng căn hộ.  
   - Quản lý nhân khẩu, biến động (thêm mới sinh, chuyển đi, tách hộ) và cảnh báo Tạm trú/Tạm vắng sắp hết hạn trước 15 ngày.  
   - Import danh sách hộ từ Excel và xuất báo cáo cư trú theo mẫu Công an.  
   - Cổng thông tin cho Cư dân tự tra cứu thông tin hộ, lịch sử nộp phí và gửi đề nghị chỉnh sửa.  
3. **💰 Module Quản lý thu phí, Thống kê & Quỹ tự nguyện (`EP-02`, `EP-03`, `EP-04`, `EP-10`):**  
   - Cấu hình danh mục khoản thu (bắt buộc theo $\text{m}^2$, cố định theo hộ) và lưu vết lịch sử đơn giá.  
   - Khởi tạo kỳ thu tự động cho 1.000 hộ trong $\leq 10$ giây (tự động cộng nợ cũ và bù trừ số dư có).  
   - Ghi nhận thu tiền (tiền mặt/chuyển khoản), xử lý nộp một phần hoặc nộp dư, in biên lai điện tử (đóng dấu "BẢN SAO" khi in lại).  
   - Quản lý các đợt vận động đóng góp quỹ tự nguyện riêng biệt với công nợ bắt buộc.  
   - Tìm kiếm đa tiêu chí $\leq 1$ giây, Dashboard biểu đồ trực quan và xuất báo cáo Excel/PDF.

---

## 👥 3\. Đội ngũ phát triển (Nhóm 18\)

| STT | Thành viên | Vai trò dự án | Phân hệ phụ trách |
| :---: | :---- | :---- | :---- |
| 1 |  | Project Manager / Fullstack | `auth`, `users`, `audit-log`, `backup` (`EP-05`, `EP-08`) |
| 2 |  | Business Analyst / Backend | `apartments`, `households`, `residents` (`EP-01`) |
| 3 |  | WBS Architect / Backend Lead | `fee-types`, `billing-periods` (`EP-02`, `EP-03`) |
| 4 |  | Schedule Planner / Frontend Lead | `payments`, `receipts`, `voluntary-funds` (`EP-03`, `EP-10`) |
| 5 |  | Risk & QA Lead / Fullstack | `search`, `reports`, `resident-portal` (`EP-04`, `EP-09`) |

&nbsp;

---

## 📂 4\. Tài liệu dự án (Documentation)

Toàn bộ tài liệu đặc tả và kế hoạch dự án được lưu trữ trong thư mục [`/docs`](./docs) hoặc các file gốc dưới đây:

- 📋 [Product Backlog & Kế hoạch 4 Sprints](./PRODUCT_BACKLOG.md)  
- 🏗️ [Kiến trúc hệ thống & Thiết kế CSDL](./ARCHITECTURE.md)  
- 🤝 [Quy tắc làm việc nhóm & Quy trình Git (Contributing Guide)](./CONTRIBUTING.md)

---

## 🚀 5\. Hướng dẫn cài đặt và chạy dự án (Quick Start)

### Yêu cầu môi trường

- **Node.js** $\ge 18.\text{x}$ (hoặc Java JDK 17 / Python 3.10 tùy stack nhóm thống nhất)  
- **PostgreSQL / MySQL** $\geq 8.0$  
- **Git**

### Các bước chạy môi trường Local

```sh
# 1. Clone repository về máy
git clone https://github.com/<ten-tai-khoan>/bluemoon-apartment-management.git
cd bluemoon-apartment-management

# 2. Khởi tạo Cơ sở dữ liệu và nạp dữ liệu mẫu (1.000 căn hộ)
# Chạy file database/schema.sql và database/seed_1000_households.sql trong DBMS của bạn

# 3. Cài đặt và chạy Backend
cd backend
cp .env.example .env       # Cập nhật thông tin kết nối DB trong file .env
npm install
npm run dev

# 4. Cài đặt và chạy Frontend (Mở 1 terminal mới)
cd ../frontend
npm install
npm run dev
```

&nbsp;

### Tài khoản thử nghiệm mặc định (Sau khi chạy Seed Data)

| Vai trò | Tên đăng nhập | Mật khẩu mặc định | Quyền hạn chính |
| :---- | :---- | :---- | :---- |
| **Trưởng BQT (Admin)** | `admin_bqt` | `BlueMoon@2026` | Toàn quyền hệ thống, duyệt nhân khẩu, xem Dashboard |
| **Kế toán** | `ketoan_01` | `BlueMoon@2026` | Cấu hình khoản thu, tạo kỳ thu, nhập CK, xuất báo cáo |
| **Thủ quỹ** | `thuquy_01` | `BlueMoon@2026` | Thu tiền mặt tại quầy, in biên lai, thu quỹ tự nguyện |
| **Cư dân (Căn B1204)** | `cudan_B1204` | `BlueMoon@2026` | Xem thông tin hộ B1204, lịch sử đóng phí, gửi đề nghị sửa |

&nbsp;