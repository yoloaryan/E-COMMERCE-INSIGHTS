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


def test_gstr1_monthly_return_reconciliation_and_hsn_summary(tmp_path):
    engine = TaxInvoiceEngine(data_path=tmp_path / "missing.parquet")
    ret = engine.generate_gstr1_return(period="All", supply_mode="MIXED")

    assert ret["status"] == "healthy"
    s = ret["summary"]
    assert s["gross_outward_taxable_inr"] > 0
    assert s["cdnr_credit_note_taxable_inr"] > 0
    assert abs((s["gross_outward_taxable_inr"] - s["cdnr_credit_note_taxable_inr"]) - s["net_taxable_turnover_inr"]) < 1e-6
    assert abs((s["gross_outward_gst_inr"] - s["cdnr_gst_offset_inr"]) - s["net_gst_payable_inr"]) < 1e-6
    assert abs((s["cgst_payable_inr"] + s["sgst_payable_inr"] + s["igst_payable_inr"]) - s["net_gst_payable_inr"]) < 1e-6
    assert len(ret["hsn_summary"]) >= 2
    assert len(ret["sections"]) == 3


def test_api_gstr1_return_endpoint():
    res = client.get("/api/v1/invoices/gstr1-return?period=All&supply_mode=INTRA_ONLY")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert body["summary"]["igst_payable_inr"] == 0.0
    assert body["summary"]["cgst_payable_inr"] > 0.0
    assert body["gstr1_json_payload"]["gstin"] == "29AAACN4192K1ZV"


def test_dynamic_upi_qr_code_svg_and_endpoint(tmp_path):
    from src.api.invoices import generate_dynamic_upi_qr_svg

    uri = "upi://pay?pa=prismretail@icici&pn=PrismRetail&am=1250.00&cu=INR"
    svg = generate_dynamic_upi_qr_svg(uri, size=150)
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert svg.endswith("</svg>")
    assert '<rect x="' in svg
    assert 'fill="#0F172A"' in svg

    engine = TaxInvoiceEngine(data_path=tmp_path / "missing.parquet")
    inv = engine.get_invoice("536365", tax_regime="GST")
    assert "upi_payment" in inv
    upi = inv["upi_payment"]
    assert upi["merchant_vpa"] == "prismretail@icici"
    assert upi["currency"] == "INR"
    assert upi["intent_uri"].startswith("upi://pay?pa=prismretail@icici")
    assert "<svg" in upi["qr_svg"]

    # Test QR API Endpoint
    res_qr = client.get("/api/v1/invoices/536365/qr-code")
    assert res_qr.status_code == 200
    assert "image/svg+xml" in res_qr.headers.get("content-type", "")
    assert res_qr.text.startswith("<svg")

    # Non-existent invoice returns 404
    res_404 = client.get("/api/v1/invoices/99999999/qr-code")
    assert res_404.status_code == 404


