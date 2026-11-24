-- =====================================================================
-- Seed dữ liệu kiểm thử Sprint 2 trên PostgreSQL thật (Idempotent)
-- Chạy sau seed_sprint1_test.sql
-- Bao gồm: căn hộ, hộ gia đình, nhân khẩu (<14 tuổi & >=14 tuổi),
-- nhà cung cấp, khoản thu (xe máy/ô tô/xe đạp/điện/nước), lịch sử đơn giá,
-- miễn giảm (ACTIVE & REVOKED), phương tiện (ACTIVE & INACTIVE),
-- kỳ thu lịch sử 2026-09-01 (CLOSED) kèm chỉ số điện/nước và giấy báo.
-- =====================================================================

BEGIN;

-- 1. Căn hộ bổ sung cho Sprint 2 (giữ nguyên C0901 trống để test import/chuyển nhượng)
INSERT INTO apartments (code, floor, area_m2, status, note)
VALUES
    ('D1508', 15, 98.00, 'ACTIVE', 'Căn 3 phòng ngủ tầng 15 - Phục vụ test Sprint 2')
ON CONFLICT (code) DO NOTHING;

-- 2. Hộ gia đình bổ sung
INSERT INTO households (household_code, status, contact_phone, contact_email, note)
VALUES
    ('H-D1508-01', 'ACTIVE', '0956789012', 'hung.d1508@bluemoon.local', 'Hộ gia đình mẫu căn D1508')
ON CONFLICT (household_code) DO NOTHING;

-- 3. Gán cư trú hiện tại cho D1508
INSERT INTO apartment_occupancies (apartment_id, household_id, start_date, end_date)
SELECT a.id, h.id, DATE '2026-01-01', NULL
FROM apartments a
JOIN households h ON h.household_code = 'H-D1508-01'
WHERE a.code = 'D1508'
  AND NOT EXISTS (
      SELECT 1 FROM apartment_occupancies ao
      WHERE ao.household_id = h.id AND ao.end_date IS NULL
  );

-- 4. Nhân khẩu bổ sung (US-05, US-23): thành viên người lớn + trẻ em < 14 tuổi (không CCCD)
-- Hộ H-B1204-01: vợ + con nhỏ
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lê Thị Hương', DATE '1990-07-15', 'NU', '001190001205', '0934567891', 'huong.b1204@bluemoon.local', 'Vợ', false, 'THUONG_TRU'
FROM households h
WHERE h.household_code = 'H-B1204-01'
  AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001190001205' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Phạm Gia Bảo', DATE '2018-09-02', 'NAM', NULL, NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h
WHERE h.household_code = 'H-B1204-01'
  AND NOT EXISTS (
      SELECT 1 FROM residents r
      WHERE r.household_id = h.id AND r.full_name = 'Phạm Gia Bảo' AND NOT r.is_deleted
  );

-- Hộ H-A0502-01: con gái
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Nguyễn Thảo Vy', DATE '2004-11-10', 'NU', '001304000503', '0945678902', NULL, 'Con', false, 'THUONG_TRU'
FROM households h
WHERE h.household_code = 'H-A0502-01'
  AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001304000503' AND NOT r.is_deleted);

-- Hộ H-D1508-01: chủ hộ + thành viên
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Đỗ Mạnh Hùng', DATE '1985-03-22', 'NAM', '001085001508', '0956789012', 'hung.d1508@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h
WHERE h.household_code = 'H-D1508-01'
  AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001085001508' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Đỗ Minh Anh', DATE '2016-05-19', 'NU', NULL, NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h
WHERE h.household_code = 'H-D1508-01'
  AND NOT EXISTS (
      SELECT 1 FROM residents r
      WHERE r.household_id = h.id AND r.full_name = 'Đỗ Minh Anh' AND NOT r.is_deleted
  );

-- Hộ HH-RT-02 (chưa có chủ hộ trong DB): bổ sung chủ hộ để đủ dữ liệu tra cứu
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Hoàng Văn An', DATE '1992-01-18', 'NAM', '001092009901', '0966778899', NULL, 'Chủ hộ', true, 'THUONG_TRU'
FROM households h
WHERE h.household_code = 'HH-RT-02'
  AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001092009901' AND NOT r.is_deleted);

-- 5. Nhà cung cấp dịch vụ (điện, nước) phục vụ khoản thu METERED / thu hộ
INSERT INTO service_providers (name, service_type, contact, is_active)
SELECT 'EVN Hà Nội', 'ELECTRIC', '19001288', true
WHERE NOT EXISTS (SELECT 1 FROM service_providers WHERE name = 'EVN Hà Nội');

