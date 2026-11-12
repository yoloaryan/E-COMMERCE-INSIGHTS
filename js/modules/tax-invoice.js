/**
 * Phase 28: Indian GST (CGST/SGST/IGST + HSN) & Tax Invoice Studio
 * Loaded lazily on demand by app.js module router.
 */

let ACTIVE_TAX_INVOICE_CACHE = null;
let TAX_INVOICE_WIRED = false;

function _escInv(v) {
    return String(v ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function renderTaxInvoicePreview(inv) {
    const previewBox = document.getElementById("taxInvoicePreviewBox");
    if (!previewBox || !inv) return;
    ACTIVE_TAX_INVOICE_CACHE = inv;

    const sym = _escInv(inv.totals?.currency_symbol || "₹");
    const isCn = inv.document_type === "CREDIT NOTE";
    const badgeColor = isCn ? "#EF4444" : "#3B82F6";
    const seller = inv.seller || {};
    const buyer = inv.buyer || {};
    const tax = inv.tax_summary || {};
    const totals = inv.totals || {};

    const rowsHtml = (inv.items || []).map(item => `
        <tr>
            <th scope="row">${_escInv(item.stock_code)}</th>
            <td data-label="HSN">${_escInv(item.hsn_code)}</td>
            <td data-label="Description">${_escInv(item.description)}</td>
            <td data-label="Qty">${Number(item.quantity)}</td>
            <td data-label="Rate">${sym}${Number(item.unit_price).toFixed(2)}</td>
            <td data-label="Taxable">${sym}${Number(item.taxable_value).toFixed(2)}</td>
            <td data-label="CGST">${sym}${Number(item.cgst_amount).toFixed(2)}</td>
            <td data-label="SGST">${sym}${Number(item.sgst_amount).toFixed(2)}</td>
            <td data-label="IGST">${sym}${Number(item.igst_amount).toFixed(2)}</td>
            <td data-label="Total"><strong>${sym}${Number(item.gross_amount).toFixed(2)}</strong></td>
        </tr>
    `).join("");

    const compRows = (tax.components || []).map(c => `
        <div style="display:flex; justify-content:space-between; font-size:0.84rem; margin-bottom:0.25rem;">
            <span>${_escInv(c.label)} (${_escInv(c.rate_pct)})</span>
            <strong>${sym}${Number(c.amount).toFixed(2)}</strong>
        </div>
    `).join("");

    previewBox.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:1px solid var(--border-color);">
            <div>
                <span class="badge-tag" style="background:${badgeColor}22; color:${badgeColor}; border:1px solid ${badgeColor}; margin-bottom:0.35rem; display:inline-block;">
                    ${_escInv(inv.document_type)} • ${_escInv(tax.tax_regime || "GST")}
                </span>
                <h4 style="margin:0.15rem 0;">${_escInv(seller.legal_name)}</h4>
                <small class="text-muted">${_escInv(seller.tax_id_label)}: <code>${_escInv(seller.tax_id)}</code> | ${_escInv(seller.state)}</small>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.05rem;"><strong>Invoice #${_escInv(inv.invoice_no)}</strong></div>
                <small class="text-muted">${_escInv(inv.invoice_date)}</small>
                ${inv.irn_reference ? `<div style="font-size:0.72rem;color:var(--text-muted);margin-top:0.2rem;">IRN: <code>${_escInv(inv.irn_reference.slice(0, 22))}…</code></div>` : ""}
            </div>
        </div>

        <div class="invoice-parties-grid">
            <div class="invoice-party-box">
                <strong>Buyer / Recipient</strong><br>
                Account: #${_escInv(buyer.customer_id)} (${_escInv(buyer.country)})<br>
                Buyer ID: <code>${_escInv(buyer.buyer_tax_id)}</code><br>
                Place of Supply: <strong>${_escInv(buyer.place_of_supply)}</strong>
            </div>
            <div class="invoice-party-box">
                <strong>Statutory Supply Classification</strong><br>
                Type: <code>${_escInv(tax.gst_supply_type)}</code><br>
                Rule: ${_escInv(tax.jurisdiction)}<br>
                Effective Tax Rate: <strong>${Number(tax.effective_rate_pct || 0).toFixed(2)}%</strong>
            </div>
        </div>

        <div tabindex="0" role="region" aria-labelledby="taxInvoiceTableCaption" class="invoice-table-wrapper">
            <table class="data-table">
                <caption id="taxInvoiceTableCaption" class="survival-caption">Itemized HSN &amp; GST / VAT Tax Breakdown for Invoice #${_escInv(inv.invoice_no)}</caption>
                <thead>
                    <tr>
                        <th scope="col">SKU</th>
                        <th scope="col">HSN</th>
                        <th scope="col">Description</th>
                        <th scope="col">Qty</th>
                        <th scope="col">Rate</th>
                        <th scope="col">Taxable</th>
                        <th scope="col">CGST</th>
                        <th scope="col">SGST</th>
                        <th scope="col">IGST</th>
                        <th scope="col">Gross Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        </div>

        <div class="invoice-totals-panel">
            <div style="display:flex; justify-content:space-between; font-size:0.86rem; margin-bottom:0.35rem;">
                <span>Taxable Value (Net)</span>
                <strong>${sym}${Number(totals.subtotal_net || 0).toFixed(2)}</strong>
            </div>
            ${compRows}
            <div style="display:flex; justify-content:space-between; font-size:1.05rem; margin-top:0.5rem; padding-top:0.5rem; border-top:1px solid var(--border-color);">
                <strong>Grand Total (${_escInv(totals.currency)})</strong>
                <strong style="color:${badgeColor};">${sym}${Number(totals.grand_total || 0).toFixed(2)}</strong>
            </div>
        </div>
    `;
}

async function fetchActiveTaxInvoice() {
    const invInput = document.getElementById("taxInvoiceLookupInput");
    const regimeSel = document.getElementById("taxRegimeSelect");
    const supplySel = document.getElementById("taxSupplyStateSelect");
    const buyerIdInput = document.getElementById("taxBuyerIdInput");
    const previewBox = document.getElementById("taxInvoicePreviewBox");
    if (!invInput || !previewBox) return;

    const invNo = String(invInput.value || "536365").trim() || "536365";
    const regime = regimeSel ? regimeSel.value : "GST";
    const supply = supplySel ? supplySel.value : "Karnataka";
    const buyerId = buyerIdInput ? String(buyerIdInput.value || "").trim() : "";

    const url = nexusApiUrl(`/api/v1/invoices/${encodeURIComponent(invNo)}?tax_regime=${encodeURIComponent(regime)}&supply_state=${encodeURIComponent(supply)}&buyer_tax_id=${encodeURIComponent(buyerId)}`);
    try {
        const res = await fetch(url);
        if (!res.ok) {
            previewBox.innerHTML = `<div class="btyd-stat-box"><strong>Invoice Not Found</strong><small>No record found for #${_escInv(invNo)}. Try 536365, C536379, or click Issue from POS Form.</small></div>`;
            return;
        }
        const data = await res.json();
        renderTaxInvoicePreview(data);
    } catch (_e) {
        previewBox.innerHTML = `<div class="btyd-stat-box"><strong>Invoice Engine Offline</strong><small>Connect FastAPI (:8000) to generate statutory GST &amp; VAT invoices.</small></div>`;
    }
}

