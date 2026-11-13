"""
Unit and Integration Tests for Enterprise RBAC, HS256 JWT Auth & Multi-Tenant Isolation.
"""

from pathlib import Path
import sys
import time
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.api.server import app
from src.api.security import (
    PasswordHasher,
    JWTEngine,
    AuthError,
    SecurityRegistry,
    role_has_permission,
)

client = TestClient(app)


def _login_as(email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()


def test_password_hasher_pbkdf2():
    """Verify salted PBKDF2-HMAC-SHA256 hashing and constant-time check."""
    hashed = PasswordHasher.hash_password("SuperSecretPassword99!")
    assert hashed.startswith("pbkdf2_sha256$")
    assert PasswordHasher.verify_password("SuperSecretPassword99!", hashed) is True
    assert PasswordHasher.verify_password("WrongPassword", hashed) is False
    assert PasswordHasher.verify_password("SuperSecretPassword99!", "corrupt_hash") is False


def test_jwt_sign_verify_tamper_and_expiry():
    """Verify HS256 JWT signing, payload decoding, tamper detection, and expiration."""
    jwt_engine = JWTEngine(secret="unit-test-secret-key")
    token = jwt_engine.create_access_token(
        subject="usr_test",
        email="tester@nexusretail.ai",
        name="Unit Tester",
        role="lead_ds",
        tenant_id="tenant_uk_flagship",
        permissions=["mlops:retrain"],
        expires_minutes=15,
    )
    assert len(token.split(".")) == 3

    decoded = jwt_engine.decode_token(token)
    assert decoded["sub"] == "usr_test"
    assert decoded["role"] == "lead_ds"
    assert decoded["tenant_id"] == "tenant_uk_flagship"

    # Tamper payload section
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}A.{parts[2]}"
    with pytest.raises(AuthError):
        jwt_engine.decode_token(tampered)

    # Expired token
    expired_token = jwt_engine.create_access_token(
        subject="usr_exp",
        email="exp@nexusretail.ai",
        name="Expired",
        role="admin",
        tenant_id="tenant_uk_flagship",
        permissions=["*"],
        expires_minutes=-1,
    )
    with pytest.raises(AuthError):
        jwt_engine.decode_token(expired_token)


def test_role_permission_matrix():
    """Verify granular permission scopes across the 4 operational roles."""
    assert role_has_permission("admin", "tenants:manage") is True
    assert role_has_permission("admin", "anything:at_all") is True
    assert role_has_permission("lead_ds", "mlops:retrain") is True
    assert role_has_permission("lead_ds", "tenants:manage") is False
    assert role_has_permission("growth", "campaigns:dispatch") is True
    assert role_has_permission("growth", "mlops:retrain") is False
    assert role_has_permission("supply", "inventory:write") is True
    assert role_has_permission("supply", "experiments:run") is False


def test_api_login_me_and_logout_revocation():
    """Assert login issues valid JWT, /me decodes claims, and /logout revokes JTI."""
    # Bad password
    bad = client.post("/api/v1/auth/login", json={"email": "admin@nexusretail.ai", "password": "wrongpassword"})
    assert bad.status_code == 401

    # Unauthenticated /me blocked
    no_auth = client.get("/api/v1/auth/me")
    assert no_auth.status_code == 401

    # Valid login
    login_data = _login_as("ds@nexusretail.ai", "NexusDS2026!")
    token = login_data["access_token"]
    assert login_data["user"]["role"] == "lead_ds"

    # Check /me
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["principal"]["email"] == "ds@nexusretail.ai"
    assert me.json()["principal"]["role"] == "lead_ds"

    # Logout & verify JTI revoked
    out = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert out.status_code == 200

    after_logout = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert after_logout.status_code == 401