INSERT INTO service_providers (name, service_type, contact, is_active)
SELECT 'Nước sạch Viwaco', 'WATER', '19002929', true
WHERE NOT EXISTS (SELECT 1 FROM service_providers WHERE name = 'Nước sạch Viwaco');

-- 6. Danh mục khoản thu Sprint 2 (PARKING: CAR/BICYCLE, UTILITY: METERED điện/nước)
INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, provider_id, cycle, due_day, status, description, created_by)
SELECT 'PHI_GUI_OTO', 'Phí gửi xe ô tô', 'PARKING', 'PER_VEHICLE', 'xe', 'CAR', false, NULL, 'MONTHLY', 15, 'ACTIVE', 'Phí trông giữ xe ô tô theo tháng', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt'
ON CONFLICT (code) DO NOTHING;

INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, provider_id, cycle, due_day, status, description, created_by)
SELECT 'PHI_GUI_XEDAP', 'Phí gửi xe đạp', 'PARKING', 'PER_VEHICLE', 'xe', 'BICYCLE', false, NULL, 'MONTHLY', 15, 'ACTIVE', 'Phí trông giữ xe đạp theo tháng', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt'
ON CONFLICT (code) DO NOTHING;

INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, provider_id, cycle, due_day, status, description, created_by)
SELECT 'TIEN_DIEN', 'Tiền điện sinh hoạt', 'UTILITY', 'METERED', 'kWh', NULL, true, sp.id, 'MONTHLY', 15, 'ACTIVE', 'Thu hộ tiền điện theo chỉ số công tơ', u.id
FROM users u, service_providers sp
WHERE lower(u.username) = 'admin_bqt' AND sp.name = 'EVN Hà Nội'
ON CONFLICT (code) DO NOTHING;

INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, provider_id, cycle, due_day, status, description, created_by)
SELECT 'TIEN_NUOC', 'Tiền nước sinh hoạt', 'UTILITY', 'METERED', 'm3', NULL, true, sp.id, 'MONTHLY', 15, 'ACTIVE', 'Thu hộ tiền nước theo đồng hồ nước', u.id
FROM users u, service_providers sp
WHERE lower(u.username) = 'admin_bqt' AND sp.name = 'Nước sạch Viwaco'
ON CONFLICT (code) DO NOTHING;

-- 7. Lịch sử đơn giá (US-14): có cả đơn giá lịch sử đã khép và đơn giá đang áp dụng
-- PHI_GUI_OTO: 1.200.000 đ (01/01/2026 - 30/06/2026), sau đó tăng lên 1.500.000 đ (01/07/2026 - NULL)
INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 1200000.00, DATE '2026-01-01', DATE '2026-06-30', u.id
FROM fee_types ft, users u
WHERE ft.code = 'PHI_GUI_OTO' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id AND fr.effective_from = DATE '2026-01-01');

INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 1500000.00, DATE '2026-07-01', NULL, u.id
FROM fee_types ft, users u
WHERE ft.code = 'PHI_GUI_OTO' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id AND fr.effective_from = DATE '2026-07-01');

-- PHI_GUI_XEDAP: 20.000 đ
INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 20000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u
WHERE ft.code = 'PHI_GUI_XEDAP' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id);

-- TIEN_DIEN: 3.000 đ/kWh
INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 3000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u
WHERE ft.code = 'TIEN_DIEN' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id);

-- TIEN_NUOC: 12.000 đ/m3
INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 12000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u
WHERE ft.code = 'TIEN_NUOC' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id);

-- 8. Chính sách miễn giảm (US-15, US-16): PERCENT ACTIVE, AMOUNT ACTIVE, và REVOKED
INSERT INTO fee_exemptions (household_id, fee_type_id, discount_type, discount_value, reason, decision_no, approved_by, valid_from, valid_to, status)
SELECT h.id, ft.id, 'PERCENT', 50.00, 'Gia đình chính sách giảm 50% phí quản lý', 'QD-MG-2026-01', u.id, DATE '2026-01-01', NULL, 'ACTIVE'
FROM households h, fee_types ft, users u
WHERE h.household_code = 'H-B1204-01' AND ft.code = 'PHI_QUAN_LY' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_exemptions fe WHERE fe.decision_no = 'QD-MG-2026-01');