async function issueTaxInvoiceFromPosForm() {
    const custId = document.getElementById("simCustId")?.value || "12352";
    const skuSel = document.getElementById("simSkuCode");
    const skuCode = skuSel?.value || "22423";
    const skuDesc = skuSel?.options?.[skuSel.selectedIndex]?.text?.replace(/^\[[^\]]+\]\s*/, "").replace(/\s*\([^)]+\)$/, "") || "REGENCY CAKESTAND 3 TIER";
    const qty = Number(document.getElementById("simQty")?.value || 12);
    const unitPrice = Number(document.getElementById("simPrice")?.value || 10.95);
    const country = document.getElementById("simCountry")?.value || "India";
    const regime = document.getElementById("taxRegimeSelect")?.value || "GST";
    const supply = document.getElementById("taxSupplyStateSelect")?.value || "Karnataka";
    const buyerId = document.getElementById("taxBuyerIdInput")?.value || "";

    try {
        const res = await fetch(nexusApiUrl("/api/v1/invoices/generate"), {
            method: "POST",
            headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({
                customer_id: custId,
                country,
                tax_regime: regime,
                buyer_tax_id: buyerId || null,
                supply_state: supply,
                items: [{
                    stock_code: skuCode,
                    description: skuDesc.toUpperCase(),
                    quantity: qty,
                    unit_price: unitPrice
                }]
            })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast("Invoice Issuance Blocked", err.detail || `HTTP ${res.status}`, "alert");
            return;
        }
        const data = await res.json();
        const invInput = document.getElementById("taxInvoiceLookupInput");
        if (invInput) invInput.value = data.invoice_no;
        renderTaxInvoicePreview(data);
        showToast("Tax Invoice Issued", `Generated ${data.document_type} #${data.invoice_no}`, "success");
        logAuditEvent("Tax Invoice", `Issued ${data.document_type} #${data.invoice_no} (${data.tax_summary?.gst_supply_type})`);
    } catch (_e) {
        showToast("Backend Offline", "Connect FastAPI (:8000) to generate POS tax invoices.", "alert");
    }
}

