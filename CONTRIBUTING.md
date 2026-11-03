# HƯỚNG DẪN ĐÓNG GÓP CODE & QUY TRÌNH LÀM VIỆC NHÓM (NHÓM 18\)

Tài liệu này quy định cách 5 thành viên Nhóm 18 phối hợp làm việc trên GitHub để đảm bảo code sạch, không bị mất code của nhau và bám sát 100% Acceptance Criteria trong Product Backlog.

---

## 🌿 1\. Quy tắc phân nhánh (Git Branching Strategy)

Chúng ta sử dụng mô hình **Git Flow rút gọn** gồm 3 loại nhánh:

1. **`main`**: Nhánh chứa code ổn định nhất dùng để bàn giao tại các mốc **First UAT (30/11)**, **Second UAT (15/12)** và **Final Release (30/12)**. **TUYỆT ĐỐI KHÔNG** push trực tiếp lên `main`.  
2. **`develop`**: Nhánh tích hợp code chung của cả 5 thành viên trong suốt các Sprint.  
3. **Nhánh tính năng / sửa lỗi cá nhân**: Mỗi khi làm một User Story hoặc sửa lỗi, thành viên bắt buộc tạo nhánh mới từ `develop` theo cú pháp:  
   - Làm User Story mới: `feat/US-<mã-số>-<tên-ngắn-gọn>`  
     - *Ví dụ:* `feat/US-01-apartment-crud`, `feat/US-17-auto-billing`  
   - Sửa lỗi (Bug): `fix/US-<mã-số>-<mô-tả-lỗi>`  
     - *Ví dụ:* `fix/US-19-overpayment-balance`  
   - Cập nhật tài liệu: `docs/<tên-tài-liệu>`  
     - *Ví dụ:* `docs/update-wbs-gantt`

---

## 💬 2\. Quy chuẩn viết Commit Message

Mỗi commit cần ghi rõ mã User Story để dễ truy vết khi chấm điểm:

```
<loại>(US-xx): <mô tả ngắn gọn việc đã làm>
```

&nbsp;

- **`feat`**: Thêm tính năng mới (Ví dụ: `feat(US-20): thêm chức năng đóng dấu BẢN SAO khi in lại biên lai`)  
- **`fix`**: Sửa lỗi (Ví dụ: `fix(US-05): cho phép để trống CCCD với trẻ dưới 14 tuổi`)  
- **`docs`**: Thêm/sửa tài liệu (Ví dụ: `docs(charter): cập nhật bảng phân bổ ngân sách 100 triệu`)  
- **`refactor`**: Tối ưu code nhưng không đổi logic nghiệp vụ  
- **`test`**: Thêm dữ liệu mẫu hoặc viết test case

---

## 🔄 3\. Quy trình 5 bước hoàn thành 1 Nhiệm vụ (User Story)

### Bước 1: Nhận task trên GitHub Projects

- Mở bảng **GitHub Projects** của nhóm, chuyển thẻ User Story của bạn từ cột `Sprint Todo` sang `In Progress`.

### Bước 2: Tạo nhánh làm việc trên máy cá nhân

```sh
git checkout develop
git pull origin develop
git checkout -b feat/US-xx-ten-tinh-nang
```

&nbsp;

### Bước 3: Lập trình & Tự kiểm thử (Self-Test)

- Viết code trong đúng thư mục module được phân công.  
- Mở file `PRODUCT_BACKLOG.md`, đọc kỹ tất cả các mã **`AC-xx.y`** của User Story đó và tự chạy thử trên máy xem đã thỏa mãn 100% chưa.

### Bước 4: Đẩy code và Tạo Pull Request (PR)

```sh
git add .
git commit -m "feat(US-xx): hoàn thành chức năng ..."
git push origin feat/US-xx-ten-tinh-nang
```

&nbsp;

- Lên GitHub tạo **Pull Request** từ nhánh `feat/US-xx...` vào nhánh **`develop`**.  
- Điền đầy đủ checklist trong mẫu Pull Request và gắn Reviewer theo cặp phân công:  
  - **Cặp 1:** Thành viên 1 $\leftrightarrow$ Lê Trường Giang (TV3)  
  - **Cặp 2:** Vũ Trung Kiên (TV2) $\leftrightarrow$ Nguyễn Việt Tùng (TV4) $\leftrightarrow$ Lê Nguyễn Nhật Huy (TV5)

### Bước 5: Code Review & Merge

- Người được gắn tên Reviewer kiểm tra code trong vòng **12 giờ**, chạy thử các trường hợp biên (Edge cases). Nếu đạt thì bấm **Approve & Merge** vào `develop`, sau đó chuyển thẻ trên GitHub Projects sang cột `Done`.

---

## ✅ 4\. Định nghĩa Hoàn thành (Definition of Done \- DoD)

Một User Story chỉ được coi là **Done** khi thỏa mãn tất cả các điều kiện sau:

1. Thỏa mãn 100% các tiêu chí nghiệm thu (`Acceptance Criteria`) đã viết trong Backlog.  
2. Đáp ứng các yêu cầu phi chức năng chung (`NFR`):  
   - Phân quyền RBAC đúng theo **Ma trận phân quyền** (không bị lộ API cho vai trò không có quyền).  
   - Giao diện tiếng Việt rõ ràng, cỡ chữ tối thiểu `14px`, nút bấm lớn dễ thao tác cho Thủ quỹ lớn tuổi (`NFR-007`).  
   - Các thao tác nhạy cảm (sửa đơn giá, hủy biên lai, duyệt sửa nhân khẩu) đều gọi hàm ghi `Audit Log` (`US-31`).  
3. Đã được ít nhất 1 thành viên khác trong nhóm Review và Merge vào nhánh `develop` không có lỗi biên dịch.