INSERT INTO fee_exemptions (household_id, fee_type_id, discount_type, discount_value, reason, decision_no, approved_by, valid_from, valid_to, status)
SELECT h.id, ft.id, 'AMOUNT', 20000.00, 'Hỗ trợ giảm phí vệ sinh hàng tháng', 'QD-MG-2026-02', u.id, DATE '2026-01-01', NULL, 'ACTIVE'
FROM households h, fee_types ft, users u
WHERE h.household_code = 'H-A0502-01' AND ft.code = 'PHI_VE_SINH' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_exemptions fe WHERE fe.decision_no = 'QD-MG-2026-02');

INSERT INTO fee_exemptions (household_id, fee_type_id, discount_type, discount_value, reason, decision_no, approved_by, valid_from, valid_to, status)
SELECT h.id, ft.id, 'PERCENT', 100.00, 'Miễn phí vệ sinh giai đoạn đầu nhận nhà (đã thu hồi)', 'QD-MG-2026-03', u.id, DATE '2026-01-01', DATE '2026-05-31', 'REVOKED'
FROM households h, fee_types ft, users u
WHERE h.household_code = 'H-D1508-01' AND ft.code = 'PHI_VE_SINH' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_exemptions fe WHERE fe.decision_no = 'QD-MG-2026-03');

-- 9. Phương tiện gửi xe (US-36, US-37): đủ 3 loại xe + cả xe ACTIVE và INACTIVE
INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date, unregistered_date)
SELECT h.id, '29B1-12345', 'MOTORBIKE', 'Honda Vision', 'Đen', 'ACTIVE', DATE '2026-01-10', NULL
FROM households h WHERE h.household_code = 'H-B1204-01'
  AND NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = '29B1-12345');

INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date, unregistered_date)
SELECT h.id, '29B1-67890', 'MOTORBIKE', 'Yamaha Grande', 'Trắng', 'ACTIVE', DATE '2026-02-01', NULL
FROM households h WHERE h.household_code = 'H-B1204-01'
  AND NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = '29B1-67890');

INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date, unregistered_date)
SELECT h.id, '30A-55588', 'CAR', 'Mazda CX-5', 'Đỏ', 'ACTIVE', DATE '2026-01-15', NULL
FROM households h WHERE h.household_code = 'H-B1204-01'
  AND NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = '30A-55588');

INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date, unregistered_date)
SELECT h.id, '29B1-00001', 'MOTORBIKE', 'Honda Wave', 'Xanh', 'INACTIVE', DATE '2026-01-05', DATE '2026-03-01'
FROM households h WHERE h.household_code = 'H-B1204-01'
  AND NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = '29B1-00001');

INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date, unregistered_date)
SELECT h.id, '29C1-22233', 'MOTORBIKE', 'Honda Lead', 'Bạc', 'ACTIVE', DATE '2026-01-20', NULL
FROM households h WHERE h.household_code = 'H-A0502-01'
  AND NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = '29C1-22233');

INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date, unregistered_date)
SELECT h.id, 'XD-A0502-01', 'BICYCLE', 'Giant ATX', 'Xanh dương', 'ACTIVE', DATE '2026-02-10', NULL
FROM households h WHERE h.household_code = 'H-A0502-01'
  AND NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = 'XD-A0502-01');

INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date, unregistered_date)
SELECT h.id, '30H-99900', 'CAR', 'Toyota Camry', 'Đen', 'ACTIVE', DATE '2026-03-01', NULL
FROM households h WHERE h.household_code = 'H-D1508-01'
  AND NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = '30H-99900');

INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date, unregistered_date)
SELECT h.id, 'XD-D1508-01', 'BICYCLE', 'Thống Nhất', 'Trắng', 'ACTIVE', DATE '2026-03-05', NULL
FROM households h WHERE h.household_code = 'H-D1508-01'
  AND NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = 'XD-D1508-01');

-- 10. Kỳ thu lịch sử mẫu 2026-09-01 (CLOSED) kèm chỉ số điện/nước và công nợ cũ cho hộ H-A0502-01
INSERT INTO billing_periods (period_month, name, due_date, status, generated_at, closed_at, created_by)
SELECT DATE '2026-09-01', 'Kỳ thu phí tháng 09/2026', DATE '2026-09-20', 'CLOSED',
       TIMESTAMPTZ '2026-09-02 09:00:00+07', TIMESTAMPTZ '2026-09-25 17:00:00+07', u.id
