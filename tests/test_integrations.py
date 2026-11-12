"""
Unit and Integration Tests for E-Commerce Webhook Hub (Shopify, Stripe, WooCommerce).
"""

import hmac
import hashlib
import base64
import json
import time
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.api.server import app
from src.api.integrations import ECommerceIntegrations, IntegrationRegistry

client = TestClient(app)


def test_shopify_hmac_verification():
    """Verify Shopify HMAC-SHA256 signature verification logic."""
    secret = "test_shopify_secret_123"
    payload = b'{"id": 1001, "total_price": "50.00"}'

    # Compute valid HMAC
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    valid_hmac = base64.b64encode(digest).decode("utf-8")

    assert ECommerceIntegrations.verify_shopify_hmac(payload, valid_hmac, secret) is True
    assert ECommerceIntegrations.verify_shopify_hmac(payload, "invalid_hmac_value", secret) is False
    assert ECommerceIntegrations.verify_shopify_hmac(payload, None, secret) is False


def test_stripe_signature_verification():
    """Verify Stripe timestamped HMAC-SHA256 signature verification."""
    secret = "whsec_test_stripe_secret_456"
    payload = b'{"type": "payment_intent.succeeded"}'
    ts = int(time.time())

    signed_payload = f"{ts}.".encode("utf-8") + payload
    v1_sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    valid_header = f"t={ts},v1={v1_sig}"

    assert ECommerceIntegrations.verify_stripe_signature(payload, valid_header, secret) is True
    assert ECommerceIntegrations.verify_stripe_signature(payload, f"t={ts},v1=bad_signature", secret) is False
    assert ECommerceIntegrations.verify_stripe_signature(payload, None, secret) is False


def test_woocommerce_signature_verification():
    """Verify WooCommerce Base64 HMAC-SHA256 signature verification."""
    secret = "wc_test_secret_789"
    payload = b'{"id": 2002, "total": "75.00"}'

    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    valid_sig = base64.b64encode(digest).decode("utf-8")

    assert ECommerceIntegrations.verify_woocommerce_signature(payload, valid_sig, secret) is True
    assert ECommerceIntegrations.verify_woocommerce_signature(payload, "bad_wc_sig", secret) is False
    assert ECommerceIntegrations.verify_woocommerce_signature(payload, None, secret) is False


def test_shopify_payload_normalization():
    """Verify Shopify order payload maps to canonical retail items."""
    sample = ECommerceIntegrations.generate_sample_webhook_payload("shopify")
    records = ECommerceIntegrations.normalize_shopify_order(sample)

    assert len(records) == 3
    assert records[0]["InvoiceNo"].startswith("SH-")
    assert records[0]["SourcePlatform"] == "Shopify"
    assert "StockCode" in records[0]
    assert records[0]["Quantity"] > 0
    assert records[0]["UnitPrice"] > 0.0


def test_stripe_payload_normalization():
    """Verify Stripe payment payload maps to canonical retail items."""
    sample = ECommerceIntegrations.generate_sample_webhook_payload("stripe")
    records = ECommerceIntegrations.normalize_stripe_event(sample)

    assert len(records) == 1
    assert records[0]["InvoiceNo"].startswith("STR-")
    assert records[0]["SourcePlatform"] == "Stripe"
    assert records[0]["UnitPrice"] == 54.90


def test_woocommerce_payload_normalization():
    """Verify WooCommerce order payload maps to canonical retail items."""
    sample = ECommerceIntegrations.generate_sample_webhook_payload("woocommerce")
    records = ECommerceIntegrations.normalize_woocommerce_order(sample)

    assert len(records) == 2
    assert records[0]["InvoiceNo"].startswith("WC-")
    assert records[0]["SourcePlatform"] == "WooCommerce"


def test_api_integrations_status_endpoint():
    """Assert GET /api/v1/integrations/status returns active connectors."""
    res = client.get("/api/v1/integrations/status")
    assert res.status_code == 200
    data = res.json()
    assert "connectors" in data
    assert "shopify" in data["connectors"]
    assert "stripe" in data["connectors"]
    assert "woocommerce" in data["connectors"]
    assert data["connectors"]["shopify"]["status"] in ["LISTENING", "ACTIVE"]


