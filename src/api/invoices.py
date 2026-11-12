"""
Indian GST (CGST / SGST / IGST + HSN) & Multi-Jurisdiction VAT Tax Invoice Engine (Phase 28).

Primary Mode (Indian GST):
- Maps retail SKUs to statutory 4-digit HSN codes with multi-slab GST rates (5%, 12%, 18%).
- Splits intra-state supply (Seller State == Place of Supply) into CGST + SGST (50/50).
- Applies IGST for inter-state supply and 0% IGST under LUT for Export.
- Supports both real DuckDB historical invoices (and C-prefixed Credit Notes) from
  online_retail_cleaned.parquet as well as on-demand POS Tax Invoice generation and
  print/PDF-ready HTML5 rendering.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

PARQUET_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"

STATE_CODES: Dict[str, str] = {
    "Karnataka": "29",
    "Maharashtra": "27",
    "Delhi": "07",
    "Tamil Nadu": "33",
    "Uttar Pradesh": "09",
    "Gujarat": "24",
    "West Bengal": "19",
    "Telangana": "36",
    "Export": "96",
}

EU_VAT_RATES: Dict[str, float] = {
    "Germany": 19.0,
    "France": 20.0,
    "Netherlands": 21.0,
    "EIRE": 23.0,
    "Ireland": 23.0,
    "Spain": 21.0,
    "Italy": 22.0,
    "Belgium": 21.0,
    "Portugal": 23.0,
    "Austria": 20.0,
    "Sweden": 25.0,
    "Denmark": 25.0,
    "Finland": 24.0,
    "Poland": 23.0,
}

# Keyword -> (HSN Code, Statutory GST Slab %)
HSN_SLAB_RULES = [
    ("CARD", "4911", 5.0),
    ("STICKER", "4911", 5.0),
    ("T-LIGHT", "3406", 12.0),
    ("CANDLE", "3406", 12.0),
    ("LANTERN", "9405", 12.0),
    ("LIGHT", "9405", 12.0),
    ("TEACUP", "6912", 12.0),
    ("SAUCER", "6912", 12.0),
    ("MUG", "6912", 12.0),
    ("CAKESTAND", "7323", 12.0),
    ("CAKE", "7323", 12.0),
    ("BUNTING", "9505", 12.0),
    ("PARTY", "9505", 12.0),
    ("BIRD", "9505", 12.0),
    ("ALARM", "9105", 18.0),
    ("CLOCK", "9105", 18.0),
    ("BAG", "4202", 18.0),
    ("LUNCH", "4202", 18.0),
    ("HANGER", "7323", 12.0),
    ("BOX", "4819", 18.0),
]


def resolve_hsn_and_gst_rate(description: str) -> tuple[str, float]:
    upper = str(description or "").upper()
    for kw, hsn, slab in HSN_SLAB_RULES:
        if kw in upper:
            return hsn, slab
    return "9983", 18.0


def _synthetic_catalog() -> Dict[str, Dict[str, Any]]:
    return {
        "536365": {
            "invoice_no": "536365",
            "invoice_date": "2010-12-01 08:26:00",
            "customer_id": "17850",
            "country": "India",
            "is_credit_note": False,
            "items": [
                {"stock_code": "85123A", "description": "WHITE HANGING HEART T-LIGHT HOLDER", "quantity": 6, "unit_price": 255.00},
                {"stock_code": "71053", "description": "WHITE METAL LANTERN", "quantity": 6, "unit_price": 339.00},
                {"stock_code": "85099B", "description": "JUMBO BAG RED RETROSPOT", "quantity": 4, "unit_price": 179.00},
            ],
        },
        "536370": {
            "invoice_no": "536370",
            "invoice_date": "2010-12-01 08:45:00",
            "customer_id": "12583",
            "country": "France",
            "is_credit_note": False,
            "items": [
                {"stock_code": "22728", "description": "ALARM CLOCK BAKELIKE PINK", "quantity": 24, "unit_price": 3.75},
                {"stock_code": "22727", "description": "ALARM CLOCK BAKELIKE RED", "quantity": 24, "unit_price": 3.75},
            ],
        },
        "536381": {
            "invoice_no": "536381",
            "invoice_date": "2010-12-01 09:41:00",
            "customer_id": "14646",
            "country": "Netherlands",
            "is_credit_note": False,
            "items": [
                {"stock_code": "22423", "description": "REGENCY CAKESTAND 3 TIER", "quantity": 24, "unit_price": 10.95},
                {"stock_code": "85099B", "description": "JUMBO BAG RED RETROSPOT", "quantity": 40, "unit_price": 1.79},
            ],
        },
        "C536379": {
            "invoice_no": "C536379",
            "invoice_date": "2010-12-01 09:41:00",
            "customer_id": "14527",
            "country": "India",
            "is_credit_note": True,
            "items": [
                {"stock_code": "85099B", "description": "RETURN ADJUSTMENT - JUMBO BAG RETROSPOT", "quantity": -2, "unit_price": 179.00},
            ],
        },
    }


def compute_tax_mode(
    country: str,
    tax_regime: str = "GST",
    buyer_tax_id: Optional[str] = None,
    seller_state: str = "Karnataka",
    supply_state: str = "Karnataka",
) -> Dict[str, Any]:
    """Determines whether GST uses Intra-State (CGST+SGST), Inter-State (IGST), Export LUT, or VAT."""
    regime = (tax_regime or "GST").strip().upper()
    clean_country = (country or "India").strip()
    clean_supply = (supply_state or seller_state).strip()
    clean_seller = (seller_state or "Karnataka").strip()
    has_buyer_id = bool(buyer_tax_id and len(buyer_tax_id.strip()) >= 4)

    if regime == "GST":
        seller_code = STATE_CODES.get(clean_seller, "29")
        supply_code = STATE_CODES.get(clean_supply, "96")
        if clean_supply.lower() == "export":
            return {
                "tax_regime": "GST",
                "gst_supply_type": "EXPORT_LUT",
                "jurisdiction": f"India Export under LUT (0% IGST, State Code {supply_code})",
                "reverse_charge": False,
                "seller_state_code": seller_code,
                "supply_state_code": supply_code,
                "fixed_rate_override": 0.0,
            }
        if clean_supply.lower() == clean_seller.lower():
            return {
                "tax_regime": "GST",
                "gst_supply_type": "INTRA_STATE",
                "jurisdiction": f"Intra-State Supply ({clean_supply} [{supply_code}] — CGST + SGST)",
                "reverse_charge": False,
                "seller_state_code": seller_code,
                "supply_state_code": supply_code,
                "fixed_rate_override": None,
            }
        return {
            "tax_regime": "GST",
            "gst_supply_type": "INTER_STATE",
            "jurisdiction": f"Inter-State Supply ({clean_seller} [{seller_code}] → {clean_supply} [{supply_code}] — IGST)",
            "reverse_charge": False,
            "seller_state_code": seller_code,
            "supply_state_code": supply_code,
            "fixed_rate_override": None,
        }

    # Optional UK / EU VAT fallback
    if clean_country == "United Kingdom":
        return {
            "tax_regime": "VAT",
            "gst_supply_type": "UK_VAT",
            "jurisdiction": "United Kingdom (HMRC Standard VAT 20%)",
            "reverse_charge": False,
            "seller_state_code": "GB",
            "supply_state_code": "GB",
            "fixed_rate_override": 20.0,
        }
    if clean_country in EU_VAT_RATES:
        rate = 0.0 if has_buyer_id else EU_VAT_RATES[clean_country]
        desc = "EU B2B Reverse Charge (0%)" if has_buyer_id else f"{clean_country} Destination EU VAT ({rate:.0f}%)"
        return {
            "tax_regime": "VAT",
            "gst_supply_type": "EU_VAT",
            "jurisdiction": desc,
            "reverse_charge": has_buyer_id,
            "seller_state_code": "GB",
            "supply_state_code": "EU",
            "fixed_rate_override": rate,
        }
    return {
        "tax_regime": "VAT",
        "gst_supply_type": "EXPORT_VAT_ZERO",
        "jurisdiction": f"{clean_country} (Zero-Rated Export 0%)",
        "reverse_charge": False,
        "seller_state_code": "GB",
        "supply_state_code": "EXP",
        "fixed_rate_override": 0.0,
    }


class TaxInvoiceEngine:
    """Builds statutory Indian GST (CGST/SGST/IGST + HSN) & VAT Tax Invoices and Credit Notes."""

    def __init__(self, data_path: Path = PARQUET_PATH):
        self.data_path = data_path
        self._synthetic = _synthetic_catalog()
        self._generated_store: Dict[str, Dict[str, Any]] = {}

    def _fetch_raw_invoice(self, invoice_no: str) -> Optional[Dict[str, Any]]:
        inv = str(invoice_no or "").strip()
        if not inv:
            return None
        if inv in self._generated_store:
            return self._generated_store[inv]

        if self.data_path.exists():
            try:
                con = duckdb.connect(database=":memory:")
                rows = con.execute(
                    """
                    SELECT
                        CAST(InvoiceNo AS VARCHAR) AS invoice_no,
                        CAST(InvoiceDate AS VARCHAR) AS invoice_date,
                        COALESCE(CAST(CAST(CustomerID AS BIGINT) AS VARCHAR), 'Guest') AS customer_id,
                        CAST(Country AS VARCHAR) AS country,
                        CAST(IsCancelled AS BOOLEAN) AS is_cancelled,
                        CAST(StockCode AS VARCHAR) AS stock_code,
                        CAST(Description AS VARCHAR) AS description,
                        CAST(Quantity AS BIGINT) AS quantity,
                        CAST(UnitPrice AS DOUBLE) AS unit_price
                    FROM read_parquet(?)
                    WHERE CAST(InvoiceNo AS VARCHAR) = ?
                    LIMIT 100
                    """,
                    [str(self.data_path), inv],
                ).fetchall()
                con.close()
                if rows:
                    first = rows[0]
                    is_cn = bool(first[4]) or inv.upper().startswith("C")
                    return {
                        "invoice_no": str(first[0]),
                        "invoice_date": str(first[1]),
                        "customer_id": str(first[2]),
                        "country": str(first[3]),
                        "is_credit_note": is_cn,
                        "items": [
                            {
                                "stock_code": str(r[5]),
                                "description": str(r[6]),
                                "quantity": int(r[7]),
                                "unit_price": round(float(r[8]), 2),
                            }
                            for r in rows
                        ],
                    }
            except Exception:
                pass

        return self._synthetic.get(inv)

    def _price_invoice(
        self,
        raw: Dict[str, Any],
        tax_regime: str = "GST",
        buyer_tax_id: Optional[str] = None,
        seller_state: str = "Karnataka",
        supply_state: str = "Karnataka",
    ) -> Dict[str, Any]:
        is_cn = bool(raw.get("is_credit_note")) or str(raw.get("invoice_no", "")).upper().startswith("C")
        mode = compute_tax_mode(
            country=raw.get("country", "India"),
            tax_regime=tax_regime,
            buyer_tax_id=buyer_tax_id,
            seller_state=seller_state,
            supply_state=supply_state,
        )
        is_gst = mode["tax_regime"] == "GST"
        currency = "INR" if is_gst else "GBP"
        sym = "₹" if is_gst else "£"

        priced_lines: List[Dict[str, Any]] = []
        subtotal_net = 0.0
        cgst_total = 0.0
        sgst_total = 0.0
        igst_total = 0.0
        vat_total = 0.0

        for idx, item in enumerate(raw.get("items", []), start=1):
            qty = int(item.get("quantity", 1))
            if is_cn and qty > 0:
                qty = -qty
            unit_price = round(float(item.get("unit_price", 0.0)), 2)
            desc = str(item.get("description", "Retail Merchandise"))
            hsn, hsn_gst_rate = resolve_hsn_and_gst_rate(desc)
            rate_pct = hsn_gst_rate if mode["fixed_rate_override"] is None else float(mode["fixed_rate_override"])

            net = round(qty * unit_price, 2)
            line_tax = round(net * (rate_pct / 100.0), 2)

            line_cgst = 0.0
            line_sgst = 0.0
            line_igst = 0.0
            line_vat = 0.0
            if is_gst:
                if mode["gst_supply_type"] == "INTRA_STATE":
                    line_cgst = round(line_tax / 2.0, 2)
                    line_sgst = round(line_tax - line_cgst, 2)
                else:
                    line_igst = line_tax
            else:
                line_vat = line_tax

            gross = round(net + line_tax, 2)
            subtotal_net = round(subtotal_net + net, 2)
            cgst_total = round(cgst_total + line_cgst, 2)
            sgst_total = round(sgst_total + line_sgst, 2)
            igst_total = round(igst_total + line_igst, 2)
            vat_total = round(vat_total + line_vat, 2)

            priced_lines.append({
                "line_no": idx,
                "stock_code": str(item.get("stock_code", "")),
                "hsn_code": hsn,
                "description": desc,
                "quantity": qty,
                "unit_price": unit_price,
                "taxable_value": net,
                "tax_rate_pct": rate_pct,
                "cgst_amount": line_cgst,
                "sgst_amount": line_sgst,
                "igst_amount": line_igst,
                "tax_amount": line_tax,
                "gross_amount": gross,
            })

        total_tax = round(cgst_total + sgst_total + igst_total + vat_total, 2)
        grand_total = round(subtotal_net + total_tax, 2)

        components = []
        if is_gst:
            if mode["gst_supply_type"] == "INTRA_STATE":
                components = [
                    {"label": "CGST (Central Tax)", "rate_pct": "Split 50%", "amount": cgst_total},
                    {"label": "SGST (State Tax)", "rate_pct": "Split 50%", "amount": sgst_total},
                ]
            elif mode["gst_supply_type"] == "INTER_STATE":
                components = [{"label": "IGST (Integrated Tax)", "rate_pct": "HSN Slab", "amount": igst_total}]
            else:
                components = [{"label": "IGST (Export LUT 0%)", "rate_pct": "0.0%", "amount": 0.0}]
        else:
            eff_rate = round((total_tax / subtotal_net) * 100.0, 1) if subtotal_net else 0.0
            components = [{"label": f"{mode['tax_regime']} Tax", "rate_pct": f"{eff_rate}%", "amount": vat_total}]

        irn_hash = hashlib.sha256(f"{raw['invoice_no']}|{grand_total}|{supply_state}".encode("utf-8")).hexdigest()
        weighted_rate_pct = round((abs(total_tax) / abs(subtotal_net)) * 100.0, 2) if subtotal_net else 0.0

        return {
            "status": "success",
            "document_type": "CREDIT NOTE" if is_cn else "TAX INVOICE",
            "invoice_no": str(raw["invoice_no"]),
            "invoice_date": str(raw.get("invoice_date", dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))),
            "irn_reference": irn_hash if is_gst else None,
            "seller": {
                "legal_name": "Nexus Retail AI Commerce Pvt Ltd" if is_gst else "Nexus Retail AI Flagship Ltd",
                "tax_id_label": "GSTIN" if is_gst else "UK VAT Reg",
                "tax_id": "29AAACN4192K1ZV" if is_gst else "GB-394-8821-09",
                "state": f"{seller_state} ({mode['seller_state_code']})",
                "address": "100ft Road, Indiranagar, Bengaluru, Karnataka 560038, India" if is_gst else "221B Baker Commerce Way, London W1U 6SG, UK",
            },
            "buyer": {
                "customer_id": str(raw.get("customer_id", "Guest")),
                "country": str(raw.get("country", "India" if is_gst else "United Kingdom")),
                "buyer_tax_id": buyer_tax_id or ("Unregistered Consumer (B2C)"),
                "place_of_supply": f"{supply_state} ({mode['supply_state_code']})" if is_gst else str(raw.get("country", "United Kingdom")),
            },
            "tax_summary": {
                "tax_regime": mode["tax_regime"],
                "gst_supply_type": mode["gst_supply_type"],
                "jurisdiction": mode["jurisdiction"],
                "reverse_charge": mode["reverse_charge"],
                "effective_rate_pct": weighted_rate_pct,
                "cgst_total": cgst_total,
                "sgst_total": sgst_total,
                "igst_total": igst_total,
                "vat_total": vat_total,
                "components": components,
            },
            "items": priced_lines,
            "totals": {
                "currency": currency,
                "currency_symbol": sym,
                "line_count": len(priced_lines),
                "subtotal_net": subtotal_net,
                "total_tax": total_tax,
                "grand_total": grand_total,
            },
        }

    def get_invoice(
        self,
        invoice_no: str,
        tax_regime: str = "GST",
        buyer_tax_id: Optional[str] = None,
        seller_state: str = "Karnataka",
        supply_state: str = "Karnataka",
    ) -> Optional[Dict[str, Any]]:
        raw = self._fetch_raw_invoice(invoice_no)
        if raw is None:
            return None
        return self._price_invoice(
            raw=raw,
            tax_regime=tax_regime,
            buyer_tax_id=buyer_tax_id,
            seller_state=seller_state,
            supply_state=supply_state,
        )

    def list_recent_invoices(self, limit: int = 15, country: Optional[str] = None) -> Dict[str, Any]:
        limit = max(1, min(50, int(limit)))
        invoices: List[Dict[str, Any]] = []

        for inv in reversed(list(self._generated_store.values())):
            if country and country != "All" and inv.get("country") != country:
                continue
            priced = self._price_invoice(inv)
            invoices.append({
                "invoice_no": priced["invoice_no"],
                "document_type": priced["document_type"],
                "invoice_date": priced["invoice_date"],
                "customer_id": priced["buyer"]["customer_id"],
                "country": priced["buyer"]["country"],
                "line_count": priced["totals"]["line_count"],
                "grand_total": priced["totals"]["grand_total"],
                "currency": priced["totals"]["currency"],
            })

        if len(invoices) < limit and self.data_path.exists():
            try:
                con = duckdb.connect(database=":memory:")
                where_clause = ""
                params: List[Any] = []
                if country and country != "All":
                    where_clause = "WHERE CAST(Country AS VARCHAR) = ?"
                    params.append(country)
                params.append(limit - len(invoices))
                rows = con.execute(
                    f"""
                    SELECT
                        CAST(InvoiceNo AS VARCHAR) AS invoice_no,
                        MIN(CAST(InvoiceDate AS VARCHAR)) AS invoice_date,
                        COALESCE(CAST(CAST(MAX(CustomerID) AS BIGINT) AS VARCHAR), 'Guest') AS customer_id,
                        MAX(CAST(Country AS VARCHAR)) AS country,
                        COUNT(*) AS line_count,
                        ROUND(SUM(TotalPrice), 2) AS gross_val,
                        MAX(CAST(IsCancelled AS INTEGER)) AS is_cn
                    FROM read_parquet(?)
                    {where_clause}
                    GROUP BY InvoiceNo
                    ORDER BY MIN(InvoiceDate) ASC
                    LIMIT ?
                    """,
                    [str(self.data_path)] + params,
                ).fetchall()
                con.close()
                for r in rows:
                    inv_id = str(r[0])
                    is_cn = bool(r[6]) or inv_id.upper().startswith("C")
                    invoices.append({
                        "invoice_no": inv_id,
                        "document_type": "CREDIT NOTE" if is_cn else "TAX INVOICE",
                        "invoice_date": str(r[1]),
                        "customer_id": str(r[2]),
                        "country": str(r[3]),
                        "line_count": int(r[4]),
                        "grand_total": round(float(r[5]), 2),
                        "currency": "INR",
                    })
            except Exception:
                pass

        if len(invoices) < limit:
            for raw in self._synthetic.values():
                if country and country != "All" and raw["country"] != country:
                    continue
                if any(x["invoice_no"] == raw["invoice_no"] for x in invoices):
                    continue
                priced = self._price_invoice(raw)
                invoices.append({
                    "invoice_no": priced["invoice_no"],
                    "document_type": priced["document_type"],
                    "invoice_date": priced["invoice_date"],
                    "customer_id": priced["buyer"]["customer_id"],
                    "country": priced["buyer"]["country"],
                    "line_count": priced["totals"]["line_count"],
                    "grand_total": priced["totals"]["grand_total"],
                    "currency": priced["totals"]["currency"],
                })

        return {"status": "healthy", "count": len(invoices[:limit]), "invoices": invoices[:limit]}

    def generate_invoice(
        self,
        customer_id: str,
        country: str,
        items: List[Dict[str, Any]],
        tax_regime: str = "GST",
        buyer_tax_id: Optional[str] = None,
        seller_state: str = "Karnataka",
        supply_state: str = "Karnataka",
        is_credit_note: bool = False,
    ) -> Dict[str, Any]:
        prefix = "CN" if is_credit_note else "INV"
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
        seq = uuid.uuid4().hex[:5].upper()
        invoice_no = f"{prefix}-{stamp}-{seq}"

        raw = {
            "invoice_no": invoice_no,
            "invoice_date": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "customer_id": str(customer_id or "Guest").strip(),
            "country": str(country or "India").strip(),
            "is_credit_note": bool(is_credit_note),
            "items": items,
        }
        self._generated_store[invoice_no] = raw
        return self._price_invoice(
            raw=raw,
            tax_regime=tax_regime,
            buyer_tax_id=buyer_tax_id,
            seller_state=seller_state,
            supply_state=supply_state,
        )

    def render_invoice_html(self, invoice: Dict[str, Any]) -> str:
        """Renders a self-contained print/PDF-ready statutory Indian GST or VAT HTML5 Tax Invoice."""
        esc = html.escape
        doc_type = esc(invoice["document_type"])
        seller = invoice["seller"]
        buyer = invoice["buyer"]
        tax = invoice["tax_summary"]
        totals = invoice["totals"]
        sym = esc(totals["currency_symbol"])

        rows_html = "\n".join(
            f"""
            <tr>
                <td>{line['line_no']}</td>
                <td><code>{esc(line['stock_code'])}</code></td>
                <td><strong>{esc(line['hsn_code'])}</strong></td>
                <td>{esc(line['description'])}</td>
                <td class="num">{line['quantity']}</td>
                <td class="num">{sym}{line['unit_price']:.2f}</td>
                <td class="num">{sym}{line['taxable_value']:.2f}</td>
                <td class="num">{line['tax_rate_pct']:.1f}% ({sym}{line['tax_amount']:.2f})</td>
                <td class="num"><strong>{sym}{line['gross_amount']:.2f}</strong></td>
            </tr>
            """
            for line in invoice["items"]
        )

        comp_rows = "\n".join(
            f"<tr><td>{esc(str(c['label']))} ({esc(str(c['rate_pct']))})</td><td class='num'>{sym}{c['amount']:.2f}</td></tr>"
            for c in tax["components"]
        )

        irn_block = (
            f"<div style='font-size:0.75rem;color:#475569;margin-top:0.35rem;'>IRN: <code>{esc(invoice['irn_reference'][:32])}...</code></div>"
            if invoice.get("irn_reference")
            else ""
        )

        badge_bg = "#FEE2E2" if invoice["document_type"] == "CREDIT NOTE" else "#DBEAFE"
        badge_fg = "#991B1B" if invoice["document_type"] == "CREDIT NOTE" else "#1E40AF"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{doc_type} {esc(invoice['invoice_no'])}</title>
<style>
  @page {{ margin: 14mm; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #0F172A; margin: 2rem auto; max-width: 920px; line-height: 1.45; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0F172A; padding-bottom: 1rem; margin-bottom: 1.25rem; }}
  .doc-badge {{ display: inline-block; padding: 0.35rem 0.75rem; font-weight: 700; font-size: 0.85rem; border-radius: 6px; background: {badge_bg}; color: {badge_fg}; letter-spacing: 0.04em; }}
  .parties {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; font-size: 0.9rem; }}
  .box {{ border: 1px solid #CBD5E1; border-radius: 8px; padding: 0.85rem 1rem; background: #F8FAFC; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 0.75rem; font-size: 0.85rem; }}
  th, td {{ border-bottom: 1px solid #E2E8F0; padding: 0.55rem 0.45rem; text-align: left; }}
  th {{ background: #F1F5F9; font-weight: 600; color: #334155; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .totals-box {{ margin-left: auto; width: 340px; margin-top: 1.25rem; border: 1px solid #CBD5E1; border-radius: 8px; padding: 0.75rem 1rem; background: #F8FAFC; }}
  .totals-box table {{ margin-top: 0; }}
  .grand {{ font-size: 1.05rem; font-weight: 700; border-top: 2px solid #0F172A; }}
  .print-btn {{ margin-bottom: 1rem; padding: 0.5rem 1rem; background: #2563EB; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }}
  @media print {{ .print-btn {{ display: none; }} body {{ margin: 0; }} }}
</style>
</head>
<body>
  <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
  <div class="header">
    <div>
      <h1 style="margin:0 0 0.25rem 0;">{esc(seller['legal_name'])}</h1>
      <div style="font-size:0.85rem;color:#475569;">{esc(seller['tax_id_label'])}: <strong>{esc(seller['tax_id'])}</strong> | State: {esc(seller['state'])}</div>
      <div style="font-size:0.85rem;color:#475569;">{esc(seller['address'])}</div>
      {irn_block}
    </div>
    <div style="text-align:right;">
      <span class="doc-badge">{doc_type}</span>
      <div style="margin-top:0.5rem;font-size:0.95rem;"><strong>#{esc(invoice['invoice_no'])}</strong></div>
      <div style="font-size:0.82rem;color:#475569;">Date: {esc(invoice['invoice_date'])}</div>
    </div>
  </div>
  <div class="parties">
    <div class="box">
      <strong>Bill To / Recipient</strong><br>
      Customer Account: #{esc(buyer['customer_id'])}<br>
      Country: {esc(buyer['country'])}<br>
      Buyer GSTIN / Tax ID: {esc(buyer['buyer_tax_id'])}<br>
      Place of Supply: {esc(buyer['place_of_supply'])}
    </div>
    <div class="box">
      <strong>Tax Regime &amp; Compliance</strong><br>
      Regime: {esc(tax['tax_regime'])} ({esc(tax['gst_supply_type'])})<br>
      Supply Rule: {esc(tax['jurisdiction'])}<br>
      Reverse Charge: {"Yes" if tax['reverse_charge'] else "No"}<br>
      Blended Effective Rate: {tax['effective_rate_pct']:.2f}%
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>SKU</th><th>HSN</th><th>Description</th><th class="num">Qty</th><th class="num">Unit Rate</th><th class="num">Taxable Value</th><th class="num">GST / Tax</th><th class="num">Total</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <div class="totals-box">
    <table>
      <tr><td>Taxable Value (Net)</td><td class="num">{sym}{totals['subtotal_net']:.2f}</td></tr>
      {comp_rows}
      <tr><td>Total Tax</td><td class="num">{sym}{totals['total_tax']:.2f}</td></tr>
      <tr class="grand"><td><strong>Grand Total ({esc(totals['currency'])})</strong></td><td class="num"><strong>{sym}{totals['grand_total']:.2f}</strong></td></tr>
    </table>
  </div>
</body>
</html>"""


_INVOICE_ENGINE_SINGLETON: Optional[TaxInvoiceEngine] = None


def get_invoice_engine() -> TaxInvoiceEngine:
    global _INVOICE_ENGINE_SINGLETON
    if _INVOICE_ENGINE_SINGLETON is None:
        _INVOICE_ENGINE_SINGLETON = TaxInvoiceEngine()
    return _INVOICE_ENGINE_SINGLETON