FROM users u WHERE lower(u.username) = 'ketoan_01'
ON CONFLICT (period_month) DO NOTHING;

-- Chỉ số điện kỳ 09/2026 (cột consumption là GENERATED ALWAYS AS STORED -> không insert)
INSERT INTO utility_readings (household_id, fee_type_id, billing_period_id, previous_index, current_index, unit_price, amount, recorded_by)
SELECT h.id, ft.id, bp.id, 1000.00, 1150.00, 3000.00, 450000.00, u.id
FROM households h, fee_types ft, billing_periods bp, users u
WHERE h.household_code = 'H-B1204-01' AND ft.code = 'TIEN_DIEN'
  AND bp.period_month = DATE '2026-09-01' AND lower(u.username) = 'ketoan_01'
ON CONFLICT (household_id, fee_type_id, billing_period_id) DO NOTHING;

INSERT INTO utility_readings (household_id, fee_type_id, billing_period_id, previous_index, current_index, unit_price, amount, recorded_by)
SELECT h.id, ft.id, bp.id, 500.00, 620.00, 3000.00, 360000.00, u.id
FROM households h, fee_types ft, billing_periods bp, users u
WHERE h.household_code = 'H-A0502-01' AND ft.code = 'TIEN_DIEN'
  AND bp.period_month = DATE '2026-09-01' AND lower(u.username) = 'ketoan_01'
ON CONFLICT (household_id, fee_type_id, billing_period_id) DO NOTHING;

-- Giấy báo kỳ 09/2026 cho H-A0502-01 (UNPAID -> để test cộng dồn previous_debt khi chạy kỳ mới)
-- Căn A0502: 72m2 * 7000 = 504000 (PHI_QUAN_LY) + 30000 - 20000 = 10000 (PHI_VE_SINH) + 360000 (TIEN_DIEN)
-- Tổng fee_amount = 894000, discount_amount = 20000, total_due = 874000
INSERT INTO invoices (billing_period_id, household_id, apartment_id, apartment_area, fee_amount, discount_amount, previous_debt, credit_applied, total_due, paid_amount, status)
SELECT bp.id, h.id, a.id, a.area_m2, 894000.00, 20000.00, 0.00, 0.00, 874000.00, 0.00, 'UNPAID'
FROM billing_periods bp
JOIN households h ON h.household_code = 'H-A0502-01'
JOIN apartment_occupancies ao ON ao.household_id = h.id AND ao.end_date IS NULL
JOIN apartments a ON a.id = ao.apartment_id
WHERE bp.period_month = DATE '2026-09-01'
ON CONFLICT (billing_period_id, household_id) DO NOTHING;

INSERT INTO invoice_items (invoice_id, fee_type_id, quantity, unit_price, gross_amount, discount_amount, net_amount, paid_amount, description)
SELECT inv.id, ft.id, 72.000, 7000.00, 504000.00, 0.00, 504000.00, 0.00, '72 m² × 7.000 đ'
FROM invoices inv
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-09-01'
JOIN households h ON h.id = inv.household_id AND h.household_code = 'H-A0502-01'
JOIN fee_types ft ON ft.code = 'PHI_QUAN_LY'
ON CONFLICT (invoice_id, fee_type_id) DO NOTHING;

INSERT INTO invoice_items (invoice_id, fee_type_id, quantity, unit_price, gross_amount, discount_amount, net_amount, paid_amount, description)
SELECT inv.id, ft.id, 1.000, 30000.00, 30000.00, 20000.00, 10000.00, 0.00, '1 hộ × 30.000 đ (giảm 20.000 đ)'
FROM invoices inv
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-09-01'
JOIN households h ON h.id = inv.household_id AND h.household_code = 'H-A0502-01'
JOIN fee_types ft ON ft.code = 'PHI_VE_SINH'
ON CONFLICT (invoice_id, fee_type_id) DO NOTHING;

INSERT INTO invoice_items (invoice_id, fee_type_id, quantity, unit_price, gross_amount, discount_amount, net_amount, paid_amount, description)
SELECT inv.id, ft.id, 120.000, 3000.00, 360000.00, 0.00, 360000.00, 0.00, 'Tiền điện: 620 - 500 = 120 kWh × 3.000 đ'
FROM invoices inv
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-09-01'
JOIN households h ON h.id = inv.household_id AND h.household_code = 'H-A0502-01'
JOIN fee_types ft ON ft.code = 'TIEN_DIEN'
ON CONFLICT (invoice_id, fee_type_id) DO NOTHING;

COMMIT;
