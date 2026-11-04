import itertools
import pytest
from sqlalchemy import text
from app.core.security import create_access_token

_id_generator = itertools.count(3000)


# ==============================================================================
# FIXTURES & TEST SETUP FOR US-02 (HOUSEHOLD MANAGEMENT)
# ==============================================================================

@pytest.fixture
def seed_treasurer_user(db_session):
    """Ensure a user with role TREASURER (role_id=3) exists in the test DB."""
    user = db_session.execute(text("SELECT id FROM users WHERE id = 5")).fetchone()
    if not user:
        db_session.execute(text("""
            INSERT INTO users (id, username, password_hash, full_name, email, role_id, is_active, must_change_password, failed_login_count)
            VALUES (5, 'treasurer_test', 'hash123', 'Thu Quy Test', 'treasurer@bluemoon.local', 3, 1, 0, 0)
        """))
        db_session.commit()
    return 5


@pytest.fixture
def auth_headers_accountant():
    token = create_access_token({
        "sub": "2",
        "username": "accountant_test",
        "role": "ACCOUNTANT",
        "must_change_password": False
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_treasurer(seed_treasurer_user):
    token = create_access_token({
        "sub": "5",
        "username": "treasurer_test",
        "role": "TREASURER",
        "must_change_password": False
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_must_change_pw(db_session):
    """Ensure a user exists with must_change_password=True in DB."""
    user = db_session.execute(text("SELECT id FROM users WHERE id = 6")).fetchone()
    if not user:
        db_session.execute(text("""
            INSERT INTO users (id, username, password_hash, full_name, email, role_id, is_active, must_change_password, failed_login_count)
            VALUES (6, 'admin_must_change', 'hash123', 'Admin Must Change', 'mustchange@bluemoon.local', 1, 1, 1, 0)
        """))
    else:
        db_session.execute(text("UPDATE users SET must_change_password = 1 WHERE id = 6"))
    db_session.commit()

    token = create_access_token({
        "sub": "6",
        "username": "admin_must_change",
        "role": "ADMIN",
        "must_change_password": True
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def household_factory(db_session):
    """Factory to create test apartments, households, occupancies, and residents cleanly with unique IDs."""
    def _create(
        household_id=None,
        household_code=None,
        status="ACTIVE",
        contact_phone="0901234567",
        contact_email="test@example.com",
        note="Initial household note",
        apartment_id=None,
        apartment_code=None,
        create_residents=True
    ):
        hid = household_id or next(_id_generator)
        apt_id = apartment_id or next(_id_generator)
        code = household_code or f"HO-{hid}"
        apt_code = apartment_code or f"P.{apt_id}"

        # Insert apartment
        db_session.execute(text("""
            INSERT INTO apartments (id, code, floor, area_m2, status, note)
            VALUES (:apt_id, :apt_code, 10, 75.5, 'ACTIVE', 'Test Apartment')
        """), {"apt_id": apt_id, "apt_code": apt_code})

        # Insert household
        db_session.execute(text("""
            INSERT INTO households (id, household_code, status, contact_phone, contact_email, note)
            VALUES (:hid, :hcode, :status, :phone, :email, :note)
        """), {
            "hid": hid,
            "hcode": code,
            "status": status,
            "phone": contact_phone,
            "email": contact_email,
            "note": note
        })

        # Link apartment occupancy
        db_session.execute(text("""
            INSERT INTO apartment_occupancies (apartment_id, household_id, start_date)
            VALUES (:apt_id, :hid, '2026-01-01')
        """), {"apt_id": apt_id, "hid": hid})

        head_res_id = next(_id_generator)
        member_res_id = next(_id_generator)

        if create_residents:
            # Head resident
            db_session.execute(text("""
                INSERT INTO residents (id, household_id, full_name, date_of_birth, gender, cccd, is_head, residence_status, is_deleted)
                VALUES (:rid, :hid, :name, '1980-01-01', 'NAM', :cccd, 1, 'THUONG_TRU', 0)
            """), {
                "rid": head_res_id,
                "hid": hid,
                "name": f"Chủ Hộ {hid}",
                "cccd": f"001080{hid:06d}"[:12]
            })

            # Member resident
            db_session.execute(text("""
                INSERT INTO residents (id, household_id, full_name, date_of_birth, gender, cccd, is_head, residence_status, is_deleted)
                VALUES (:rid, :hid, :name, '1985-05-05', 'NU', :cccd, 0, 'THUONG_TRU', 0)
            """), {
                "rid": member_res_id,
                "hid": hid,
                "name": f"Thành Viên {hid}",
                "cccd": f"001085{hid:06d}"[:12]
            })

        db_session.commit()
        return {
            "household_id": hid,
            "household_code": code,
            "apartment_id": apt_id,
            "apartment_code": apt_code,
            "head_resident_id": head_res_id if create_residents else None,
            "member_resident_id": member_res_id if create_residents else None
        }

    return _create


# ==============================================================================
# SUITE 1: PATCH /api/v1/households/{id} (Cập nhật thông tin liên hệ hộ)
# ==============================================================================

class TestPatchHousehold:

    def test_patch_phone_only_success(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0987654321"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == h["household_id"]
        assert data["contact_phone"] == "0987654321"
        assert data["contact_email"] == "test@example.com"
        assert data["note"] == "Initial household note"

    def test_patch_email_only_success(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_email": "updated@example.com"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["contact_email"] == "updated@example.com"
        assert data["contact_phone"] == "0901234567"

    def test_patch_note_only_success(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"note": "New note updated by admin"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["note"] == "New note updated by admin"

    def test_patch_all_fields_success(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        payload = {
            "contact_phone": "0911223344",
            "contact_email": "allfields@example.com",
            "note": "All three fields updated"
        }
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json=payload,
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["contact_phone"] == "0911223344"
        assert data["contact_email"] == "allfields@example.com"
        assert data["note"] == "All three fields updated"

    def test_patch_empty_payload_noop(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["contact_phone"] == "0901234567"
        assert data["contact_email"] == "test@example.com"
        assert data["note"] == "Initial household note"

    def test_patch_vietnamese_unicode_note(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        vietnamese_note = "Hộ gia đình có người cao tuổi và trẻ sơ sinh. Ưu tiên liên lạc qua Zalo."
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"note": vietnamese_note},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["note"] == vietnamese_note

    def test_patch_special_characters_note(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        spec_chars = "!@#$%^&*()_+-=[]{}|;':\",.<>?/`~"
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"note": spec_chars},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["note"] == spec_chars

    def test_patch_long_note(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        long_note = "A" * 1000
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"note": long_note},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["note"] == long_note

    def test_patch_clear_note_with_null(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"note": None},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["note"] is None

    def test_patch_clear_phone_with_null(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": None},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["contact_phone"] is None

    def test_patch_clear_email_with_null(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_email": None},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["contact_email"] is None

    @pytest.mark.parametrize("phone_val", [
        "0912345678",
        "+84912345678",
        "024-3123-4567"
    ])
    def test_patch_valid_phone_formats(self, client, auth_headers_admin, household_factory, phone_val):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": phone_val},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["contact_phone"] == phone_val

    def test_patch_full_response_schema(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0999999999"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        expected_fields = [
            "id", "household_code", "status", "contact_phone", "contact_email", "note",
            "apartment_id", "apartment_code", "floor", "area_m2",
            "head_resident_id", "head_name", "head_phone", "member_count",
            "created_at", "updated_at"
        ]
        for f in expected_fields:
            assert f in data, f"Missing field in Household response: {f}"
        assert data["household_code"] == h["household_code"]
        assert data["status"] == "ACTIVE"
        assert data["member_count"] == 2

    def test_patch_on_inactive_household(self, client, auth_headers_admin, household_factory):
        h = household_factory(status="INACTIVE")
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0977777777"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "INACTIVE"
        assert data["contact_phone"] == "0977777777"

    @pytest.mark.parametrize("invalid_email", [
        "not-an-email",
        "missingatsign.com",
        "user name@example.com",
        "@missinguser.com"
    ])
    def test_patch_invalid_email_format(self, client, auth_headers_admin, household_factory, invalid_email):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_email": invalid_email},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        err = res.json()
        assert err["code"] == "VALIDATION_ERROR"
        assert "message" in err
        assert "details" in err

    def test_patch_invalid_phone_type(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": ["invalid", "phone", "list"]},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_patch_invalid_note_type(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"note": {"nested": "dict_not_string"}},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_patch_immutable_household_code_ignored(self, client, auth_headers_admin, household_factory):
        h = household_factory(household_code="HO-ORIGINAL-CODE")
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"household_code": "HO-HACKED-CODE"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["household_code"] == "HO-ORIGINAL-CODE"

    def test_patch_immutable_id_ignored(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"id": 999999},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["id"] == h["household_id"]

    def test_patch_immutable_status_ignored(self, client, auth_headers_admin, household_factory):
        h = household_factory(status="ACTIVE")
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"status": "INACTIVE"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACTIVE"

    def test_patch_not_found_household(self, client, auth_headers_admin):
        res = client.patch(
            "/api/v1/households/999999",
            json={"contact_phone": "0912345678"},
            headers=auth_headers_admin
        )
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_patch_negative_household_id(self, client, auth_headers_admin):
        res = client.patch(
            "/api/v1/households/-1",
            json={"contact_phone": "0912345678"},
            headers=auth_headers_admin
        )
        assert res.status_code in (400, 404)
        assert res.json()["code"] in ("NOT_FOUND", "VALIDATION_ERROR")

    def test_patch_zero_household_id(self, client, auth_headers_admin):
        res = client.patch(
            "/api/v1/households/0",
            json={"contact_phone": "0912345678"},
            headers=auth_headers_admin
        )
        assert res.status_code in (400, 404)
        assert res.json()["code"] in ("NOT_FOUND", "VALIDATION_ERROR")

    def test_patch_unauthenticated(self, client, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0912345678"}
        )
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_patch_invalid_token(self, client, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0912345678"},
            headers={"Authorization": "Bearer malformed.jwt.token"}
        )
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_patch_forbidden_accountant(self, client, auth_headers_accountant, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0912345678"},
            headers=auth_headers_accountant
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_patch_forbidden_treasurer(self, client, auth_headers_treasurer, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0912345678"},
            headers=auth_headers_treasurer
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_patch_forbidden_resident(self, client, auth_headers_resident_101, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0912345678"},
            headers=auth_headers_resident_101
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_patch_password_change_required(self, client, auth_headers_must_change_pw, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0912345678"},
            headers=auth_headers_must_change_pw
        )
        assert res.status_code == 403
        assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# ==============================================================================
# SUITE 2: POST /api/v1/households/{id}/deactivate (Ngừng quản lý hộ)
# ==============================================================================

class TestDeactivateHousehold:

    def test_deactivate_household_success(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Ho gia dinh chuyen sang khu vuc khac"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["status"] == "INACTIVE"

    def test_deactivate_household_status_is_inactive(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Deactivation verification"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == h["household_id"]
        assert data["status"] == "INACTIVE"

    def test_deactivate_household_db_persistence_no_hard_delete(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Check persistence no delete"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200

        # Query database directly to confirm record still exists with INACTIVE status
        row = db_session.execute(
            text("SELECT id, household_code, status FROM households WHERE id = :hid"),
            {"hid": h["household_id"]}
        ).fetchone()
        assert row is not None, "Record was deleted! Hard delete is strictly forbidden!"
        assert row[2] == "INACTIVE"

    def test_deactivate_household_preserves_household_metadata(self, client, auth_headers_admin, household_factory):
        h = household_factory(contact_phone="0912999888", contact_email="preserve@example.com")
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Check metadata preserved"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["household_code"] == h["household_code"]
        assert data["contact_phone"] == "0912999888"
        assert data["contact_email"] == "preserve@example.com"
        # When deactivated, household occupancy is ended so apartment_id becomes None
        assert data["apartment_id"] is None

    def test_deactivate_household_vietnamese_unicode_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        vietnamese_reason = "Gia đình chuyển công tác ra nước ngoài định cư dài hạn."
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": vietnamese_reason},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["status"] == "INACTIVE"

    def test_deactivate_household_long_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        long_reason = "Lý do ngừng quản lý chi tiết: " + ("B" * 500)
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": long_reason},
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["status"] == "INACTIVE"

    def test_deactivate_household_special_chars_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Deactivate with chars: [P.1001] -> Status changed (#123) & note: 'ok'"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200

    def test_deactivate_household_missing_reason_field(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_deactivate_household_empty_string_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": ""},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_deactivate_household_whitespace_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "    "},
            headers=auth_headers_admin
        )
        # Whitespace-only reason must either fail minLength validation or be rejected
        assert res.status_code in (200, 400)
        if res.status_code == 400:
            assert res.json()["code"] == "VALIDATION_ERROR"

    def test_deactivate_household_null_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": None},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_deactivate_household_invalid_reason_type_integer(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": 123456},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_deactivate_household_invalid_reason_type_dict(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": {"text": "object_not_string"}},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_deactivate_household_empty_request_body(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_deactivate_household_already_inactive(self, client, auth_headers_admin, household_factory):
        h = household_factory(status="INACTIVE")
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Already inactive deactivation attempt"},
            headers=auth_headers_admin
        )
        # Should be idempotent 200 or 400
        assert res.status_code in (200, 400)
        if res.status_code == 200:
            assert res.json()["status"] == "INACTIVE"

    def test_deactivate_household_not_found(self, client, auth_headers_admin):
        res = client.post(
            "/api/v1/households/999999/deactivate",
            json={"reason": "Deactivate nonexistent"},
            headers=auth_headers_admin
        )
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_deactivate_household_negative_id(self, client, auth_headers_admin):
        res = client.post(
            "/api/v1/households/-1/deactivate",
            json={"reason": "Negative id"},
            headers=auth_headers_admin
        )
        assert res.status_code in (400, 404)
        assert res.json()["code"] in ("NOT_FOUND", "VALIDATION_ERROR")

    def test_deactivate_household_zero_id(self, client, auth_headers_admin):
        res = client.post(
            "/api/v1/households/0/deactivate",
            json={"reason": "Zero id"},
            headers=auth_headers_admin
        )
        assert res.status_code in (400, 404)
        assert res.json()["code"] in ("NOT_FOUND", "VALIDATION_ERROR")

    def test_deactivate_household_unauthenticated(self, client, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "No token"}
        )
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_deactivate_household_invalid_token(self, client, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Invalid token"},
            headers={"Authorization": "Bearer invalid.jwt.string"}
        )
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_deactivate_household_forbidden_accountant(self, client, auth_headers_accountant, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Accountant forbidden"},
            headers=auth_headers_accountant
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_deactivate_household_forbidden_treasurer(self, client, auth_headers_treasurer, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Treasurer forbidden"},
            headers=auth_headers_treasurer
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_deactivate_household_forbidden_resident(self, client, auth_headers_resident_101, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Resident forbidden"},
            headers=auth_headers_resident_101
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_deactivate_household_password_change_required(self, client, auth_headers_must_change_pw, household_factory):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Must change pw"},
            headers=auth_headers_must_change_pw
        )
        assert res.status_code == 403
        assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"

    def test_deactivate_household_audit_log_recorded(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        res = client.post(
            f"/api/v1/households/{h['household_id']}/deactivate",
            json={"reason": "Audit verification for deactivation"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200

        # Verify audit log entry
        rows = db_session.execute(
            text("SELECT * FROM audit_logs WHERE entity_id = :hid"),
            {"hid": str(h["household_id"])}
        ).fetchall()
        assert len(rows) >= 1, "Deactivation must record an audit log!"


# ==============================================================================
# SUITE 3: PUT /api/v1/households/{id}/head (Đổi chủ hộ)
# ==============================================================================

class TestChangeHouseholdHead:

    def test_change_head_success(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04",
                "reason": "Chuyen quyen chu ho cho vo"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200

    def test_change_head_response_fields_updated(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == h["household_id"]
        assert data["head_resident_id"] == h["member_resident_id"]
        assert data["head_name"] == f"Thành Viên {h['household_id']}"

    def test_change_head_db_state_old_head_demoted(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        old_head_id = h["head_resident_id"]
        new_head_id = h["member_resident_id"]

        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": new_head_id, "effective_date": "2026-11-04"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200

        # Check DB: old head resident must have is_head = 0 (False)
        old_row = db_session.execute(
            text("SELECT is_head FROM residents WHERE id = :rid"),
            {"rid": old_head_id}
        ).fetchone()
        assert old_row is not None
        assert old_row[0] in (0, False), "Old head resident must have is_head = False!"

    def test_change_head_db_state_new_head_promoted(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        new_head_id = h["member_resident_id"]

        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": new_head_id, "effective_date": "2026-11-04"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200

        # Check DB: new head resident must have is_head = 1 (True)
        new_row = db_session.execute(
            text("SELECT is_head FROM residents WHERE id = :rid"),
            {"rid": new_head_id}
        ).fetchone()
        assert new_row is not None
        assert new_row[0] in (1, True), "New head resident must have is_head = True!"

    def test_change_head_single_active_head_invariant(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        new_head_id = h["member_resident_id"]

        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": new_head_id, "effective_date": "2026-11-04"},
            headers=auth_headers_admin
        )
        assert res.status_code == 200

        # Strict invariant: ux_residents_one_head (exactly ONE resident in the household has is_head = True)
        head_count = db_session.execute(
            text("SELECT COUNT(*) FROM residents WHERE household_id = :hid AND is_head = 1"),
            {"hid": h["household_id"]}
        ).scalar()
        assert head_count == 1, f"Expected exactly 1 head resident, found {head_count}!"

    def test_change_head_with_optional_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04",
                "reason": "Chủ hộ cũ bận công tác dài hạn"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200

    def test_change_head_without_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200

    def test_change_head_vietnamese_unicode_reason(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        vn_reason = "Ủy quyền đại diện pháp luật của căn hộ theo biên bản họp gia đình số 01/2026."
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04",
                "reason": vn_reason
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200

    def test_change_head_effective_date_iso(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-12-31"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200

    def test_change_head_audit_log_created(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04",
                "reason": "Audit verification"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200

        # AC-02.1: Ghi Audit Log CHANGE_HEAD
        rows = db_session.execute(
            text("SELECT action, entity_type, entity_id FROM audit_logs WHERE action = 'CHANGE_HEAD' AND entity_id = :hid"),
            {"hid": str(h["household_id"])}
        ).fetchall()
        assert len(rows) >= 1, "Audit Log with action 'CHANGE_HEAD' must be recorded!"
        assert rows[-1][0] == "CHANGE_HEAD"
        assert rows[-1][1] == "HOUSEHOLD"

    def test_change_head_audit_log_values_and_entity(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04",
                "reason": "Test audit values"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200

        row = db_session.execute(
            text("SELECT old_value, new_value, user_id FROM audit_logs WHERE action = 'CHANGE_HEAD' AND entity_id = :hid ORDER BY id DESC LIMIT 1"),
            {"hid": str(h["household_id"])}
        ).fetchone()
        assert row is not None
        old_val_str = str(row[0])
        new_val_str = str(row[1])
        assert str(h["head_resident_id"]) in old_val_str, "Old head resident ID must be recorded in old_value"
        assert str(h["member_resident_id"]) in new_val_str, "New head resident ID must be recorded in new_value"
        assert row[2] == 1  # User ID of admin_test

    def test_change_head_missing_new_head_resident_id(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"effective_date": "2026-11-04"},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_change_head_missing_effective_date(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["member_resident_id"]},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",
        "2026/11/04",
        "04-11-2026",
        "2026-02-30"
    ])
    def test_change_head_invalid_date_format(self, client, auth_headers_admin, household_factory, bad_date):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": bad_date
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_change_head_invalid_resident_id_type(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": "string_not_int",
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_change_head_nonexistent_resident(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": 999999,
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code in (400, 404)
        assert res.json()["code"] in ("NOT_FOUND", "VALIDATION_ERROR")

    def test_change_head_resident_from_different_household(self, client, auth_headers_admin, household_factory):
        h1 = household_factory()
        h2 = household_factory()
        # Attempt to make resident from h2 the head of h1
        res = client.put(
            f"/api/v1/households/{h1['household_id']}/head",
            json={
                "new_head_resident_id": h2["member_resident_id"],
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code in (400, 404)
        assert res.json()["code"] in ("NOT_FOUND", "VALIDATION_ERROR")

    def test_change_head_inactive_household_rejected(self, client, auth_headers_admin, household_factory):
        h = household_factory(status="INACTIVE")
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_change_head_deceased_resident_rejected(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        # Set member resident status to DA_QUA_DOI
        db_session.execute(
            text("UPDATE residents SET residence_status = 'DA_QUA_DOI' WHERE id = :rid"),
            {"rid": h["member_resident_id"]}
        )
        db_session.commit()

        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_change_head_moved_resident_rejected(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        # Set member resident status to DA_CHUYEN_DI
        db_session.execute(
            text("UPDATE residents SET residence_status = 'DA_CHUYEN_DI' WHERE id = :rid"),
            {"rid": h["member_resident_id"]}
        )
        db_session.commit()

        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["member_resident_id"],
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_change_head_already_head_idempotent(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        # Select the same resident who is currently head
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={
                "new_head_resident_id": h["head_resident_id"],
                "effective_date": "2026-11-04"
            },
            headers=auth_headers_admin
        )
        assert res.status_code == 200
        assert res.json()["head_resident_id"] == h["head_resident_id"]

    def test_change_head_two_consecutive_transfers(self, client, auth_headers_admin, household_factory, db_session):
        h = household_factory()
        res1 = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["member_resident_id"], "effective_date": "2026-11-04"},
            headers=auth_headers_admin
        )
        assert res1.status_code == 200
        assert res1.json()["head_resident_id"] == h["member_resident_id"]

        # Transfer back to original head
        res2 = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["head_resident_id"], "effective_date": "2026-11-05"},
            headers=auth_headers_admin
        )
        assert res2.status_code == 200
        assert res2.json()["head_resident_id"] == h["head_resident_id"]

        # Check invariant
        count = db_session.execute(
            text("SELECT COUNT(*) FROM residents WHERE household_id = :hid AND is_head = 1"),
            {"hid": h["household_id"]}
        ).scalar()
        assert count == 1

    def test_change_head_not_found_household(self, client, auth_headers_admin):
        res = client.put(
            "/api/v1/households/999999/head",
            json={"new_head_resident_id": 1, "effective_date": "2026-11-04"},
            headers=auth_headers_admin
        )
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_change_head_negative_household_id(self, client, auth_headers_admin):
        res = client.put(
            "/api/v1/households/-1/head",
            json={"new_head_resident_id": 1, "effective_date": "2026-11-04"},
            headers=auth_headers_admin
        )
        assert res.status_code in (400, 404)
        assert res.json()["code"] in ("NOT_FOUND", "VALIDATION_ERROR")

    def test_change_head_zero_household_id(self, client, auth_headers_admin):
        res = client.put(
            "/api/v1/households/0/head",
            json={"new_head_resident_id": 1, "effective_date": "2026-11-04"},
            headers=auth_headers_admin
        )
        assert res.status_code in (400, 404)
        assert res.json()["code"] in ("NOT_FOUND", "VALIDATION_ERROR")

    def test_change_head_unauthenticated(self, client, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["member_resident_id"], "effective_date": "2026-11-04"}
        )
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_change_head_invalid_token(self, client, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["member_resident_id"], "effective_date": "2026-11-04"},
            headers={"Authorization": "Bearer bad.token.value"}
        )
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_change_head_forbidden_accountant(self, client, auth_headers_accountant, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["member_resident_id"], "effective_date": "2026-11-04"},
            headers=auth_headers_accountant
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_change_head_forbidden_treasurer(self, client, auth_headers_treasurer, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["member_resident_id"], "effective_date": "2026-11-04"},
            headers=auth_headers_treasurer
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_change_head_forbidden_resident(self, client, auth_headers_resident_101, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["member_resident_id"], "effective_date": "2026-11-04"},
            headers=auth_headers_resident_101
        )
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_change_head_password_change_required(self, client, auth_headers_must_change_pw, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": h["member_resident_id"], "effective_date": "2026-11-04"},
            headers=auth_headers_must_change_pw
        )
        assert res.status_code == 403
        assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# ==============================================================================
# SUITE 4: ERROR ENVELOPES & CROSS-CUTTING AUDIT LOGS
# ==============================================================================

class TestUS02CrossCuttingAndEdgeCases:

    def test_standard_error_envelope_structure_on_400(self, client, auth_headers_admin, household_factory):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_email": "invalid_email_format"},
            headers=auth_headers_admin
        )
        assert res.status_code == 400
        body = res.json()
        assert "code" in body
        assert "message" in body
        assert "details" in body
        assert isinstance(body["details"], list)

    def test_standard_error_envelope_structure_on_401(self, client, household_factory):
        h = household_factory()
        res = client.post(f"/api/v1/households/{h['household_id']}/deactivate", json={"reason": "test"})
        assert res.status_code == 401
        body = res.json()
        assert body["code"] == "UNAUTHENTICATED"
        assert "message" in body
        assert "details" in body

    def test_standard_error_envelope_structure_on_403(self, client, auth_headers_accountant, household_factory):
        h = household_factory()
        res = client.put(
            f"/api/v1/households/{h['household_id']}/head",
            json={"new_head_resident_id": 1, "effective_date": "2026-11-04"},
            headers=auth_headers_accountant
        )
        assert res.status_code == 403
        body = res.json()
        assert body["code"] == "FORBIDDEN"
        assert "message" in body
        assert "details" in body

    def test_standard_error_envelope_structure_on_404(self, client, auth_headers_admin):
        res = client.patch(
            "/api/v1/households/999999",
            json={"contact_phone": "0912345678"},
            headers=auth_headers_admin
        )
        assert res.status_code == 404
        body = res.json()
        assert body["code"] == "NOT_FOUND"
        assert "message" in body
        assert "details" in body

    def test_rbac_access_denied_creates_audit_log(self, client, auth_headers_accountant, household_factory, db_session):
        h = household_factory()
        res = client.patch(
            f"/api/v1/households/{h['household_id']}",
            json={"contact_phone": "0988888888"},
            headers=auth_headers_accountant
        )
        assert res.status_code == 403

        # Verify ACCESS_DENIED logged per API contract
        rows = db_session.execute(
            text("SELECT action, user_id FROM audit_logs WHERE action = 'ACCESS_DENIED'")
        ).fetchall()
        assert len(rows) >= 1
        assert rows[-1][0] == "ACCESS_DENIED"
        assert rows[-1][1] == 2  # accountant user_id