window.loadTaxInvoicePreset = function(invNo, regime, supplyState) {
    const invInput = document.getElementById("taxInvoiceLookupInput");
    const regimeSel = document.getElementById("taxRegimeSelect");
    const supplySel = document.getElementById("taxSupplyStateSelect");
    if (invInput) invInput.value = invNo;
    if (regimeSel) regimeSel.value = regime;
    if (supplySel) supplySel.value = supplyState;
    fetchActiveTaxInvoice();
};

export function initTaxInvoiceStudio() {
    fetchActiveTaxInvoice();
    if (TAX_INVOICE_WIRED) return;
    TAX_INVOICE_WIRED = true;

    const lookupBtn = document.getElementById("taxInvoiceLookupBtn");
    const issueBtn = document.getElementById("taxIssueFromPosBtn");
    const regimeSel = document.getElementById("taxRegimeSelect");
    const supplySel = document.getElementById("taxSupplyStateSelect");
    const printBtn = document.getElementById("taxPrintInvoiceBtn");
    const jsonBtn = document.getElementById("taxDownloadJsonBtn");

    if (lookupBtn) lookupBtn.addEventListener("click", fetchActiveTaxInvoice);
    if (issueBtn) issueBtn.addEventListener("click", issueTaxInvoiceFromPosForm);
    if (regimeSel) regimeSel.addEventListener("change", fetchActiveTaxInvoice);
    if (supplySel) supplySel.addEventListener("change", fetchActiveTaxInvoice);

    if (printBtn) {
        printBtn.addEventListener("click", () => {
            const invNo = ACTIVE_TAX_INVOICE_CACHE?.invoice_no || document.getElementById("taxInvoiceLookupInput")?.value || "536365";
            const regime = document.getElementById("taxRegimeSelect")?.value || "GST";
            const supply = document.getElementById("taxSupplyStateSelect")?.value || "Karnataka";
            const buyerId = document.getElementById("taxBuyerIdInput")?.value || "";
            const url = nexusApiUrl(`/api/v1/invoices/${encodeURIComponent(invNo)}/html?tax_regime=${encodeURIComponent(regime)}&supply_state=${encodeURIComponent(supply)}&buyer_tax_id=${encodeURIComponent(buyerId)}`);
            window.open(url, "_blank", "noopener,noreferrer");
        });
    }

    if (jsonBtn) {
        jsonBtn.addEventListener("click", () => {
            if (!ACTIVE_TAX_INVOICE_CACHE) return;
            const blob = new Blob([JSON.stringify(ACTIVE_TAX_INVOICE_CACHE, null, 2)], { type: "application/json" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `tax_invoice_${ACTIVE_TAX_INVOICE_CACHE.invoice_no}.json`;
            a.click();
            URL.revokeObjectURL(a.href);
            showToast("JSON Exported", `Downloaded tax_invoice_${ACTIVE_TAX_INVOICE_CACHE.invoice_no}.json`, "success");
        });
    }
}
