import sqlite3
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import text

from app.core.security import create_access_token


# ==============================================================================
# FIXTURES & BASE SETUP (Using database/bluemoon_debug.db as foundation)
# ==============================================================================

@pytest.fixture(autouse=True)
def load_debug_db(db_session):
    """
    Restore test domain tables from database/bluemoon_debug.db into in-memory SQLite for complete isolation,
    while strictly preserving conftest.py users and roles.
    """
    # 0. Ensure invoices and invoice_items tables exist in test sqlite
    db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            billing_period_id INTEGER,
            household_id INTEGER NOT NULL,
            apartment_id INTEGER,
            apartment_area REAL DEFAULT 70,
            fee_amount REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            previous_debt REAL DEFAULT 0,
            credit_applied REAL DEFAULT 0,
            total_due REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'UNPAID',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """))
    db_session.execute(text("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            fee_type_id INTEGER DEFAULT 1,
            quantity REAL DEFAULT 1,
            unit_price REAL DEFAULT 0,
            gross_amount REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            net_amount REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            description TEXT
        )
    """))
    db_session.commit()

    # 1. Clean domain tables
    for tbl in [
        "invoice_items", "invoices", "apartment_occupancies",
        "residents", "households", "apartments", "audit_logs"
    ]:
        try:
            db_session.execute(text(f"DELETE FROM {tbl}"))
        except Exception:
            pass
    db_session.commit()

    # 2. Copy domain data from database/bluemoon_debug.db
    source = sqlite3.connect("database/bluemoon_debug.db")
    raw_conn = db_session.connection().connection.driver_connection
    src_cursor = source.cursor()
    dest_cursor = raw_conn.cursor()

    domain_tables = [
        "apartments", "households", "apartment_occupancies",
        "residents", "invoices", "invoice_items"
    ]
    for tbl in domain_tables:
        src_cursor.execute(f"SELECT * FROM {tbl}")
        rows = src_cursor.fetchall()
        if rows:
            placeholders = ", ".join(["?"] * len(rows[0]))
            dest_cursor.executemany(f"INSERT INTO {tbl} VALUES ({placeholders})", rows)
    raw_conn.commit()
    source.close()

    # 3. Ensure a treasurer user (id=5) exists for RBAC tests without overwriting users 1..4
    u_treasurer = db_session.execute(text("SELECT id FROM users WHERE id = 5")).fetchone()
    if not u_treasurer:
        db_session.execute(text("""
            INSERT INTO users (id, username, password_hash, full_name, email, role_id, is_active, must_change_password, failed_login_count)
            VALUES (5, 'treasurer_test', 'hash123', 'Thu Quy Test', 'treasurer@bluemoon.local', 3, 1, 0, 0)
        """))
        db_session.commit()

    # Reset any flag on user 1
    db_session.execute(text("UPDATE users SET must_change_password = 0, is_active = 1 WHERE id = 1"))
    db_session.commit()

    yield

    # Teardown: ensure user 1 must_change_password is reset to 0 and drop invoices
    try:
        db_session.execute(text("UPDATE users SET must_change_password = 0, is_active = 1 WHERE id = 1"))
        db_session.execute(text("DROP TABLE IF EXISTS invoice_items"))
        db_session.execute(text("DROP TABLE IF EXISTS invoices"))
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture
def auth_headers_accountant():
    token = create_access_token({
        "sub": "2",
        "username": "accountant_test",
        "role": "ACCOUNTANT",
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_treasurer():
    token = create_access_token({
        "sub": "5",
        "username": "treasurer_test",
        "role": "TREASURER",
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_resident():
    token = create_access_token({
        "sub": "3",
        "username": "resident_101",
        "role": "RESIDENT",
        "household_id": 1,
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


def helper_create_empty_household(db_session, hh_id=100, code="HO-TEST-100", status="ACTIVE"):
    """Helper to insert a valid household that currently holds no apartment."""
    db_session.execute(text(
        "INSERT INTO households (id, household_code, status) VALUES (:id, :code, :status)"
    ), {"id": hh_id, "code": code, "status": status})
    db_session.commit()
    return hh_id


# ==============================================================================
# 1. AUTHENTICATION & RBAC PERMISSION TESTS (11 Test Cases)
# ==============================================================================

def test_transfer_unauthenticated_no_header(client):
    """Calling transfer without Authorization header must return 401 UNAUTHENTICATED."""
    resp = client.post("/api/v1/households/1/transfer", json={
        "new_household_id": 100,
        "effective_date": "2026-11-05"
    })
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "UNAUTHENTICATED"


def test_transfer_unauthenticated_invalid_bearer(client):
    """Calling transfer with an invalid JWT string must return 401 UNAUTHENTICATED."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers={"Authorization": "Bearer invalid.token.payload"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


def test_transfer_unauthenticated_wrong_scheme(client):
    """Calling transfer with Basic auth instead of Bearer must return 401 UNAUTHENTICATED."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


def test_transfer_unauthenticated_empty_token(client):
    """Calling transfer with empty Bearer token must return 401 UNAUTHENTICATED."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers={"Authorization": "Bearer "}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


def test_transfer_unauthenticated_expired_token(client):
    """Calling transfer with an expired token must return 401 UNAUTHENTICATED."""
    token = create_access_token(
        {"sub": "1", "username": "admin_test", "role": "ADMIN"},
        expires_delta=timedelta(seconds=-10)
    )
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


def test_transfer_forbidden_role_resident(client, auth_headers_resident):
    """RESIDENT role is forbidden from transferring apartments (403 FORBIDDEN)."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_resident
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_transfer_forbidden_role_accountant(client, auth_headers_accountant):
    """ACCOUNTANT role is forbidden from transferring apartments (403 FORBIDDEN)."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_accountant
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_transfer_forbidden_role_treasurer(client, auth_headers_treasurer):
    """TREASURER role is forbidden from transferring apartments (403 FORBIDDEN)."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_treasurer
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_transfer_forbidden_role_unknown(client, db_session):
    """User with a non-admin role or newly created unknown role is forbidden (403 FORBIDDEN)."""
    db_session.execute(text("INSERT INTO roles (id, code, name) VALUES (99, 'GUEST', 'Khách')"))
    db_session.execute(text("""
        INSERT INTO users (id, username, password_hash, full_name, role_id, is_active, must_change_password, failed_login_count)
        VALUES (99, 'guest_user', 'hash', 'Khách Test', 99, 1, 0, 0)
    """))
    db_session.commit()
    token = create_access_token({
        "sub": "99",
        "username": "guest_user",
        "role": "GUEST",
        "must_change_password": False,
    })
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_transfer_forbidden_must_change_password(client, db_session):
    """Admin user with must_change_password=True must receive 403 PASSWORD_CHANGE_REQUIRED."""
    try:
        db_session.execute(text("UPDATE users SET must_change_password = 1 WHERE id = 1"))
        db_session.commit()
        token = create_access_token({
            "sub": "1",
            "username": "admin_test",
            "role": "ADMIN",
            "must_change_password": True,
        })
        resp = client.post(
            "/api/v1/households/1/transfer",
            json={"new_household_id": 100, "effective_date": "2026-11-05"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    finally:
        db_session.execute(text("UPDATE users SET must_change_password = 0 WHERE id = 1"))
        db_session.commit()


def test_transfer_rbac_audit_log_access_denied(client, auth_headers_resident, db_session):
    """RBAC Guard must log ACCESS_DENIED in audit_logs when a resident attempts to transfer."""
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_resident
    )
    log = db_session.execute(text(
        "SELECT action, user_id FROM audit_logs WHERE action = 'ACCESS_DENIED' ORDER BY id DESC LIMIT 1"
    )).fetchone()
    assert log is not None
    assert log[0] == "ACCESS_DENIED"


# ==============================================================================
# 2. HTTP METHOD NOT ALLOWED (405) TESTS (4 Test Cases)
# ==============================================================================

def test_transfer_method_get_not_allowed(client, auth_headers_admin):
    """GET /api/v1/households/{id}/transfer is not allowed (405)."""
    resp = client.get("/api/v1/households/1/transfer", headers=auth_headers_admin)
    assert resp.status_code == 405


def test_transfer_method_put_not_allowed(client, auth_headers_admin):
    """PUT /api/v1/households/{id}/transfer is not allowed (405)."""
    resp = client.put("/api/v1/households/1/transfer", headers=auth_headers_admin, json={})
    assert resp.status_code == 405


def test_transfer_method_patch_not_allowed(client, auth_headers_admin):
    """PATCH /api/v1/households/{id}/transfer is not allowed (405)."""
    resp = client.patch("/api/v1/households/1/transfer", headers=auth_headers_admin, json={})
    assert resp.status_code == 405


def test_transfer_method_delete_not_allowed(client, auth_headers_admin):
    """DELETE /api/v1/households/{id}/transfer is not allowed (405)."""
    resp = client.delete("/api/v1/households/1/transfer", headers=auth_headers_admin)
    assert resp.status_code == 405


# ==============================================================================
# 3. PATH PARAMETER VALIDATION (5 Test Cases)
# ==============================================================================

def test_transfer_path_id_string_not_int(client, auth_headers_admin):
    """Path ID non-integer string returns 400, 404, or 422."""
    resp = client.post(
        "/api/v1/households/abc/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 404, 422)


def test_transfer_path_id_float(client, auth_headers_admin):
    """Path ID float returns 400, 404, or 422."""
    resp = client.post(
        "/api/v1/households/1.5/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 404, 422)


def test_transfer_path_id_zero(client, auth_headers_admin):
    """Path ID zero returns 400, 404, or 422."""
    resp = client.post(
        "/api/v1/households/0/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 404, 422)


def test_transfer_path_id_negative(client, auth_headers_admin):
    """Path ID negative returns 400, 404, or 422."""
    resp = client.post(
        "/api/v1/households/-1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 404, 422)


def test_transfer_path_id_sql_injection(client, auth_headers_admin):
    """Path ID with SQL injection characters is rejected safely with 400, 404, or 422."""
    resp = client.post(
        "/api/v1/households/1%20OR%201=1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 404, 422)


# ==============================================================================
# 4. REQUEST BODY SCHEMA VALIDATION (21 Test Cases)
# ==============================================================================

def test_transfer_body_empty(client, auth_headers_admin):
    """Empty body {} violates required fields -> 400 VALIDATION_ERROR."""
    resp = client.post("/api/v1/households/1/transfer", json={}, headers=auth_headers_admin)
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_missing_new_household_id(client, auth_headers_admin):
    """Missing new_household_id violates schema -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_missing_effective_date(client, auth_headers_admin):
    """Missing effective_date violates schema -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_null_new_household_id(client, auth_headers_admin):
    """new_household_id is null -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": None, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_null_effective_date(client, auth_headers_admin):
    """effective_date is null -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": None},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_new_household_id_string(client, auth_headers_admin):
    """new_household_id string value -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": "not_an_id", "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_new_household_id_float(client, auth_headers_admin):
    """new_household_id float value -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 12.34, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_new_household_id_list(client, auth_headers_admin):
    """new_household_id list value -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": [100], "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_new_household_id_dict(client, auth_headers_admin):
    """new_household_id dict value -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": {"id": 100}, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_new_household_id_zero(client, auth_headers_admin):
    """new_household_id is 0 -> rejected as invalid ID (400, 404, or 422)."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 0, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 404, 422)


def test_transfer_body_new_household_id_negative(client, auth_headers_admin):
    """new_household_id is negative -> rejected as invalid ID (400, 404, or 422)."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": -5, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 404, 422)


def test_transfer_body_effective_date_empty_string(client, auth_headers_admin):
    """effective_date is empty string -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": ""},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_effective_date_invalid_format_dmy(client, auth_headers_admin):
    """effective_date in DD-MM-YYYY format instead of YYYY-MM-DD -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "05-11-2026"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_effective_date_invalid_format_slash(client, auth_headers_admin):
    """effective_date with slashes YYYY/MM/DD -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026/11/05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_effective_date_invalid_string(client, auth_headers_admin):
    """effective_date non-date string -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "not-a-valid-date"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_effective_date_impossible_month(client, auth_headers_admin):
    """effective_date month 13 -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-13-01"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_effective_date_impossible_day(client, auth_headers_admin):
    """effective_date Feb 30 -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-02-30"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_effective_date_not_string(client, auth_headers_admin):
    """effective_date integer -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": 20261105},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_reason_invalid_type_int(client, auth_headers_admin):
    """reason integer value instead of string -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05", "reason": 12345},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_reason_invalid_type_list(client, auth_headers_admin):
    """reason list value instead of string -> 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 100, "effective_date": "2026-11-05", "reason": ["some", "reason"]},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_body_not_json(client, auth_headers_admin):
    """Sending non-JSON payload string returns 400 or 422 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        content="not-json-content",
        headers={**auth_headers_admin, "Content-Type": "application/json"}
    )
    assert resp.status_code in (400, 422)


# ==============================================================================
# 5. NOT FOUND (404 NOT_FOUND) TESTS (4 Test Cases)
# ==============================================================================

def test_transfer_source_household_not_found(client, auth_headers_admin):
    """Transferring from non-existent household ID returns 404 NOT_FOUND."""
    resp = client.post(
        "/api/v1/households/99999/transfer",
        json={"new_household_id": 1, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "NOT_FOUND"


def test_transfer_target_household_not_found(client, auth_headers_admin):
    """Transferring to non-existent target household ID returns 404 NOT_FOUND."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 99999, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "NOT_FOUND"


def test_transfer_both_households_not_found(client, auth_headers_admin):
    """Both source and target non-existent returns 404 NOT_FOUND."""
    resp = client.post(
        "/api/v1/households/88888/transfer",
        json={"new_household_id": 99999, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


def test_transfer_404_error_schema_conformance(client, auth_headers_admin):
    """404 Error response conforms strictly to Error schema (code, message, details)."""
    resp = client.post(
        "/api/v1/households/99999/transfer",
        json={"new_household_id": 1, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 404
    data = resp.json()
    assert "code" in data
    assert "message" in data
    assert "details" in data
    assert isinstance(data["details"], list)


# ==============================================================================
# 6. BUSINESS CONFLICTS & DOMAIN VALIDATION (11 Test Cases)
# ==============================================================================

def test_transfer_source_household_has_no_apartment(client, auth_headers_admin, db_session):
    """Source household exists and ACTIVE but currently has no apartment -> 409 HOUSEHOLD_HAS_NO_APARTMENT."""
    empty_hh_id = helper_create_empty_household(db_session, hh_id=101, code="HO-NO-APT")
    target_hh_id = helper_create_empty_household(db_session, hh_id=102, code="HO-TARGET")
    resp = client.post(
        f"/api/v1/households/{empty_hh_id}/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "HOUSEHOLD_HAS_NO_APARTMENT"


def test_transfer_source_household_occupancy_closed_previously(client, auth_headers_admin, db_session):
    """Household previously held an apartment, but occupancy was closed -> 409 or 400."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=103, code="HO-TARGET-103")
    resp = client.post(
        "/api/v1/households/16/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 409)
    assert resp.json()["code"] in ("VALIDATION_ERROR", "HOUSEHOLD_HAS_NO_APARTMENT")


def test_transfer_target_household_already_occupies_apartment(client, auth_headers_admin):
    """Target household 5 already occupies apartment 5 -> 409 APARTMENT_OCCUPIED."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 5, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "APARTMENT_OCCUPIED"


def test_transfer_debt_not_settled_household_2(client, auth_headers_admin, db_session):
    """Household 2 has partially paid debt (invoice 17) -> 409 DEBT_NOT_SETTLED."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=104, code="HO-TARGET-104")
    resp = client.post(
        "/api/v1/households/2/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "DEBT_NOT_SETTLED"


def test_transfer_debt_not_settled_household_3(client, auth_headers_admin, db_session):
    """Household 3 has unpaid invoice 18 -> 409 DEBT_NOT_SETTLED."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=105, code="HO-TARGET-105")
    resp = client.post(
        "/api/v1/households/3/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "DEBT_NOT_SETTLED"


def test_transfer_debt_not_settled_household_4(client, auth_headers_admin, db_session):
    """Household 4 has unpaid invoice 19 -> 409 DEBT_NOT_SETTLED."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=106, code="HO-TARGET-106")
    resp = client.post(
        "/api/v1/households/4/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "DEBT_NOT_SETTLED"


def test_transfer_source_household_inactive(client, auth_headers_admin, db_session):
    """Transfer from an INACTIVE household must return 400 VALIDATION_ERROR or 409."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=107, code="HO-TARGET-107")
    resp = client.post(
        "/api/v1/households/16/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code in (400, 409)


def test_transfer_target_household_inactive(client, auth_headers_admin):
    """Transfer to an INACTIVE household (household 16) must return 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 16, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_same_household(client, auth_headers_admin):
    """Transfer to the same household ID must be rejected with 400 VALIDATION_ERROR."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 1, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_effective_date_before_start_date(client, auth_headers_admin, db_session):
    """effective_date earlier than start_date (2024-01-01) violates chronological integrity (400)."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=108, code="HO-TARGET-108")
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2023-01-01"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_transfer_409_error_schema_conformance(client, auth_headers_admin):
    """409 Conflict Error conforms to Error schema (code, message, details)."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 5, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 409
    data = resp.json()
    assert "code" in data
    assert "message" in data
    assert "details" in data
    assert isinstance(data["details"], list)


# ==============================================================================
# 7. HAPPY PATHS & STATE TRANSITIONS (15 Test Cases)
# ==============================================================================

def test_transfer_happy_path_success(client, auth_headers_admin, db_session):
    """Happy path transfer: household 1 (0 debt) transfers apartment 1 to new household -> 200 OK."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=110, code="HO-TARGET-110")
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05", "reason": "Bán căn hộ"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200


def test_transfer_response_schema_fields(client, auth_headers_admin, db_session):
    """Response conforms to Household schema with all expected keys."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=111, code="HO-TARGET-111")
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200
    data = resp.json()
    for field in ["id", "household_code", "status", "apartment_id", "apartment_code", "floor", "area_m2", "created_at", "updated_at"]:
        assert field in data, f"Missing {field} in Household response"


def test_transfer_response_returns_target_household(client, auth_headers_admin, db_session):
    """Response returns the new household now associated with the transferred apartment."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=112, code="HO-TARGET-112")
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == target_hh_id
    assert data["household_code"] == "HO-TARGET-112"
    assert data["apartment_id"] == 1
    assert data["apartment_code"] == "P.0101"


def test_transfer_db_old_occupancy_closed(client, auth_headers_admin, db_session):
    """Old household's apartment_occupancies record is closed with end_date = effective_date."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=113, code="HO-TARGET-113")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05", "reason": "Bàn giao nhà"},
        headers=auth_headers_admin
    )
    occ = db_session.execute(text(
        "SELECT end_date, end_reason FROM apartment_occupancies WHERE household_id = 1"
    )).fetchone()
    assert occ is not None
    assert str(occ[0]) == "2026-11-05"
    assert occ[1] == "Bàn giao nhà"


def test_transfer_db_new_occupancy_opened(client, auth_headers_admin, db_session):
    """New household's apartment_occupancies record is created with start_date = effective_date and end_date NULL."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=114, code="HO-TARGET-114")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    occ = db_session.execute(text(
        "SELECT apartment_id, start_date, end_date FROM apartment_occupancies WHERE household_id = :hid"
    ), {"hid": target_hh_id}).fetchone()
    assert occ is not None
    assert occ[0] == 1
    assert str(occ[1]) == "2026-11-05"
    assert occ[2] is None


def test_transfer_get_old_household_after(client, auth_headers_admin, db_session):
    """Querying GET /households/{old_id} shows apartment_id is now None."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=115, code="HO-TARGET-115")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    get_resp = client.get("/api/v1/households/1", headers=auth_headers_admin)
    assert get_resp.status_code == 200
    assert get_resp.json()["apartment_id"] is None


def test_transfer_get_new_household_after(client, auth_headers_admin, db_session):
    """Querying GET /households/{new_id} shows apartment_id is now 1."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=116, code="HO-TARGET-116")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    get_resp = client.get(f"/api/v1/households/{target_hh_id}", headers=auth_headers_admin)
    assert get_resp.status_code == 200
    assert get_resp.json()["apartment_id"] == 1


def test_transfer_without_optional_reason(client, auth_headers_admin, db_session):
    """Successful transfer when omitting the optional reason field -> 200 OK."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=117, code="HO-TARGET-117")
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200


def test_transfer_with_empty_reason(client, auth_headers_admin, db_session):
    """Successful transfer with reason='' -> 200 OK."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=118, code="HO-TARGET-118")
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05", "reason": ""},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200


def test_transfer_with_null_reason(client, auth_headers_admin, db_session):
    """Successful transfer with reason=None -> 200 OK."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=119, code="HO-TARGET-119")
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05", "reason": None},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200


def test_transfer_with_vietnamese_unicode_reason(client, auth_headers_admin, db_session):
    """Successful transfer with full Vietnamese unicode text in reason -> 200 OK."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=120, code="HO-TARGET-120")
    reason_vn = "Chuyển nhượng quyền sở hữu căn hộ theo hợp đồng mua bán số 123/2026/HĐMB"
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05", "reason": reason_vn},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200
    occ = db_session.execute(text(
        "SELECT end_reason FROM apartment_occupancies WHERE household_id = 1"
    )).fetchone()
    assert occ[0] == reason_vn


def test_transfer_with_long_reason(client, auth_headers_admin, db_session):
    """Successful transfer with a long explanation (500 characters) in reason -> 200 OK."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=121, code="HO-TARGET-121")
    long_reason = "Lý do chuyển nhượng chi tiết: " + ("A" * 450)
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05", "reason": long_reason},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200


def test_transfer_effective_date_equal_start_date(client, auth_headers_admin, db_session):
    """Boundary test: effective_date exactly equals the start_date of the old household -> 200 OK."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=122, code="HO-TARGET-122")
    # Household 1 start_date in debug DB is 2024-01-01
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2024-01-01", "reason": "Chuyển trong ngày"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200


def test_transfer_future_effective_date(client, auth_headers_admin, db_session):
    """Transfer with a valid future effective_date (e.g. 2026-12-31) -> 200 OK."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=123, code="HO-TARGET-123")
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-12-31"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200


def test_transfer_chain_sequential(client, auth_headers_admin, db_session):
    """Sequential transfer: HH1 -> HH124 on 2026-06-01, then HH124 -> HH125 on 2026-10-01."""
    hh_b = helper_create_empty_household(db_session, hh_id=124, code="HO-CHAIN-B")
    hh_c = helper_create_empty_household(db_session, hh_id=125, code="HO-CHAIN-C")

    # Step 1: 1 -> B
    r1 = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": hh_b, "effective_date": "2026-06-01", "reason": "Bán lần 1"},
        headers=auth_headers_admin
    )
    assert r1.status_code == 200

    # Step 2: B -> C
    r2 = client.post(
        f"/api/v1/households/{hh_b}/transfer",
        json={"new_household_id": hh_c, "effective_date": "2026-10-01", "reason": "Bán lần 2"},
        headers=auth_headers_admin
    )
    assert r2.status_code == 200
    assert r2.json()["apartment_id"] == 1


# ==============================================================================
# 8. AUDIT LOGGING & AUDIT TRAIL (5 Test Cases)
# ==============================================================================

def test_transfer_creates_audit_log(client, auth_headers_admin, db_session):
    """Transfer apartment must create an audit_logs entry with action='TRANSFER_APARTMENT'."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=126, code="HO-TARGET-126")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    count = db_session.execute(text(
        "SELECT count(*) FROM audit_logs WHERE action = 'TRANSFER_APARTMENT'"
    )).scalar()
    assert count >= 1


def test_transfer_audit_log_user_id(client, auth_headers_admin, db_session):
    """Audit log entry user_id must match the admin caller's user_id (1)."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=127, code="HO-TARGET-127")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    log = db_session.execute(text(
        "SELECT user_id FROM audit_logs WHERE action = 'TRANSFER_APARTMENT' ORDER BY id DESC LIMIT 1"
    )).fetchone()
    assert log is not None
    assert log[0] == 1


def test_transfer_audit_log_entity_info(client, auth_headers_admin, db_session):
    """Audit log entry entity_type is HOUSEHOLD and entity_id is the source household ID."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=128, code="HO-TARGET-128")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    log = db_session.execute(text(
        "SELECT entity_type, entity_id FROM audit_logs WHERE action = 'TRANSFER_APARTMENT' ORDER BY id DESC LIMIT 1"
    )).fetchone()
    assert log is not None
    assert log[0] == "HOUSEHOLD"
    assert log[1] == "1"


def test_transfer_audit_log_reason(client, auth_headers_admin, db_session):
    """Audit log entry records the transfer reason given in request."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=129, code="HO-TARGET-129")
    custom_reason = "Ghi audit log ly do chuyen nhuong"
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05", "reason": custom_reason},
        headers=auth_headers_admin
    )
    log = db_session.execute(text(
        "SELECT reason FROM audit_logs WHERE action = 'TRANSFER_APARTMENT' ORDER BY id DESC LIMIT 1"
    )).fetchone()
    assert log is not None
    assert log[0] == custom_reason


def test_transfer_audit_log_values_recorded(client, auth_headers_admin, db_session):
    """Audit log old_value and new_value reflect the transfer details."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=130, code="HO-TARGET-130")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    log = db_session.execute(text(
        "SELECT old_value, new_value FROM audit_logs WHERE action = 'TRANSFER_APARTMENT' ORDER BY id DESC LIMIT 1"
    )).fetchone()
    assert log is not None
    assert log[0] is not None
    assert log[1] is not None


# ==============================================================================
# 9. DATA INVARIANTS & ACID INTEGRITY (AC-03.1) (8 Test Cases)
# ==============================================================================

def test_transfer_preserves_old_household_invoices(client, auth_headers_admin, db_session):
    """
    AC-03.1: 100% of old household's financial invoices are preserved under old household.
    Household 1 has invoices 1 and 3 in bluemoon_debug.db.
    """
    initial_invoices = db_session.execute(text(
        "SELECT id, total_due, paid_amount, status FROM invoices WHERE household_id = 1 ORDER BY id"
    )).fetchall()
    assert len(initial_invoices) >= 1

    target_hh_id = helper_create_empty_household(db_session, hh_id=131, code="HO-TARGET-131")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )

    # Invoices for household 1 must remain identical
    after_invoices = db_session.execute(text(
        "SELECT id, total_due, paid_amount, status FROM invoices WHERE household_id = 1 ORDER BY id"
    )).fetchall()
    assert initial_invoices == after_invoices

    # New household has no transferred invoices
    new_hh_invoices = db_session.execute(text(
        "SELECT count(*) FROM invoices WHERE household_id = :hid"
    ), {"hid": target_hh_id}).scalar()
    assert new_hh_invoices == 0


def test_transfer_preserves_old_household_residents(client, auth_headers_admin, db_session):
    """Residents of old household remain attached to old household, not moved."""
    initial_residents = db_session.execute(text(
        "SELECT id, full_name, is_head FROM residents WHERE household_id = 1 ORDER BY id"
    )).fetchall()
    assert len(initial_residents) >= 1

    target_hh_id = helper_create_empty_household(db_session, hh_id=132, code="HO-TARGET-132")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )

    after_residents = db_session.execute(text(
        "SELECT id, full_name, is_head FROM residents WHERE household_id = 1 ORDER BY id"
    )).fetchall()
    assert initial_residents == after_residents


def test_transfer_preserves_new_household_residents(client, auth_headers_admin, db_session):
    """Residents already belonging to target household remain intact after receiving apartment."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=133, code="HO-TARGET-133")
    db_session.execute(text("""
        INSERT INTO residents (id, household_id, full_name, date_of_birth, gender, is_head, residence_status, is_deleted)
        VALUES (9901, 133, 'Chủ Nhà Mới', '1990-01-01', 'NAM', 1, 'THUONG_TRU', 0)
    """))
    db_session.commit()

    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )

    new_residents = db_session.execute(text(
        "SELECT full_name, is_head FROM residents WHERE household_id = :hid"
    ), {"hid": target_hh_id}).fetchall()
    assert len(new_residents) == 1
    assert new_residents[0][0] == "Chủ Nhà Mới"


def test_transfer_old_household_cannot_transfer_again(client, auth_headers_admin, db_session):
    """After transferring, old household no longer has apartment and cannot transfer again (409)."""
    target_hh_1 = helper_create_empty_household(db_session, hh_id=134, code="HO-TARGET-134")
    target_hh_2 = helper_create_empty_household(db_session, hh_id=135, code="HO-TARGET-135")

    # First transfer succeeds
    r1 = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_1, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert r1.status_code == 200

    # Second transfer from same source household must fail with 409 HOUSEHOLD_HAS_NO_APARTMENT
    r2 = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_2, "effective_date": "2026-11-06"},
        headers=auth_headers_admin
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "HOUSEHOLD_HAS_NO_APARTMENT"


def test_transfer_transaction_atomicity_on_target_not_found(client, auth_headers_admin, db_session):
    """When target household does not exist, transaction rolls back and old occupancy is untouched."""
    initial_occ = db_session.execute(text(
        "SELECT end_date FROM apartment_occupancies WHERE household_id = 1"
    )).scalar()
    assert initial_occ is None

    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 99999, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 404

    after_occ = db_session.execute(text(
        "SELECT end_date FROM apartment_occupancies WHERE household_id = 1"
    )).scalar()
    assert after_occ is None


def test_transfer_transaction_atomicity_on_debt_failure(client, auth_headers_admin, db_session):
    """When transfer is rejected due to debt, no new occupancy record is inserted."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=136, code="HO-TARGET-136")

    resp = client.post(
        "/api/v1/households/2/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "DEBT_NOT_SETTLED"

    new_occ = db_session.execute(text(
        "SELECT count(*) FROM apartment_occupancies WHERE household_id = :hid"
    ), {"hid": target_hh_id}).scalar()
    assert new_occ == 0


def test_transfer_transaction_atomicity_on_target_occupied_failure(client, auth_headers_admin, db_session):
    """When transfer fails because target is occupied, source occupancy is untouched."""
    resp = client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": 5, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "APARTMENT_OCCUPIED"

    occ = db_session.execute(text(
        "SELECT end_date FROM apartment_occupancies WHERE household_id = 1"
    )).scalar()
    assert occ is None


def test_transfer_apartment_physical_unit_remains_active(client, auth_headers_admin, db_session):
    """Transferring apartment changes resident occupancy, but physical apartment remains ACTIVE."""
    target_hh_id = helper_create_empty_household(db_session, hh_id=137, code="HO-TARGET-137")
    client.post(
        "/api/v1/households/1/transfer",
        json={"new_household_id": target_hh_id, "effective_date": "2026-11-05"},
        headers=auth_headers_admin
    )
    apt_status = db_session.execute(text(
        "SELECT status FROM apartments WHERE id = 1"
    )).scalar()
    assert apt_status == "ACTIVE"
