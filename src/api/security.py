"""
Enterprise RBAC, HS256 JWT Authentication & Multi-Tenant Security Engine.

Provides zero-dependency cryptographic authentication and multi-tenant isolation:
1. PasswordHasher: PBKDF2-HMAC-SHA256 salted password hashing and constant-time verification.
2. JWTEngine: RFC 7519 HS256 compact JWT issuance, verification, expiration, and JTI revocation.
3. RBAC Matrix: Role-based permission scopes across Admin, Lead DS, Growth, and Supply roles.
4. SecurityRegistry: Singleton store for multi-tenant workspaces, hashed API keys, user directory,
   strict RBAC enforcement policy, and server-side security audit stream.
5. FastAPI Dependencies: `get_current_principal` and `require_permission` enforcing 401/403 semantics.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import Header, HTTPException, Request, status

from src.utils.state_store import get_state_store

# -----------------------------------------------------------------------------
# Cryptographic Helpers (PBKDF2-SHA256 & HS256 JWT)
# -----------------------------------------------------------------------------
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "prism-retail"
DEFAULT_JWT_SECRET = os.environ.get(
    "PRISM_JWT_SECRET",
    os.environ.get("NEXUS_JWT_SECRET", "prism-retail-enterprise-jwt-signing-key-v3"),
)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


class AuthError(Exception):
    """Raised on authentication (401) or authorization (403) failures."""

    def __init__(self,
                 message: str,
                 status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class PasswordHasher:
    """Salted PBKDF2-HMAC-SHA256 password hashing helper."""
    ITERATIONS = 100_000

    @classmethod
    def hash_password(cls, password: str, salt: Optional[str] = None) -> str:
        salt_hex = salt or secrets.token_hex(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_hex.encode("utf-8"),
            cls.ITERATIONS,
        ).hex()
        return f"pbkdf2_sha256${cls.ITERATIONS}${salt_hex}${derived}"

    @classmethod
    def verify_password(cls, plain_password: str, encoded_hash: str) -> bool:
        try:
            algo, iter_str, salt_hex, expected_hex = encoded_hash.split("$", 3)
            if algo != "pbkdf2_sha256":
                return False
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt_hex.encode("utf-8"),
                int(iter_str),
            ).hex()
            return hmac.compare_digest(derived, expected_hex)
        except Exception:
            return False


class JWTEngine:
    """RFC 7519 HS256 JWT signer and verifier using standard-library HMAC-SHA256."""

    def __init__(self, secret: str = DEFAULT_JWT_SECRET):
        self.secret = secret

    def create_access_token(
        self,
        subject: str,
        email: str,
        name: str,
        role: str,
        tenant_id: str,
        permissions: List[str],
        expires_minutes: int = 120,
    ) -> str:
        now = int(time.time())
        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        payload = {
            "iss": JWT_ISSUER,
            "sub": subject,
            "email": email,
            "name": name,
            "role": role,
            "tenant_id": tenant_id,
            "permissions": permissions,
            "iat": now,
            "exp": now + (expires_minutes * 60),
            "jti": f"jti_{secrets.token_hex(8)}",
        }
        h_b64 = _b64url_encode(
            json.dumps(header, separators=(",", ":")).encode("utf-8"))
        p_b64 = _b64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{h_b64}.{p_b64}".encode("ascii")
        sig = hmac.new(self.secret.encode("utf-8"), signing_input,
                       hashlib.sha256).digest()
        return f"{h_b64}.{p_b64}.{_b64url_encode(sig)}"

    def decode_token(self, token: str) -> Dict[str, Any]:
        parts = token.strip().split(".")
        if len(parts) != 3:
            raise AuthError("Malformed JWT structure.")

        h_b64, p_b64, s_b64 = parts
        try:
            header = json.loads(_b64url_decode(h_b64).decode("utf-8"))
            payload = json.loads(_b64url_decode(p_b64).decode("utf-8"))
        except Exception:
            raise AuthError("Invalid JWT encoding.")

        if header.get("alg") != JWT_ALGORITHM:
            raise AuthError("Unsupported JWT signing algorithm.")

        signing_input = f"{h_b64}.{p_b64}".encode("ascii")
        expected_sig = _b64url_encode(
            hmac.new(self.secret.encode("utf-8"), signing_input,
                     hashlib.sha256).digest())
        if not hmac.compare_digest(expected_sig, s_b64):
            raise AuthError("Invalid JWT cryptographic signature.")

        now = int(time.time())
        if int(payload.get("exp", 0)) < now:
            raise AuthError("JWT access token has expired.")

        return payload


# -----------------------------------------------------------------------------
# Role-Based Access Control (RBAC) Matrix
# -----------------------------------------------------------------------------
ROLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "label":
        "Principal Admin",
        "description":
        "Full platform governance, cross-tenant switching, API keys, and MLOps control.",
        "can_switch_tenants":
        True,
        "permissions": ["*"],
        "allowed_tabs": [
            "overview",
            "segmentation",
            "forecasting",
            "churn",
            "recommendations",
            "customer-mgmt",
            "inventory-mart",
            "campaign-studio",
            "pricing-lab",
            "fraud-radar",
            "transaction-simulator",
            "data-warehouse",
            "admin-ops",
            "api-console",
            "audit-logs",
        ],
    },
    "lead_ds": {
        "label":
        "Lead Data Scientist",
        "description":
        "ML model retraining, drift diagnostics, pricing elasticity, and audit inspection.",
        "can_switch_tenants":
        False,
        "permissions": [
            "analytics:read",
            "predict:execute",
            "mlops:read",
            "mlops:retrain",
            "pricing:read",
            "experiments:run",
            "copilot:query",
            "audit:read",
            "fraud:read",
            "fraud:resolve",
        ],
        "allowed_tabs": [
            "overview",
            "segmentation",
            "forecasting",
            "churn",
            "recommendations",
            "pricing-lab",
            "fraud-radar",
            "data-warehouse",
            "admin-ops",
            "api-console",
            "audit-logs",
        ],
    },
    "growth": {
        "label":
        "Growth & Marketing Director",
        "description":
        "Customer segments, churn retention campaigns, and pricing experimentation.",
        "can_switch_tenants":
        False,
        "permissions": [
            "analytics:read",
            "predict:execute",
            "campaigns:read",
            "campaigns:dispatch",
            "pricing:read",
            "experiments:run",
            "copilot:query",
            "customers:read",
        ],
        "allowed_tabs": [
            "overview",
            "segmentation",
            "forecasting",
            "churn",
            "recommendations",
            "customer-mgmt",
            "campaign-studio",
            "pricing-lab",
        ],
    },
    "supply": {
        "label":
        "Supply Chain & Inventory VP",
        "description":
        "Demand forecasting, SKU velocity mart, inventory restocks, and POS webhooks.",
        "can_switch_tenants":
        False,
        "permissions": [
            "analytics:read",
            "predict:execute",
            "inventory:read",
            "inventory:write",
            "webhooks:read",
            "copilot:query",
            "fraud:read",
            "fraud:resolve",
        ],
        "allowed_tabs": [
            "overview",
            "forecasting",
            "recommendations",
            "inventory-mart",
            "fraud-radar",
            "transaction-simulator",
        ],
    },
}


def role_has_permission(role: str, required_permission: str) -> bool:
    """Checks whether a role grants the required permission scope."""
    role_meta = ROLE_DEFINITIONS.get(role)
    if not role_meta:
        return False
    perms = role_meta.get("permissions", [])
    return "*" in perms or required_permission in perms


# -----------------------------------------------------------------------------
# Enterprise Multi-Tenant Security Registry (Singleton)
# -----------------------------------------------------------------------------
class SecurityRegistry:
    """
    Singleton managing multi-tenant organizations, user directory, API key hashes,
    JWT revocation list, strict enforcement toggle, and server audit events.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecurityRegistry, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.jwt_engine = JWTEngine()
        self.strict_rbac_enabled: bool = False
        self.revoked_jtis: set = set()
        self.audit_events: List[Dict[str, Any]] = []

        self.tenants: Dict[str, Dict[str, Any]] = {
            "tenant_uk_flagship": {
                "tenant_id": "tenant_uk_flagship",
                "name": "Prism UK Flagship Wholesale",
                "country": "United Kingdom",
                "currency": "GBP",
                "plan": "Enterprise",
                "status": "ACTIVE",
                "created_at": "2026-11-01T00:00:00+00:00",
            },
            "tenant_eu_nordics": {
                "tenant_id": "tenant_eu_nordics",
                "name": "EuroCraft Retail GmbH & NL",
                "country": "Netherlands",
                "currency": "EUR",
                "plan": "Growth",
                "status": "ACTIVE",
                "created_at": "2026-11-03T00:00:00+00:00",
            },
            "tenant_us_direct": {
                "tenant_id": "tenant_us_direct",
                "name": "Atlantic Direct Commerce",
                "country": "United States",
                "currency": "USD",
                "plan": "Enterprise",
                "status": "ACTIVE",
                "created_at": "2026-11-05T00:00:00+00:00",
            },
        }

        # Pre-seeded RBAC identities with salted PBKDF2-SHA256 hashes
        self.users: Dict[str, Dict[str, Any]] = {
            "admin@prismretail.ai": {
                "user_id": "usr_admin_01",
                "email": "admin@prismretail.ai",
                "name": "Aryan Gupta",
                "role": "admin",
                "tenant_id": "tenant_uk_flagship",
                "password_hash":
                PasswordHasher.hash_password("PrismAdmin2026!"),
            },
            "ds@prismretail.ai": {
                "user_id": "usr_ds_02",
                "email": "ds@prismretail.ai",
                "name": "Dr. Maya Lin",
                "role": "lead_ds",
                "tenant_id": "tenant_uk_flagship",
                "password_hash": PasswordHasher.hash_password("PrismDS2026!"),
            },
            "growth@prismretail.ai": {
                "user_id": "usr_growth_03",
                "email": "growth@prismretail.ai",
                "name": "Elena Vance",
                "role": "growth",
                "tenant_id": "tenant_eu_nordics",
                "password_hash":
                PasswordHasher.hash_password("PrismGrowth2026!"),
            },
            "supply@prismretail.ai": {
                "user_id": "usr_supply_04",
                "email": "supply@prismretail.ai",
                "name": "Marcus Sterling",
                "role": "supply",
                "tenant_id": "tenant_uk_flagship",
                "password_hash": PasswordHasher.hash_password("PrismOps2026!"),
            },
            # Backward-compatible legacy aliases
            "admin@nexusretail.ai": {
                "user_id": "usr_admin_01",
                "email": "admin@nexusretail.ai",
                "name": "Aryan Gupta",
                "role": "admin",
                "tenant_id": "tenant_uk_flagship",
                "password_hash":
                PasswordHasher.hash_password("NexusAdmin2026!"),
            },
            "ds@nexusretail.ai": {
                "user_id": "usr_ds_02",
                "email": "ds@nexusretail.ai",
                "name": "Dr. Maya Lin",
                "role": "lead_ds",
                "tenant_id": "tenant_uk_flagship",
                "password_hash": PasswordHasher.hash_password("NexusDS2026!"),
            },
            "growth@nexusretail.ai": {
                "user_id": "usr_growth_03",
                "email": "growth@nexusretail.ai",
                "name": "Elena Vance",
                "role": "growth",
                "tenant_id": "tenant_eu_nordics",
                "password_hash":
                PasswordHasher.hash_password("NexusGrowth2026!"),
            },
            "supply@nexusretail.ai": {
                "user_id": "usr_supply_04",
                "email": "supply@nexusretail.ai",
                "name": "Marcus Sterling",
                "role": "supply",
                "tenant_id": "tenant_uk_flagship",
                "password_hash": PasswordHasher.hash_password("NexusOps2026!"),
            },
        }

        # Store SHA-256 digests of API keys (never plaintext after generation)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self._seed_initial_api_keys()

        try:
            store = get_state_store()
            for t in store.load_tenants():
                self.tenants[t["tenant_id"]] = t
            past_events = store.load_audit_events(limit=100)
            if past_events:
                self.audit_events = past_events
        except Exception:
            pass

        self.record_audit_event(
            event_type="SYSTEM_INIT",
            actor_email="system@nexusretail.ai",
            actor_role="admin",
            tenant_id="tenant_uk_flagship",
            action=
            "Initialized multi-tenant RBAC registry (4 roles, 3 tenant isolates)",
            status_code=200,
            severity="INFO",
        )

    def _seed_initial_api_keys(self):
        seed_specs = [
            ("key_uk_pos_prod", "UK Flagship POS Sync", "tenant_uk_flagship",
             "admin", "admin@nexusretail.ai", "nxk_live_ukflagship_seeded01"),
            ("key_eu_growth_bot", "EU Campaign Automation",
             "tenant_eu_nordics", "growth", "growth@nexusretail.ai",
             "nxk_live_eunordic_seeded02"),
        ]
        for key_id, label, tenant_id, role, owner, raw_secret in seed_specs:
            digest = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
            self.api_keys[key_id] = {
                "key_id": key_id,
                "label": label,
                "key_prefix": f"{raw_secret[:14]}••••••••",
                "key_hash": digest,
                "tenant_id": tenant_id,
                "role": role,
                "owner_email": owner,
                "active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_used_at": None,
            }

    def record_audit_event(
        self,
        event_type: str,
        actor_email: str,
        actor_role: str,
        tenant_id: str,
        action: str,
        status_code: int = 200,
        severity: str = "INFO",
    ):
        entry = {
            "event_id": f"sec_{secrets.token_hex(4)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor_email": actor_email,
            "actor_role": actor_role,
            "tenant_id": tenant_id,
            "action": action,
            "status_code": status_code,
            "severity": severity,
        }
        self.audit_events.insert(0, entry)
        if len(self.audit_events) > 100:
            self.audit_events.pop()
        try:
            get_state_store().append_audit_event(entry)
        except Exception:
            pass

    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        clean_email = email.strip().lower()
        user = self.users.get(clean_email)
        if not user:
            if clean_email.endswith("@nexusretail.ai"):
                user = self.users.get(clean_email.replace("@nexusretail.ai", "@prismretail.ai"))
            elif clean_email.endswith("@prismretail.ai"):
                user = self.users.get(clean_email.replace("@prismretail.ai", "@nexusretail.ai"))

        is_valid = False
        if user:
            if PasswordHasher.verify_password(password, user["password_hash"]):
                is_valid = True
            elif password.startswith("Nexus") and PasswordHasher.verify_password(password.replace("Nexus", "Prism", 1), user["password_hash"]):
                is_valid = True
            elif password.startswith("Prism") and PasswordHasher.verify_password(password.replace("Prism", "Nexus", 1), user["password_hash"]):
                is_valid = True

        if not user or not is_valid:
            self.record_audit_event(
                event_type="LOGIN_FAILED",
                actor_email=clean_email or "unknown",
                actor_role="anonymous",
                tenant_id="none",
                action=f"Failed login attempt for {clean_email or 'unknown'}",
                status_code=401,
                severity="WARNING",
            )
            raise AuthError("Invalid email or password credentials.",
                            status.HTTP_401_UNAUTHORIZED)

        role = user["role"]
        role_meta = ROLE_DEFINITIONS[role]
        tenant_id = user["tenant_id"]
        token = self.jwt_engine.create_access_token(
            subject=user["user_id"],
            email=user["email"],
            name=user["name"],
            role=role,
            tenant_id=tenant_id,
            permissions=role_meta["permissions"],
        )

        self.record_audit_event(
            event_type="LOGIN_SUCCESS",
            actor_email=user["email"],
            actor_role=role,
            tenant_id=tenant_id,
            action=
            f"Issued HS256 JWT session for {user['name']} ({role_meta['label']})",
            status_code=200,
            severity="INFO",
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in_seconds": 7200,
            "user": self._format_user_profile(user, tenant_id),
            "active_tenant": self.tenants.get(tenant_id),
        }

    def _format_user_profile(self, user: Dict[str, Any],
                             tenant_id: str) -> Dict[str, Any]:
        role = user["role"]
        role_meta = ROLE_DEFINITIONS[role]
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user["name"],
            "role": role,
            "role_label": role_meta["label"],
            "tenant_id": tenant_id,
            "tenant_name": self.tenants.get(tenant_id,
                                            {}).get("name", tenant_id),
            "can_switch_tenants": role_meta["can_switch_tenants"],
            "permissions": role_meta["permissions"],
            "allowed_tabs": role_meta["allowed_tabs"],
        }

    def verify_bearer_jwt(self, token: str) -> Dict[str, Any]:
        payload = self.jwt_engine.decode_token(token)
        if payload.get("jti") in self.revoked_jtis:
            raise AuthError("JWT access token has been revoked.",
                            status.HTTP_401_UNAUTHORIZED)
        return payload

    def verify_api_key(self, raw_key: str) -> Dict[str, Any]:
        digest = hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()
        for record in self.api_keys.values():
            if record["active"] and hmac.compare_digest(
                    record["key_hash"], digest):
                record["last_used_at"] = datetime.now(timezone.utc).isoformat()
                role = record["role"]
                return {
                    "sub": record["key_id"],
                    "email": record["owner_email"],
                    "name": f"API Key ({record['label']})",
                    "role": role,
                    "tenant_id": record["tenant_id"],
                    "permissions": ROLE_DEFINITIONS[role]["permissions"],
                    "auth_method": "api_key",
                }
        raise AuthError("Invalid or revoked X-API-Key credential.",
                        status.HTTP_401_UNAUTHORIZED)

    def create_tenant(self, name: str, country: str, currency: str, plan: str,
                      actor: Dict[str, Any]) -> Dict[str, Any]:
        slug = "".join(ch for ch in name.lower().replace(" ", "_")
                       if ch.isalnum() or ch == "_")[:24].strip("_")
        tenant_id = f"tenant_{slug or secrets.token_hex(4)}"
        if tenant_id in self.tenants:
            tenant_id = f"{tenant_id}_{secrets.token_hex(2)}"

        tenant = {
            "tenant_id": tenant_id,
            "name": name.strip(),
            "country": country.strip(),
            "currency": currency.strip().upper()[:3],
            "plan": plan.strip(),
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.tenants[tenant_id] = tenant
        try:
            get_state_store().save_tenant(tenant)
        except Exception:
            pass
        self.record_audit_event(
            event_type="TENANT_CREATED",
            actor_email=actor.get("email", "admin"),
            actor_role=actor.get("role", "admin"),
            tenant_id=tenant_id,
            action=
            f"Provisioned isolated tenant '{tenant['name']}' ({tenant['currency']})",
            status_code=201,
            severity="INFO",
        )
        return tenant

    def switch_tenant(self, target_tenant_id: str,
                      principal: Dict[str, Any]) -> Dict[str, Any]:
        if target_tenant_id not in self.tenants:
            raise AuthError(
                f"Tenant workspace '{target_tenant_id}' does not exist.",
                status.HTTP_404_NOT_FOUND)

        role = principal.get("role", "")
        current_tenant = principal.get("tenant_id", "")
        can_switch = ROLE_DEFINITIONS.get(role,
                                          {}).get("can_switch_tenants", False)

        if target_tenant_id != current_tenant and not can_switch:
            self.record_audit_event(
                event_type="CROSS_TENANT_DENIED",
                actor_email=principal.get("email", "unknown"),
                actor_role=role,
                tenant_id=current_tenant,
                action=
                f"Blocked cross-tenant switch attempt from {current_tenant} to {target_tenant_id}",
                status_code=403,
                severity="CRITICAL",
            )
            raise AuthError(
                f"Role '{role}' is tenant-pinned to '{current_tenant}' and cannot access '{target_tenant_id}'.",
                status.HTTP_403_FORBIDDEN,
            )

        role_meta = ROLE_DEFINITIONS[role]
        new_token = self.jwt_engine.create_access_token(
            subject=principal.get("sub", "usr_switch"),
            email=principal.get("email", "admin@nexusretail.ai"),
            name=principal.get("name", "Principal Admin"),
            role=role,
            tenant_id=target_tenant_id,
            permissions=role_meta["permissions"],
        )

        self.record_audit_event(
            event_type="TENANT_SWITCHED",
            actor_email=principal.get("email", "admin"),
            actor_role=role,
            tenant_id=target_tenant_id,
            action=
            f"Switched active session context to tenant '{target_tenant_id}'",
            status_code=200,
            severity="INFO",
        )

        return {
            "access_token": new_token,
            "token_type": "bearer",
            "tenant": self.tenants[target_tenant_id],
        }

    def issue_api_key(self, label: str, tenant_id: str, role: str,
                      actor: Dict[str, Any]) -> Dict[str, Any]:
        if tenant_id not in self.tenants:
            raise AuthError(f"Unknown tenant_id '{tenant_id}'.",
                            status.HTTP_400_BAD_REQUEST)
        if role not in ROLE_DEFINITIONS:
            raise AuthError(f"Unsupported role '{role}'.",
                            status.HTTP_400_BAD_REQUEST)

        # Enforce tenant isolation for non-admin key creation attempts
        if actor.get("role") != "admin" and tenant_id != actor.get(
                "tenant_id"):
            raise AuthError("Cross-tenant API key provisioning denied.",
                            status.HTTP_403_FORBIDDEN)

        key_id = f"key_{secrets.token_hex(5)}"
        raw_secret = f"nxk_live_{secrets.token_hex(4)}_{secrets.token_urlsafe(18)}"
        key_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()

        record = {
            "key_id": key_id,
            "label": label.strip(),
            "key_prefix": f"{raw_secret[:15]}••••••••",
            "key_hash": key_hash,
            "tenant_id": tenant_id,
            "role": role,
            "owner_email": actor.get("email", "admin@nexusretail.ai"),
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used_at": None,
        }
        self.api_keys[key_id] = record

        self.record_audit_event(
            event_type="API_KEY_ISSUED",
            actor_email=actor.get("email", "admin"),
            actor_role=actor.get("role", "admin"),
            tenant_id=tenant_id,
            action=f"Minted API key '{label}' ({key_id}) scoped to role={role}",
            status_code=201,
            severity="INFO",
        )

        safe_record = {k: v for k, v in record.items() if k != "key_hash"}
        safe_record["raw_secret"] = raw_secret  # Shown once upon creation
        return safe_record

    def revoke_api_key(self, key_id: str, actor: Dict[str,
                                                      Any]) -> Dict[str, Any]:
        record = self.api_keys.get(key_id)
        if not record:
            raise AuthError(f"API key '{key_id}' not found.",
                            status.HTTP_404_NOT_FOUND)
        if actor.get("role") != "admin" and record["tenant_id"] != actor.get(
                "tenant_id"):
            raise AuthError("Cross-tenant API key revocation denied.",
                            status.HTTP_403_FORBIDDEN)
        record["active"] = False
        self.record_audit_event(
            event_type="API_KEY_REVOKED",
            actor_email=actor.get("email", "admin"),
            actor_role=actor.get("role", "admin"),
            tenant_id=record["tenant_id"],
            action=f"Revoked API key '{record['label']}' ({key_id})",
            status_code=200,
            severity="WARNING",
        )
        return {k: v for k, v in record.items() if k != "key_hash"}

    def list_api_keys(self,
                      tenant_id: Optional[str] = None,
                      role: str = "admin") -> List[Dict[str, Any]]:
        keys = []
        for rec in self.api_keys.values():
            if role != "admin" and tenant_id and rec["tenant_id"] != tenant_id:
                continue
            keys.append({k: v for k, v in rec.items() if k != "key_hash"})
        return list(reversed(keys))


# -----------------------------------------------------------------------------
# FastAPI Authentication & RBAC Dependencies
# -----------------------------------------------------------------------------
def _extract_principal(
    authorization: Optional[str],
    x_api_key: Optional[str],
    x_tenant_id: Optional[str],
    allow_anonymous_dev: bool,
) -> Dict[str, Any]:
    registry = SecurityRegistry()
    principal: Optional[Dict[str, Any]] = None

    if authorization:
        scheme, _, token = authorization.strip().partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header must use Bearer <token> format.",
            )
        try:
            principal = registry.verify_bearer_jwt(token)
            principal["auth_method"] = "jwt"
        except AuthError as exc:
            raise HTTPException(status_code=exc.status_code,
                                detail=exc.message)

    elif x_api_key:
        try:
            principal = registry.verify_api_key(x_api_key)
        except AuthError as exc:
            raise HTTPException(status_code=exc.status_code,
                                detail=exc.message)

    else:
        if registry.strict_rbac_enabled or not allow_anonymous_dev:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=
                "Authentication required: provide Authorization Bearer JWT or X-API-Key.",
            )
        # Backward-compatible open dev context when strict RBAC is disabled and no credentials passed
        return {
            "sub": "dev_anonymous",
            "email": "dev@prismretail.ai",
            "name": "Dev Workspace Session",
            "role": "admin",
            "tenant_id": x_tenant_id or "tenant_uk_flagship",
            "permissions": ["*"],
            "auth_method": "dev_open",
        }

    # Cross-tenant isolation header enforcement for authenticated callers
    if x_tenant_id and x_tenant_id.strip() != principal.get("tenant_id"):
        if principal.get("role") != "admin":
            registry.record_audit_event(
                event_type="TENANT_ISOLATION_BLOCK",
                actor_email=principal.get("email", "unknown"),
                actor_role=principal.get("role", "unknown"),
                tenant_id=principal.get("tenant_id", "unknown"),
                action=
                f"Blocked X-Tenant-ID spoofing header targeting '{x_tenant_id}'",
                status_code=403,
                severity="CRITICAL",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=
                f"Tenant isolation violation: credentials scoped to '{principal.get('tenant_id')}' cannot target '{x_tenant_id}'.",
            )
        if x_tenant_id in registry.tenants:
            principal["tenant_id"] = x_tenant_id

    return principal


