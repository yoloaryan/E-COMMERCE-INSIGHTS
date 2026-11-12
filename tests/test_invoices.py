"""
Unit & Integration Tests for Phase 28: Indian GST (CGST/SGST/IGST + HSN) & VAT Tax Invoice Engine.
"""

from fastapi.testclient import TestClient

from src.api.invoices import TaxInvoiceEngine
from src.api.server import app

client = TestClient(app)


def test_indian_gst_intra_vs_inter_state_and_hsn_slabs(tmp_path):
    engine = TaxInvoiceEngine(data_path=tmp_path / "missing.parquet")

    # Intra-State supply: Karnataka -> Karnataka => CGST + SGST split, per-HSN slabs (12% + 18%)
    intra = engine.get_invoice("536365", tax_regime="GST", seller_state="Karnataka", supply_state="Karnataka")
    assert intra is not None
    assert intra["document_type"] == "TAX INVOICE"
    assert intra["tax_summary"]["gst_supply_type"] == "INTRA_STATE"
    assert intra["tax_summary"]["igst_total"] == 0.0
    assert intra["tax_summary"]["cgst_total"] > 0.0
    assert intra["tax_summary"]["sgst_total"] > 0.0
    assert abs((intra["totals"]["subtotal_net"] + intra["totals"]["total_tax"]) - intra["totals"]["grand_total"]) < 1e-6

    # Check HSN mapping on items: T-LIGHT (3406 -> 12%) vs BAG (4202 -> 18%)
    hsn_map = {item["stock_code"]: (item["hsn_code"], item["tax_rate_pct"]) for item in intra["items"]}
    assert hsn_map["85123A"] == ("3406", 12.0)
    assert hsn_map["85099B"] == ("4202", 18.0)

    # Inter-State supply: Karnataka -> Maharashtra => IGST only
    inter = engine.get_invoice("536365", tax_regime="GST", seller_state="Karnataka", supply_state="Maharashtra")
    assert inter["tax_summary"]["gst_supply_type"] == "INTER_STATE"
    assert inter["tax_summary"]["cgst_total"] == 0.0
    assert inter["tax_summary"]["sgst_total"] == 0.0
    assert inter["tax_summary"]["igst_total"] == inter["totals"]["total_tax"]

    # Export under LUT => 0% tax
    export_lut = engine.get_invoice("536365", tax_regime="GST", seller_state="Karnataka", supply_state="Export")
    assert export_lut["tax_summary"]["gst_supply_type"] == "EXPORT_LUT"
    assert export_lut["totals"]["total_tax"] == 0.0
    assert export_lut["totals"]["grand_total"] == export_lut["totals"]["subtotal_net"]

    # Credit Note C536379
    cn = engine.get_invoice("C536379", tax_regime="GST", seller_state="Karnataka", supply_state="Karnataka")
    assert cn["document_type"] == "CREDIT NOTE"
    assert cn["totals"]["subtotal_net"] < 0
    assert cn["totals"]["total_tax"] < 0
    assert cn["totals"]["grand_total"] < 0


def test_vat_domestic_reverse_charge_and_export(tmp_path):
    engine = TaxInvoiceEngine(data_path=tmp_path / "missing.parquet")

    b2c_fr = engine.get_invoice("536370", tax_regime="VAT")
    assert b2c_fr["tax_summary"]["tax_regime"] == "VAT"
    assert b2c_fr["tax_summary"]["effective_rate_pct"] == 20.0
    assert b2c_fr["tax_summary"]["reverse_charge"] is False

    b2b_rc = engine.get_invoice("536370", tax_regime="VAT", buyer_tax_id="FRXX999999999")
    assert b2b_rc["tax_summary"]["reverse_charge"] is True
    assert b2b_rc["totals"]["total_tax"] == 0.0


def test_api_tax_invoice_endpoints_and_html_export():
    res_recent = client.get("/api/v1/invoices/recent?limit=5")
    assert res_recent.status_code == 200
    assert res_recent.json()["count"] >= 1

    res_inv = client.get("/api/v1/invoices/536365?tax_regime=GST&supply_state=Karnataka")
    assert res_inv.status_code == 200
    body = res_inv.json()
    assert body["invoice_no"] == "536365"
    assert body["tax_summary"]["gst_supply_type"] == "INTRA_STATE"
    assert body["seller"]["tax_id_label"] == "GSTIN"

    res_gen = client.post(
        "/api/v1/invoices/generate",
        json={
            "customer_id": "12352",
            "country": "India",
            "tax_regime": "GST",
            "supply_state": "Maharashtra",
            "items": [
                {"stock_code": "22423", "description": "REGENCY CAKESTAND 3 TIER", "quantity": 10, "unit_price": 100.0},
            ],
        },
    )
    assert res_gen.status_code == 200
    gen_body = res_gen.json()
    assert gen_body["invoice_no"].startswith("INV-")
    assert gen_body["tax_summary"]["igst_total"] == 120.0  # HSN 7323 -> 12% of 1000
    assert gen_body["totals"]["grand_total"] == 1120.0

    gen_no = gen_body["invoice_no"]
    res_html = client.get(f"/api/v1/invoices/{gen_no}/html?tax_regime=GST&supply_state=Maharashtra")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers.get("content-type", "")
    assert "IGST" in res_html.text
    assert gen_no in res_html.text