def test_statutory_eway_bill_generation_and_threshold_enforcement(tmp_path):
    import pytest
    engine = TaxInvoiceEngine(data_path=tmp_path / "missing.parquet")

    # 1. Invoice below ₹50,000 threshold raises ValueError unless force=True
    with pytest.raises(ValueError, match="below statutory E-Way Bill threshold"):
        engine.generate_eway_bill("536365", force=False)

    # 2. Force=True succeeds for any invoice
    ewb_forced = engine.generate_eway_bill(
        "536365",
        force=True,
        seller_state="Karnataka",
        supply_state="Maharashtra",
    )
    assert ewb_forced["status"] == "ACTIVE"
    assert len(ewb_forced["eway_bill_no"]) == 12
    assert ewb_forced["eway_bill_no"].startswith("29")  # Karnataka state code
    assert ewb_forced["approx_distance_km"] == 980  # Karnataka to Maharashtra distance
    assert ewb_forced["validity_days"] == 5  # ceil(980 / 200) = 5 days
    assert "<svg" in ewb_forced["verification_qr_svg"]

    # 3. High value invoice (>= ₹50,000) generates without force
    high_val_inv = engine.generate_invoice(
        customer_id="19999",
        country="India",
        items=[
            {"stock_code": "HIGHVAL1", "description": "ENTERPRISE SERVER RACK", "quantity": 10, "unit_price": 6000.0}
        ],
        tax_regime="GST",
        seller_state="Karnataka",
        supply_state="Tamil Nadu",
    )
    assert high_val_inv["totals"]["grand_total"] >= 50000.0

    ewb_high = engine.generate_eway_bill(
        high_val_inv["invoice_no"],
        force=False,
        seller_state="Karnataka",
        supply_state="Tamil Nadu",
    )
    assert ewb_high["status"] == "ACTIVE"
    assert ewb_high["approx_distance_km"] == 350
    assert ewb_high["validity_days"] == 2  # ceil(350 / 200) = 2 days

    # 4. Render HTML slip
    html_slip = engine.render_eway_bill_html(ewb_high)
    assert "<!DOCTYPE html>" in html_slip
    assert "e-Way Bill System" in html_slip
    assert ewb_high["eway_bill_no"] in html_slip
    assert "PART-A (Consignment Details)" in html_slip
    assert "PART-B (Vehicle &amp; Transporter Details)" in html_slip

    # 5. API Endpoints via client (generate high value invoice in client engine)
    res_api_gen = client.post(
        "/api/v1/invoices/generate",
        json={
            "customer_id": "19999",
            "country": "India",
            "tax_regime": "GST",
            "seller_state": "Karnataka",
            "supply_state": "Tamil Nadu",
            "items": [
                {"stock_code": "HIGHVAL1", "description": "ENTERPRISE SERVER RACK", "quantity": 10, "unit_price": 6000.0}
            ],
        },
    )
    assert res_api_gen.status_code == 200
    api_inv_no = res_api_gen.json()["invoice_no"]

    # JSON endpoint
    res_json = client.get(f"/api/v1/invoices/{api_inv_no}/eway-bill?supply_state=Tamil+Nadu")
    assert res_json.status_code == 200
    assert len(res_json.json()["eway_bill_no"]) == 12

    # HTML endpoint
    res_html = client.get(f"/api/v1/invoices/{api_inv_no}/eway-bill/html?supply_state=Tamil+Nadu")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers.get("content-type", "")
    assert "EWB-01" in res_html.text

    # Validation failure endpoint on small invoice without force
    res_err = client.get("/api/v1/invoices/536365/eway-bill?force=false")
    assert res_err.status_code == 400
    assert "below statutory" in res_err.json()["detail"]


def test_credit_note_lifecycle_and_table_9b_reconciliation(tmp_path):
    engine = TaxInvoiceEngine(data_path=tmp_path / "missing.parquet")

    # 1. Issue credit note directly from engine
    cn = engine.issue_credit_note(
        original_invoice_no="536365",
        return_items=[
            {"stock_code": "85123A", "description": "WHITE HANGING HEART T-LIGHT HOLDER", "quantity": 2, "unit_price": 2.55}
        ],
        reason="Damaged in Transit",
        customer_id="17850",
        seller_state="Karnataka",
        supply_state="Karnataka",
    )
    assert cn["invoice_no"].startswith("CN-")
    assert cn["document_type"] == "CREDIT NOTE"
    assert cn["original_invoice_reference"] == "536365"
    assert cn["credit_note_reason"] == "Damaged in Transit"
    assert cn["totals"]["subtotal_net"] < 0
    assert cn["totals"]["total_tax"] < 0
    assert cn["totals"]["grand_total"] < 0

    # 2. Check reconciliation into GSTR-1 Table 9B
    ret = engine.generate_gstr1_return(period="All")
    assert ret["summary"]["cdnr_credit_note_taxable_inr"] > 0
    # The generated credit note is in CDNR table
    cdnr_table = next(s for s in ret["sections"] if "Table 9B" in s["table"])
    assert cdnr_table["taxable_inr"] < 0

    # 3. Test API Credit Note Endpoint
    res_cn = client.post(
        "/api/v1/invoices/credit-note",
        json={
            "original_invoice_no": "536365",
            "reason": "Quality Reject / Customer Return",
            "seller_state": "Karnataka",
            "supply_state": "Maharashtra",
            "items": [
                {"stock_code": "85099B", "description": "JUMBO BAG RED RETROSPOT", "quantity": 1, "unit_price": 1.95}
            ],
        },
    )
    assert res_cn.status_code == 200
    body = res_cn.json()
    assert body["invoice_no"].startswith("CN-")
    assert body["original_invoice_reference"] == "536365"
    assert body["tax_summary"]["gst_supply_type"] == "INTER_STATE"
    assert body["totals"]["grand_total"] < 0

    # 4. Test non-existent invoice error
    res_bad = client.post(
        "/api/v1/invoices/credit-note",
        json={
            "original_invoice_no": "INVALID-99999",
            "reason": "Test",
            "items": [{"stock_code": "SKU", "quantity": 1, "unit_price": 10.0}],
        },
    )
    assert res_bad.status_code == 404