def get_required_principal(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> Dict[str, Any]:
    """Dependency requiring valid JWT or API Key regardless of global dev toggle."""
    return _extract_principal(authorization,
                              x_api_key,
                              x_tenant_id,
                              allow_anonymous_dev=False)


def require_permission(permission: str,
                       always_require_auth: bool = False) -> Callable:
    """
    FastAPI dependency factory enforcing permission checks & tenant isolation.
    Allows open dev access when strict_rbac_enabled=False and no credentials are supplied
    (preserving backward compatibility), while strictly validating any supplied credential
    and all requests under strict_rbac_enabled=True.
    """

    def dependency(
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
        x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    ) -> Dict[str, Any]:
        principal = _extract_principal(
            authorization,
            x_api_key,
            x_tenant_id,
            allow_anonymous_dev=not always_require_auth,
        )

        if principal.get("auth_method") == "dev_open":
            return principal

        role = principal.get("role", "")
        if not role_has_permission(role, permission):
            registry = SecurityRegistry()
            registry.record_audit_event(
                event_type="RBAC_FORBIDDEN",
                actor_email=principal.get("email", "unknown"),
                actor_role=role,
                tenant_id=principal.get("tenant_id", "unknown"),
                action=
                f"Denied {request.method} {request.url.path} (missing scope '{permission}')",
                status_code=403,
                severity="CRITICAL",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=
                f"RBAC Forbidden: role '{role}' lacks required permission '{permission}'.",
            )
        return principal

    return dependency
