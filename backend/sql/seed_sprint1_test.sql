-- =====================================================================
-- Seed dữ liệu kiểm thử Sprint 1 trên PostgreSQL thật (Idempotent)
-- Mật khẩu chung cho toàn bộ tài khoản test: BlueMoon@2026
-- =====================================================================

BEGIN;

-- 1. Căn hộ mẫu (US-01)
INSERT INTO apartments (code, floor, area_m2, status, note)
VALUES
    ('B1204', 12, 85.50, 'ACTIVE', 'Căn góc ban công Đông Nam - Hộ 1 đang ở'),
    ('A0502',  5, 72.00, 'ACTIVE', 'Căn 2 phòng ngủ - Hộ 2 đang ở'),
    ('C0901',  9, 64.25, 'ACTIVE', 'Căn hộ trống phục vụ test tạo hộ / chuyển nhượng')
ON CONFLICT (code) DO NOTHING;

-- 2. Hộ gia đình mẫu (US-01, US-02, US-03)
INSERT INTO households (household_code, status, contact_phone, contact_email, note)
VALUES
    ('H-B1204-01', 'ACTIVE', '0934567890', 'tuan.b1204@bluemoon.local', 'Hộ gia đình mẫu căn B1204'),
    ('H-A0502-01', 'ACTIVE', '0945678901', 'bich.a0502@bluemoon.local', 'Hộ gia đình mẫu căn A0502')
ON CONFLICT (household_code) DO NOTHING;

-- 3. Gán cư trú hiện tại (apartment_occupancies)
INSERT INTO apartment_occupancies (apartment_id, household_id, start_date, end_date)
SELECT a.id, h.id, DATE '2026-01-01', NULL
FROM apartments a
JOIN households h ON h.household_code = 'H-B1204-01'
WHERE a.code = 'B1204'
  AND NOT EXISTS (
      SELECT 1 FROM apartment_occupancies ao
      WHERE ao.household_id = h.id AND ao.end_date IS NULL
  );

INSERT INTO apartment_occupancies (apartment_id, household_id, start_date, end_date)
SELECT a.id, h.id, DATE '2026-01-01', NULL
FROM apartments a
JOIN households h ON h.household_code = 'H-A0502-01'
WHERE a.code = 'A0502'
  AND NOT EXISTS (
      SELECT 1 FROM apartment_occupancies ao
      WHERE ao.household_id = h.id AND ao.end_date IS NULL
  );

-- 4. Chủ hộ mẫu (US-01, US-02)
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Phạm Minh Tuấn', DATE '1988-04-12', 'NAM', '001088001204', '0934567890', 'tuan.b1204@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h
WHERE h.household_code = 'H-B1204-01'
  AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001088001204' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Nguyễn Thị Bích', DATE '1990-08-20', 'NU', '001190000502', '0945678901', 'bich.a0502@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h
WHERE h.household_code = 'H-A0502-01'
  AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001190000502' AND NOT r.is_deleted);

-- 5. Tài khoản người dùng 4 vai trò chuẩn (US-28..31, US-44)
-- Password hash (Bcrypt rounds=12): BlueMoon@2026
INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT
    'admin_bqt',
    '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
    'Nguyễn Văn Quản Trị',
    'admin@bluemoon.local',
    '0901234567',
    r.id,
    NULL,
    true,
    false
FROM roles r WHERE r.code = 'ADMIN'
ON CONFLICT (lower(username)) DO NOTHING;

INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT
    'ketoan_01',
    '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
    'Trần Thị Thu Trang',
    'ketoan@bluemoon.local',
    '0912345678',
    r.id,
    NULL,
    true,
    false
FROM roles r WHERE r.code = 'ACCOUNTANT'
ON CONFLICT (lower(username)) DO NOTHING;

INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT
    'thuquy_01',
    '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
    'Lê Hoàng Nam',
    'thuquy@bluemoon.local',
    '0923456789',
    r.id,
    NULL,
    true,
    false
FROM roles r WHERE r.code = 'TREASURER'
ON CONFLICT (lower(username)) DO NOTHING;

INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT
    'cudan_b1204',
    '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
    'Phạm Minh Tuấn',
    'tuan.b1204@bluemoon.local',
    '0934567890',
    r.id,
    h.id,
    true,
    false
FROM roles r
JOIN households h ON h.household_code = 'H-B1204-01'
WHERE r.code = 'RESIDENT'
ON CONFLICT (lower(username)) DO NOTHING;

-- 6. Danh mục khoản thu & đơn giá mẫu (US-12, US-13)
INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, cycle, due_day, status, description, created_by)
SELECT 'PHI_QUAN_LY', 'Phí quản lý vận hành chung cư', 'MANAGEMENT', 'PER_M2', 'm2', NULL, false, 'MONTHLY', 15, 'ACTIVE', 'Phí quản lý tính theo m2 diện tích căn hộ', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt'
ON CONFLICT (code) DO NOTHING;

INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, cycle, due_day, status, description, created_by)
SELECT 'PHI_GUI_XEMAY', 'Phí gửi xe máy', 'PARKING', 'PER_VEHICLE', 'xe', 'MOTORBIKE', false, 'MONTHLY', 15, 'ACTIVE', 'Phí trông giữ xe máy theo tháng', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt'
ON CONFLICT (code) DO NOTHING;

INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, cycle, due_day, status, description, created_by)
SELECT 'PHI_VE_SINH', 'Phí vệ sinh môi trường', 'OTHER', 'PER_HOUSEHOLD', 'hộ', NULL, false, 'MONTHLY', 15, 'ACTIVE', 'Phí thu gom rác sinh hoạt cố định theo hộ', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt'
ON CONFLICT (code) DO NOTHING;

INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 7000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u
WHERE ft.code = 'PHI_QUAN_LY' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id AND fr.effective_to IS NULL);

INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 70000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u
WHERE ft.code = 'PHI_GUI_XEMAY' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id AND fr.effective_to IS NULL);

INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 30000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u
WHERE ft.code = 'PHI_VE_SINH' AND lower(u.username) = 'admin_bqt'
  AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id AND fr.effective_to IS NULL);

COMMIT;