def test_api_rbac_enforcement_by_role():
    """Assert role-scoped authorization allows permitted endpoints and returns 403 on restricted ones."""
    growth_token = _login_as("growth@nexusretail.ai", "NexusGrowth2026!")["access_token"]
    supply_token = _login_as("supply@nexusretail.ai", "NexusOps2026!")["access_token"]
    ds_token = _login_as("ds@nexusretail.ai", "NexusDS2026!")["access_token"]
    admin_token = _login_as("admin@nexusretail.ai", "NexusAdmin2026!")["access_token"]

    # Growth CAN dispatch campaigns, CANNOT retrain MLOps models or create tenants
    ok_camp = client.post(
        "/api/v1/campaigns/dispatch",
        headers={"Authorization": f"Bearer {growth_token}"},
        json={
            "campaign_name": "Growth Authorized Wave",
            "audience_segment": "At-Risk VIPs",
            "audience_size": 20,
            "revenue_target_gbp": 5000.0,
            "discount_pct": 15,
            "channels": ["email"],
        },
    )
    assert ok_camp.status_code == 200

    deny_retrain = client.post(
        "/api/v1/mlops/retrain",
        headers={"Authorization": f"Bearer {growth_token}"},
    )
    assert deny_retrain.status_code == 403

    deny_tenant = client.post(
        "/api/v1/auth/tenants",
        headers={"Authorization": f"Bearer {growth_token}"},
        json={"name": "Unauthorized Org", "country": "France", "currency": "EUR"},
    )
    assert deny_tenant.status_code == 403

    # Supply CANNOT run pricing A/B experiments
    deny_exp = client.post(
        "/api/v1/pricing/run-ab-experiment",
        headers={"Authorization": f"Bearer {supply_token}"},
        json={"experiment_name": "Supply Blocked Test", "category": "Kitchen & Dining", "price_change_pct": 5.0},
    )
    assert deny_exp.status_code == 403

    # Lead DS CAN retrain MLOps, CANNOT rotate Shopify secrets
    ok_retrain = client.post("/api/v1/mlops/retrain", headers={"Authorization": f"Bearer {ds_token}"})
    assert ok_retrain.status_code == 200

    deny_secret = client.post(
        "/api/v1/integrations/configure-secret",
        headers={"Authorization": f"Bearer {ds_token}"},
        json={"provider": "shopify", "secret": "new_ds_attempt_123"},
    )
    assert deny_secret.status_code == 403

    # Admin succeeds on tenant creation
    ok_secret = client.post(
        "/api/v1/integrations/configure-secret",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"provider": "shopify", "secret": "shpss_test_secret_key_nexus_2026"},
    )
    assert ok_secret.status_code == 200


def test_api_multi_tenant_isolation_and_switching():
    """Verify non-admin tokens cannot spoof X-Tenant-ID or switch tenants, while admins can."""
    growth_token = _login_as("growth@nexusretail.ai", "NexusGrowth2026!")["access_token"]
    admin_token = _login_as("admin@nexusretail.ai", "NexusAdmin2026!")["access_token"]

    # Growth is pinned to tenant_eu_nordics; spoofing X-Tenant-ID: tenant_uk_flagship must 403
    spoof_res = client.post(
        "/api/v1/campaigns/dispatch",
        headers={
            "Authorization": f"Bearer {growth_token}",
            "X-Tenant-ID": "tenant_uk_flagship",
        },
        json={
            "campaign_name": "Cross-Tenant Spoof Attempt",
            "audience_segment": "At-Risk VIPs",
            "audience_size": 10,
            "revenue_target_gbp": 1000.0,
            "discount_pct": 10,
            "channels": ["email"],
        },
    )
    assert spoof_res.status_code == 403

    # Growth cannot switch tenants
    switch_deny = client.post(
        "/api/v1/auth/switch-tenant",
        headers={"Authorization": f"Bearer {growth_token}"},
        json={"tenant_id": "tenant_uk_flagship"},
    )
    assert switch_deny.status_code == 403

    # Admin creates new tenant and switches into it
    create_res = client.post(
        "/api/v1/auth/tenants",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Nordic Home Partner", "country": "Sweden", "currency": "SEK", "plan": "Enterprise"},
    )
    assert create_res.status_code == 201
    new_tid = create_res.json()["tenant"]["tenant_id"]

    switch_ok = client.post(
        "/api/v1/auth/switch-tenant",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tenant_id": new_tid},
    )
    assert switch_ok.status_code == 200
    new_jwt = switch_ok.json()["access_token"]

    me_new = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_jwt}"})
    assert me_new.status_code == 200
    assert me_new.json()["principal"]["tenant_id"] == new_tid


