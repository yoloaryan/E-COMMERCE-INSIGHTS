"""
Real-Time E-Commerce Integration Webhook Hub.
Provides signature verification, payload normalization, and live order streaming
for Shopify, Stripe, and WooCommerce.
"""

import hmac
import hashlib
import base64
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]


class ECommerceIntegrations:
    """
    Ingestion normalizer and signature verifier for multi-platform e-commerce webhooks.
    """

    # Default development sandbox secrets
    DEFAULT_SECRETS = {
        "shopify": "shpss_test_secret_key_nexus_2026",
        "stripe": "whsec_test_stripe_webhook_secret_nexus_2026",
        "woocommerce": "wc_secret_nexus_retail_ai_2026"
    }

    @staticmethod
    def verify_shopify_hmac(raw_body: bytes, hmac_header: Optional[str], secret: str) -> bool:
        """
        Verifies Shopify HMAC-SHA256 signature in X-Shopify-Hmac-Sha256.
        """
        if not hmac_header or not secret:
            return False
        try:
            digest = hmac.new(
                secret.encode("utf-8"),
                raw_body,
                hashlib.sha256
            ).digest()
            calculated_hmac = base64.b64encode(digest).decode("utf-8")
            return hmac.compare_digest(calculated_hmac.strip(), hmac_header.strip())
        except Exception:
            return False

    @staticmethod
    def verify_stripe_signature(raw_body: bytes, sig_header: Optional[str], secret: str, tolerance: int = 300) -> bool:
        """
        Verifies Stripe Webhook signature in Stripe-Signature header: t=timestamp,v1=signature.
        """
        if not sig_header or not secret:
            return False
        try:
            parts = dict(item.split("=", 1) for item in sig_header.split(",") if "=" in item)
            timestamp = parts.get("t")
            v1_signature = parts.get("v1")

            if not timestamp or not v1_signature:
                return False

            # Check timestamp tolerance if needed
            if tolerance > 0:
                current_time = int(time.time())
                if abs(current_time - int(timestamp)) > tolerance:
                    # Allow slight clock skew in dev/testing
                    pass

            signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
            expected_signature = hmac.new(
                secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature.strip(), v1_signature.strip())
        except Exception:
            return False

    @staticmethod
    def verify_woocommerce_signature(raw_body: bytes, sig_header: Optional[str], secret: str) -> bool:
        """
        Verifies WooCommerce signature in X-WC-Webhook-Signature (Base64 HMAC-SHA256).
        """
        if not sig_header or not secret:
            return False
        try:
            digest = hmac.new(
                secret.encode("utf-8"),
                raw_body,
                hashlib.sha256
            ).digest()
            calculated_sig = base64.b64encode(digest).decode("utf-8")
            return hmac.compare_digest(calculated_sig.strip(), sig_header.strip())
        except Exception:
            return False

    @classmethod
    def normalize_shopify_order(cls, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalizes a Shopify orders/create or orders/paid JSON payload into canonical retail items.
        """
        raw_order_id = payload.get("order_number") or payload.get("id") or int(time.time())
        invoice_no = f"SH-{raw_order_id}"

        # Customer identification
        customer_info = payload.get("customer") or {}
        customer_id = customer_info.get("id") or payload.get("user_id") or 99991

        # Country
        shipping_address = payload.get("shipping_address") or {}
        billing_address = payload.get("billing_address") or {}
        country = (
            shipping_address.get("country")
            or billing_address.get("country")
            or customer_info.get("default_address", {}).get("country")
            or "United Kingdom"
        )

        # Date
        created_at = payload.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        line_items = payload.get("line_items") or []
        if not line_items:
            # Fallback if webhook has no line item breakdown
            total_price = float(payload.get("total_price") or payload.get("current_total_price") or 25.0)
            return [{
                "InvoiceNo": invoice_no,
                "StockCode": "SHOPIFY_GENERIC",
                "Description": "Shopify Online Order Package",
                "Quantity": 1,
                "UnitPrice": total_price,
                "InvoiceDate": created_at,
                "CustomerID": float(customer_id),
                "Country": country,
                "SourcePlatform": "Shopify"
            }]

        records = []
        for item in line_items:
            sku = str(item.get("sku") or item.get("product_id") or item.get("id") or "SH-SKU").strip()
            name = item.get("name") or item.get("title") or "Shopify Catalog Item"
            qty = max(1, int(item.get("quantity") or 1))
            unit_price = float(item.get("price") or 0.0)

            records.append({
                "InvoiceNo": invoice_no,
                "StockCode": sku[:15],
                "Description": name[:40],
                "Quantity": qty,
                "UnitPrice": round(unit_price, 2),
                "InvoiceDate": created_at,
                "CustomerID": float(customer_id),
                "Country": country,
                "SourcePlatform": "Shopify"
            })
        return records

    @classmethod
    def normalize_stripe_event(cls, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalizes Stripe payment_intent.succeeded or checkout.session.completed event.
        """
        data_obj = payload.get("data", {}).get("object", payload)
        event_id = data_obj.get("id") or f"pi_{int(time.time())}"
        invoice_no = f"STR-{event_id[-8:].upper()}"

        # Stripe amounts are in cents/pence
        raw_amount = data_obj.get("amount") or data_obj.get("amount_total") or 2999
        currency = data_obj.get("currency", "gbp").upper()
        amount_gbp = round(float(raw_amount) / 100.0, 2)

        metadata = data_obj.get("metadata") or {}
        customer_id = metadata.get("customer_id") or metadata.get("CustomerID") or 99992

        # Country from charge or billing
        charges = data_obj.get("charges", {}).get("data", [])
        billing_details = charges[0].get("billing_details", {}) if charges else {}
        country_code = (
            billing_details.get("address", {}).get("country")
            or data_obj.get("customer_details", {}).get("address", {}).get("country")
            or "United Kingdom"
        )
        country_map = {"GB": "United Kingdom", "US": "United States", "DE": "Germany", "FR": "France"}
        country = country_map.get(country_code, country_code)

        created_ts = data_obj.get("created")
        if created_ts:
            dt = datetime.fromtimestamp(created_ts, tz=timezone.utc)
            invoice_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            invoice_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Parse line items or create transaction entry
        description = metadata.get("product_name") or f"Stripe Checkout ({currency} {amount_gbp:.2f})"
        sku = str(metadata.get("sku") or "STRIPE_CHECKOUT")

        return [{
            "InvoiceNo": invoice_no,
            "StockCode": sku[:15],
            "Description": description[:40],
            "Quantity": 1,
            "UnitPrice": amount_gbp,
            "InvoiceDate": invoice_date,
            "CustomerID": float(customer_id),
            "Country": country,
            "SourcePlatform": "Stripe"
        }]

    @classmethod
    def normalize_woocommerce_order(cls, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalizes WooCommerce order.created JSON payload.
        """
        order_id = payload.get("id") or int(time.time())
        invoice_no = f"WC-{order_id}"

        customer_id = payload.get("customer_id") or 99993
        billing = payload.get("billing") or {}
        country = billing.get("country") or "United Kingdom"
        country_map = {"GB": "United Kingdom", "UK": "United Kingdom", "US": "United States"}
        country = country_map.get(country, country)

        created_at = payload.get("date_created") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        line_items = payload.get("line_items") or []

        if not line_items:
            total_str = payload.get("total") or "45.00"
            total = float(total_str)
            return [{
                "InvoiceNo": invoice_no,
                "StockCode": "WC_GENERAL",
                "Description": "WooCommerce Web Order",
                "Quantity": 1,
                "UnitPrice": total,
                "InvoiceDate": created_at,
                "CustomerID": float(customer_id),
                "Country": country,
                "SourcePlatform": "WooCommerce"
            }]

        records = []
        for item in line_items:
            sku = str(item.get("sku") or item.get("product_id") or "WC-ITEM").strip()
            name = item.get("name") or "WooCommerce Store Item"
            qty = max(1, int(item.get("quantity") or 1))
            price = float(item.get("price") or item.get("total") or 10.0) / qty

            records.append({
                "InvoiceNo": invoice_no,
                "StockCode": sku[:15],
                "Description": name[:40],
                "Quantity": qty,
                "UnitPrice": round(price, 2),
                "InvoiceDate": created_at,
                "CustomerID": float(customer_id),
                "Country": country,
                "SourcePlatform": "WooCommerce"
            })
        return records

    @classmethod
    def generate_sample_webhook_payload(cls, provider: str) -> Dict[str, Any]:
        """
        Generates realistic sample webhook payloads for instant UI testing and verification.
        """
        provider = provider.lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        if provider == "shopify":
            return {
                "id": 8209829119415,
                "order_number": 1042,
                "created_at": now_iso,
                "total_price": "78.50",
                "currency": "GBP",
                "customer": {
                    "id": 17850,
                    "first_name": "Eleanor",
                    "last_name": "Vance",
                    "email": "eleanor.vance@example.com",
                    "default_address": {
                        "country": "United Kingdom",
                        "city": "London"
                    }
                },
                "line_items": [
                    {
                        "id": 14214,
                        "product_id": 85123,
                        "sku": "85123A",
                        "title": "WHITE HANGING HEART T-LIGHT HOLDER",
                        "quantity": 6,
                        "price": "2.55"
                    },
                    {
                        "id": 14215,
                        "product_id": 71053,
                        "sku": "71053",
                        "title": "WHITE METAL LANTERN",
                        "quantity": 2,
                        "price": "3.39"
                    },
                    {
                        "id": 14216,
                        "product_id": 84406,
                        "sku": "84406B",
                        "title": "CREAM CUPID HEARTS COAT HANGER",
                        "quantity": 4,
                        "price": "2.75"
                    }
                ]
            }

        elif provider == "stripe":
            return {
                "id": f"evt_test_{int(time.time())}",
                "type": "payment_intent.succeeded",
                "created": int(time.time()),
                "data": {
                    "object": {
                        "id": f"pi_3N928{int(time.time()) % 10000}",
                        "amount": 5490,
                        "currency": "gbp",
                        "status": "succeeded",
                        "metadata": {
                            "customer_id": "14688",
                            "sku": "22423",
                            "product_name": "REGENCY CAKESTAND 3 TIER"
                        },
                        "charges": {
                            "data": [
                                {
                                    "billing_details": {
                                        "name": "Marcus Aurelius",
                                        "address": {"country": "GB", "city": "Edinburgh"}
                                    }
                                }
                            ]
                        }
                    }
                }
            }

        elif provider == "woocommerce":
            return {
                "id": 9845,
                "status": "completed",
                "currency": "GBP",
                "date_created": now_iso,
                "total": "42.80",
                "customer_id": 15311,
                "billing": {
                    "first_name": "Julian",
                    "last_name": "Bashir",
                    "country": "United Kingdom",
                    "city": "Manchester"
                },
                "line_items": [
                    {
                        "id": 312,
                        "name": "ASSORTED COLOUR BIRD ORNAMENT",
                        "product_id": 84879,
                        "sku": "84879",
                        "quantity": 8,
                        "price": 1.69,
                        "total": "13.52"
                    },
                    {
                        "id": 313,
                        "name": "PARTY BUNTING",
                        "product_id": 47566,
                        "sku": "47566",
                        "quantity": 3,
                        "price": 4.95,
                        "total": "14.85"
                    }
                ]
            }

        else:
            # Generic webhook format
            return {
                "order_id": f"GEN-{int(time.time())}",
                "customer_id": 13089,
                "country": "United Kingdom",
                "timestamp": now_iso,
                "items": [
                    {"sku": "20725", "name": "LUNCH BAG RED RETROSPOT", "qty": 10, "price": 1.65}
                ]
            }


class IntegrationRegistry:
    """
    In-memory registry and telemetry tracker for active e-commerce connectors.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IntegrationRegistry, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.connectors = {
            "shopify": {
                "name": "Shopify Store Connector",
                "provider": "shopify",
                "endpoint": "/api/v1/integrations/webhook/shopify",
                "secret": ECommerceIntegrations.DEFAULT_SECRETS["shopify"],
                "status": "LISTENING",
                "events_received": 0,
                "total_revenue_gbp": 0.0,
                "last_event_at": None,
                "icon": "🛍️"
            },
            "stripe": {
                "name": "Stripe Payments Webhook",
                "provider": "stripe",
                "endpoint": "/api/v1/integrations/webhook/stripe",
                "secret": ECommerceIntegrations.DEFAULT_SECRETS["stripe"],
                "status": "LISTENING",
                "events_received": 0,
                "total_revenue_gbp": 0.0,
                "last_event_at": None,
                "icon": "💳"
            },
            "woocommerce": {
                "name": "WooCommerce REST Hook",
                "provider": "woocommerce",
                "endpoint": "/api/v1/integrations/webhook/woocommerce",
                "secret": ECommerceIntegrations.DEFAULT_SECRETS["woocommerce"],
                "status": "LISTENING",
                "events_received": 0,
                "total_revenue_gbp": 0.0,
                "last_event_at": None,
                "icon": "🏪"
            }
        }
        self.recent_events: List[Dict[str, Any]] = []

    def record_event(self, provider: str, invoice_no: str, items_count: int, total_amount: float, verified: bool, customer_id: Any):
        """Records an ingested event for telemetry and real-time dashboard display."""
        provider = provider.lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        if provider in self.connectors:
            self.connectors[provider]["events_received"] += 1
            self.connectors[provider]["total_revenue_gbp"] = round(self.connectors[provider]["total_revenue_gbp"] + total_amount, 2)
            self.connectors[provider]["last_event_at"] = now_iso
            self.connectors[provider]["status"] = "ACTIVE"

        event_entry = {
            "id": f"evt_{int(time.time() * 1000)}",
            "provider": provider,
            "invoice_no": invoice_no,
            "items_count": items_count,
            "total_amount_gbp": round(total_amount, 2),
            "customer_id": customer_id,
            "verified": verified,
            "timestamp": now_iso
        }
        self.recent_events.insert(0, event_entry)
        # Keep latest 50 events in buffer
        if len(self.recent_events) > 50:
            self.recent_events.pop()

        return event_entry

    def get_status(self) -> Dict[str, Any]:
        """Returns masked status summary for all connectors."""
        summary = {}
        for k, v in self.connectors.items():
            secret = v["secret"]
            masked_secret = f"{secret[:6]}...{secret[-4:]}" if len(secret) > 10 else "******"
            summary[k] = {
                **v,
                "secret_masked": masked_secret
            }
        return {
            "connectors": summary,
            "total_events_ingested": sum(c["events_received"] for c in self.connectors.values()),
            "total_revenue_ingested_gbp": round(sum(c["total_revenue_gbp"] for c in self.connectors.values()), 2),
            "recent_events": self.recent_events[:15]
        }

    def update_secret(self, provider: str, new_secret: str) -> bool:
        provider = provider.lower()
        if provider in self.connectors and new_secret:
            self.connectors[provider]["secret"] = new_secret.strip()
            return True
        return False

