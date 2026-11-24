"""Kiểm tra tự động sai lệch route/method giữa FastAPI và docs/openapi.yaml (Layer 1)."""

import re
from pathlib import Path
from typing import Set, Tuple

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_YAML_PATH = REPO_ROOT / "docs" / "openapi.yaml"

# Endpoint tiện ích Sprint 1 ngoài OpenAPI (được phép rõ ràng để phát hiện drift mới ngoài dự kiến).
KNOWN_NON_SPEC_ROUTES: Set[Tuple[str, str]] = {
    ("/fee-types/{id}", "get"),
}

_PARAM_PATTERN = re.compile(r"\{[^}]+\}")
_HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def _normalize_path(path: str) -> str:
    return _PARAM_PATTERN.sub("{id}", path)


def _extract_spec_operations() -> Set[Tuple[str, str]]:
    lines = OPENAPI_YAML_PATH.read_text(encoding="utf-8").splitlines()
    in_paths = False
    current_path = None
    ops: Set[Tuple[str, str]] = set()

    for line in lines:
        if line == "paths:":
            in_paths = True
            continue
        if in_paths and line and not line.startswith(" "):
            break
        if not in_paths:
            continue

        path_match = re.match(r"^  (/[^:]+):\s*$", line)
        if path_match:
            current_path = _normalize_path(path_match.group(1))
            continue

        method_match = re.match(r"^    (get|post|put|patch|delete):\s*$", line)
        if method_match and current_path:
            ops.add((current_path, method_match.group(1)))

    return ops


def _extract_app_operations() -> Set[Tuple[str, str]]:
    schema = app.openapi()
    ops: Set[Tuple[str, str]] = set()
    for path, methods in schema.get("paths", {}).items():
        if not path.startswith("/api/v1/") or path.startswith("/api/v1/test/") or path == "/api/v1/health":
            continue
        rel_path = _normalize_path(path.removeprefix("/api/v1"))
        for method in methods:
            m_lower = method.lower()
            if m_lower in _HTTP_METHODS:
                ops.add((rel_path, m_lower))
    return ops


def test_openapi_parser_coverage_sanity() -> None:
    """Đảm bảo parser đọc đủ routes từ cả FastAPI và docs/openapi.yaml."""
    app_ops = _extract_app_operations()
    spec_ops = _extract_spec_operations()
    assert len(app_ops) >= 50, f"Số route FastAPI bất thường: {len(app_ops)}"
    assert len(spec_ops) >= 90, f"Số route OpenAPI bất thường: {len(spec_ops)}"


def test_fastapi_routes_conform_to_openapi_spec() -> None:
    """Mọi route FastAPI /api/v1/* (trừ allowlist) đều phải khớp path + method trong docs/openapi.yaml."""
    app_ops = _extract_app_operations()
    spec_ops = _extract_spec_operations()
    unexpected_drift = sorted((app_ops - KNOWN_NON_SPEC_ROUTES) - spec_ops)
    assert unexpected_drift == [], (
        "Phát hiện route/method trên FastAPI lệch khỏi docs/openapi.yaml: "
        f"{unexpected_drift}"
    )