def test_api_key_issuance_authentication_and_revocation():
    """Verify multi-tenant API key minting, X-API-Key authentication, and revocation."""
    admin_token = _login_as("admin@nexusretail.ai", "NexusAdmin2026!")["access_token"]

    mint_res = client.post(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"label": "CI Pricing Integration Bot", "tenant_id": "tenant_uk_flagship", "role": "lead_ds"},
    )
    assert mint_res.status_code == 201
    key_obj = mint_res.json()["api_key"]
    raw_secret = key_obj["raw_secret"]
    key_id = key_obj["key_id"]
    assert raw_secret.startswith("nxk_live_")

    # Authenticate with X-API-Key
    me_key = client.get("/api/v1/auth/me", headers={"X-API-Key": raw_secret})
    assert me_key.status_code == 200
    assert me_key.json()["principal"]["auth_method"] == "api_key"
    assert me_key.json()["principal"]["role"] == "lead_ds"

    # Key respects RBAC scope (lead_ds key cannot create tenants)
    deny_key = client.post(
        "/api/v1/auth/tenants",
        headers={"X-API-Key": raw_secret},
        json={"name": "Blocked Org", "country": "UK", "currency": "GBP"},
    )
    assert deny_key.status_code == 403

    # Revoke key and verify rejection
    rev_res = client.delete(f"/api/v1/auth/api-keys/{key_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert rev_res.status_code == 200
    assert rev_res.json()["api_key"]["active"] is False

    after_rev = client.get("/api/v1/auth/me", headers={"X-API-Key": raw_secret})
    assert after_rev.status_code == 401


def test_strict_rbac_policy_toggle_and_audit_stream():
    """Assert toggling strict_rbac_enabled blocks anonymous mutations with 401 and audits events."""
    admin_token = _login_as("admin@nexusretail.ai", "NexusAdmin2026!")["access_token"]
    try:
        pol = client.post(
            "/api/v1/auth/security-policy",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"strict_rbac_enabled": True},
        )
        assert pol.status_code == 200
        assert pol.json()["strict_rbac_enabled"] is True

        # Anonymous request now blocked with 401
        anon_retrain = client.post("/api/v1/mlops/retrain")
        assert anon_retrain.status_code == 401

        # Authenticated admin request succeeds
        auth_retrain = client.post("/api/v1/mlops/retrain", headers={"Authorization": f"Bearer {admin_token}"})
        assert auth_retrain.status_code == 200

        # Audit stream contains security events
        audit = client.get("/api/v1/auth/audit-stream", headers={"Authorization": f"Bearer {admin_token}"})
        assert audit.status_code == 200
        events = audit.json()["events"]
        assert len(events) > 0
        assert any(ev["event_type"] == "POLICY_UPDATED" for ev in events)
    finally:
        # Always restore dev_open default so other suites remain unaffected
        SecurityRegistry().strict_rbac_enabled = False


def test_api_rbac_matrix_and_key_list_isolation():
    """Verify public RBAC matrix structure and tenant-scoped API key listing."""
    mat = client.get("/api/v1/auth/rbac-matrix")
    assert mat.status_code == 200
    data = mat.json()
    assert set(["admin", "lead_ds", "growth", "supply"]).issubset(data["roles"].keys())
    assert len(data["tenants"]) >= 3

    # Growth user (eu_nordics) only sees keys scoped to tenant_eu_nordics
    growth_token = _login_as("growth@nexusretail.ai", "NexusGrowth2026!")["access_token"]
    keys_res = client.get("/api/v1/auth/api-keys", headers={"Authorization": f"Bearer {growth_token}"})
    assert keys_res.status_code == 200
    for k in keys_res.json()["api_keys"]:
        assert k["tenant_id"] == "tenant_eu_nordics"
        assert "key_hash" not in k
        assert "raw_secret" not in k


def test_cross_tenant_key_management_guard():
    """Verify non-admin cannot issue or revoke keys across another tenant."""
    growth_principal = {"email": "growth@nexusretail.ai", "role": "growth", "tenant_id": "tenant_eu_nordics"}
    reg = SecurityRegistry()
    with pytest.raises(AuthError) as exc_issue:
        reg.issue_api_key("Rogue Key", "tenant_uk_flagship", "growth", actor=growth_principal)
    assert exc_issue.value.status_code == 403

    with pytest.raises(AuthError) as exc_rev:
        reg.revoke_api_key("key_uk_pos_prod", actor=growth_principal)
    assert exc_rev.value.status_code == 403


def test_prism_retail_identity_authentication():
    """Verify primary Prism Retail branding credentials authenticate successfully."""
    login_data = _login_as("admin@prismretail.ai", "PrismAdmin2026!")
    assert "access_token" in login_data
    assert login_data["user"]["role"] == "admin"
    assert login_data["user"]["email"] == "admin@prismretail.ai"
    assert "Prism" in login_data["active_tenant"]["name"]