def test_api_configure_secret_endpoint():
    """Assert POST /api/v1/integrations/configure-secret updates connector secret."""
    res = client.post("/api/v1/integrations/configure-secret", json={
        "provider": "shopify",
        "secret": "shpss_new_updated_secret_key_2026"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Bad provider
    bad = client.post("/api/v1/integrations/configure-secret", json={
        "provider": "magento_unsupported",
        "secret": "secret12345"
    })
    assert bad.status_code == 400


def test_api_shopify_webhook_verified_and_invalid():
    """Assert Shopify webhook validates signature and rejects forged payloads."""
    registry = IntegrationRegistry()
    secret = registry.connectors["shopify"]["secret"]
    sample = ECommerceIntegrations.generate_sample_webhook_payload("shopify")
    body_bytes = json.dumps(sample).encode("utf-8")

    # 1. Invalid signature -> 401
    res_bad = client.post(
        "/api/v1/integrations/webhook/shopify",
        content=body_bytes,
        headers={"X-Shopify-Hmac-Sha256": "fake_forged_signature", "Content-Type": "application/json"}
    )
    assert res_bad.status_code == 401

    # 2. Valid signature -> 200
    digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).digest()
    valid_hmac = base64.b64encode(digest).decode("utf-8")

    res_good = client.post(
        "/api/v1/integrations/webhook/shopify",
        content=body_bytes,
        headers={"X-Shopify-Hmac-Sha256": valid_hmac, "Content-Type": "application/json"}
    )
    assert res_good.status_code == 200
    data = res_good.json()
    assert data["status"] == "success"
    assert data["signature_verified"] is True
    assert data["items_ingested"] == 3


def test_api_stripe_webhook_verified_and_invalid():
    """Assert Stripe webhook validates signature and rejects forged signatures."""
    registry = IntegrationRegistry()
    secret = registry.connectors["stripe"]["secret"]
    sample = ECommerceIntegrations.generate_sample_webhook_payload("stripe")
    body_bytes = json.dumps(sample).encode("utf-8")

    # 1. Invalid signature -> 401
    res_bad = client.post(
        "/api/v1/integrations/webhook/stripe",
        content=body_bytes,
        headers={"Stripe-Signature": "t=12345,v1=forged_stripe_sig", "Content-Type": "application/json"}
    )
    assert res_bad.status_code == 401

    # 2. Valid signature -> 200
    ts = int(time.time())
    signed_payload = f"{ts}.".encode("utf-8") + body_bytes
    v1_sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    valid_header = f"t={ts},v1={v1_sig}"

    res_good = client.post(
        "/api/v1/integrations/webhook/stripe",
        content=body_bytes,
        headers={"Stripe-Signature": valid_header, "Content-Type": "application/json"}
    )
    assert res_good.status_code == 200
    data = res_good.json()
    assert data["status"] == "success"
    assert data["signature_verified"] is True


def test_api_woocommerce_webhook_verified_and_invalid():
    """Assert WooCommerce webhook validates signature."""
    registry = IntegrationRegistry()
    secret = registry.connectors["woocommerce"]["secret"]
    sample = ECommerceIntegrations.generate_sample_webhook_payload("woocommerce")
    body_bytes = json.dumps(sample).encode("utf-8")

    # 1. Invalid signature -> 401
    res_bad = client.post(
        "/api/v1/integrations/webhook/woocommerce",
        content=body_bytes,
        headers={"X-WC-Webhook-Signature": "bad_wc_signature", "Content-Type": "application/json"}
    )
    assert res_bad.status_code == 401

    # 2. Valid signature -> 200
    digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).digest()
    valid_sig = base64.b64encode(digest).decode("utf-8")

    res_good = client.post(
        "/api/v1/integrations/webhook/woocommerce",
        content=body_bytes,
        headers={"X-WC-Webhook-Signature": valid_sig, "Content-Type": "application/json"}
    )
    assert res_good.status_code == 200
    assert res_good.json()["signature_verified"] is True


def test_api_simulate_sample_webhook_endpoint():
    """Assert POST /api/v1/integrations/webhook/simulate-sample handles each provider."""
    for provider in ["shopify", "stripe", "woocommerce"]:
        res = client.post("/api/v1/integrations/webhook/simulate-sample", json={"provider": provider})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["provider"] == provider
        assert data["signature_verified"] is True
        assert data["items_ingested"] >= 1
        assert "raw_sample_payload" in data
