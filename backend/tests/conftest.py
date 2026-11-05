import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.base import Base
from app.models.user import AuditLog, BackupJob, Role, User

# In-memory SQLite Database dedicated for fast, isolated testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables in memory once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        # Seed default roles
        roles_data = [
            Role(id=1, code="ADMIN", name="Ban quản trị"),
            Role(id=2, code="ACCOUNTANT", name="Kế toán"),
            Role(id=3, code="TREASURER", name="Thủ quỹ"),
            Role(id=4, code="RESIDENT", name="Cư dân"),
        ]
        db.add_all(roles_data)
        db.commit()

        # Seed sample test users
        users_data = [
            User(
                id=1,
                username="admin_test",
                password_hash=get_password_hash("AdminPass123!"),
                full_name="Quản Trị Viên Test",
                email="admin@bluemoon.local",
                role_id=1,
                is_active=True,
                must_change_password=False
            ),
            User(
                id=2,
                username="accountant_test",
                password_hash=get_password_hash("AccPass123!"),
                full_name="Kế Toán Test",
                email="accountant@bluemoon.local",
                role_id=2,
                is_active=True,
                must_change_password=False
            ),
            User(
                id=3,
                username="resident_101",
                password_hash=get_password_hash("ResPass123!"),
                full_name="Cư Dân Hộ 101",
                email="resident101@bluemoon.local",
                role_id=4,
                household_id=101,
                is_active=True,
                must_change_password=False
            ),
            User(
                id=4,
                username="resident_102",
                password_hash=get_password_hash("ResPass123!"),
                full_name="Cư Dân Hộ 102",
                email="resident102@bluemoon.local",
                role_id=4,
                household_id=102,
                is_active=True,
                must_change_password=False
            ),
        ]
        db.add_all(users_data)
        db.commit()
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Provide a clean transactional session for each test."""
    session = TestingSessionLocal()
    yield session
    # Dọn dẹp audit_logs và reset trạng thái users sau mỗi test
    try:
        session.query(AuditLog).delete()
        session.query(BackupJob).delete()
        session.query(User).update({
            User.failed_login_count: 0,
            User.locked_until: None,
            User.is_active: True
        })
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Provide a TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers_admin(db_session):
    """Generate auth headers for admin_test."""
    token = create_access_token({
        "sub": "1",
        "username": "admin_test",
        "role": "ADMIN",
        "must_change_password": False
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_resident_101(db_session):
    """Generate auth headers for resident of household 101."""
    token = create_access_token({
        "sub": "3",
        "username": "resident_101",
        "role": "RESIDENT",
        "household_id": 101,
        "must_change_password": False
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_resident_102(db_session):
    """Generate auth headers for resident of household 102."""
    token = create_access_token({
        "sub": "4",
        "username": "resident_102",
        "role": "RESIDENT",
        "household_id": 102,
        "must_change_password": False
    })
    return {"Authorization": f"Bearer {token}"}
