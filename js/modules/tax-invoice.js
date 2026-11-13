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
    const isGst = (tax.tax_regime || "GST") === "GST";
    const eway = inv.eway_bill || {};
    const isEwayReq = Boolean(eway.required || (isGst && !isCn && totals.grand_total >= (eway.threshold_inr || 50000)));

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

    const itemOptions = (inv.items || []).map((it, idx) => `
        <option value="${idx}">[${_escInv(it.stock_code)}] ${_escInv(it.description)} (Qty: ${Math.abs(it.quantity)}, Rate: ${sym}${Number(it.unit_price).toFixed(2)})</option>
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

        ${isCn ? `
            <div style="margin-bottom:1rem; padding:0.65rem 0.9rem; background:rgba(239, 68, 68, 0.08); border:1px solid #EF4444; border-radius:6px; font-size:0.84rem;">
                <strong>↩️ Statutory GST Credit Note (GSTR-1 Table 9B CDNR Reversal)</strong><br>
                <span>Original Invoice Reference: <strong>#${_escInv(inv.original_invoice_reference || inv.original_invoice_no || "N/A")}</strong></span> &bull; 
                <span>Reason: <em>${_escInv(inv.credit_note_reason || "Damaged Goods / Quality Reject")}</em></span>
            </div>
        ` : ""}

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

        <!-- Dynamic Vector UPI QR Code Section -->
        ${inv.upi_payment?.qr_svg ? `
            <div class="upi-payment-panel" style="display:flex; align-items:center; gap:1.25rem; background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:0.85rem 1.1rem; margin-top:1.25rem;">
                <div style="background:#FFFFFF; padding:6px; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,0.12); flex-shrink:0;">
                    ${inv.upi_payment.qr_svg}
                </div>
                <div style="flex:1;">
                    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.25rem;">
                        <strong style="font-size:0.95rem; color:var(--text-primary);">⚡ Scan &amp; Pay via UPI</strong>
                        <span class="badge-tag" style="background:#10B98122; color:#10B981; border:1px solid #10B981; font-size:0.7rem;">NPCI Dynamic QR</span>
                    </div>
                    <p style="font-size:0.78rem; color:var(--text-secondary); margin:0 0 0.4rem 0;">
                        Scan with Google Pay, PhonePe, Paytm, BHIM, or any UPI banking app for instant auto-reconciled settlement.
                    </p>
                    <div style="font-size:0.78rem; color:var(--text-secondary); margin-bottom:0.5rem;">
                        VPA: <code>${_escInv(inv.upi_payment.merchant_vpa || "nexus.retail@icici")}</code> &bull; Pay: <strong>${sym}${Number(totals.grand_total || 0).toFixed(2)}</strong>
                    </div>
                    <div style="display:flex; gap:0.5rem;">
                        <button type="button" class="btn btn-outline btn-xs" id="btnCopyUpiLink">📋 Copy UPI Link</button>
                        <a href="${_escInv(inv.upi_payment.intent_uri || '#')}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-xs">🚀 Open UPI App</a>
                    </div>
                </div>
            </div>
        ` : ""}

        <!-- Statutory E-Way Bill Section -->
        <div class="eway-bill-banner" style="margin-top:1rem; padding:0.85rem 1rem; border-radius:8px; border:1px solid ${isEwayReq ? '#059669' : 'var(--border-color)'}; background:${isEwayReq ? 'rgba(5, 150, 105, 0.08)' : 'var(--bg-secondary)'}; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.75rem;">
            <div>
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <strong>${isEwayReq ? '🚚 Statutory E-Way Bill (EWB-01) Mandatory' : '🚚 E-Way Bill Consignment Status'}</strong>
                    <span class="badge-tag" style="background:${isEwayReq ? '#059669' : '#64748B'}22; color:${isEwayReq ? '#059669' : '#64748B'}; border:1px solid ${isEwayReq ? '#059669' : '#64748B'}; font-size:0.7rem;">
                        ${isEwayReq ? 'Mandatory (>= ₹50,000)' : 'Optional (< ₹50,000)'}
                    </span>
                </div>
                <p style="font-size:0.78rem; color:var(--text-secondary); margin:0.25rem 0 0 0;">
                    ${isEwayReq 
                        ? 'Consignment value ₹' + Number(totals.grand_total || 0).toLocaleString('en-IN') + ' exceeds statutory Rule 138 CGST threshold (₹50,000). Goods in transit require Form EWB-01 verification slip.'
                        : 'Consignment value ₹' + Number(totals.grand_total || 0).toLocaleString('en-IN') + ' is below statutory threshold (₹50,000). Optional E-Way Bill can be issued for inter-state tracking.'}
                </p>
            </div>
            <div style="display:flex; gap:0.5rem;">
                <button type="button" class="btn ${isEwayReq ? 'btn-primary' : 'btn-secondary'} btn-sm" id="btnViewEwayBillSlip">
                    🚚 View &amp; Print EWB-01 Slip
                </button>
            </div>
        </div>

        <!-- POS Credit Note Lifecycle Action -->
        ${!isCn ? `
            <div style="margin-top:1rem; display:flex; justify-content:flex-end;">
                <button type="button" class="btn btn-outline btn-sm" id="btnToggleCreditNoteDrawer">
                    🔄 Issue Credit Note for this Invoice (Rule 53)
                </button>
            </div>

            <div id="creditNoteDrawer" style="display:none; margin-top:0.75rem; padding:1rem; border:1px dashed var(--accent-red, #EF4444); border-radius:8px; background:rgba(239,68,68,0.03);">
                <h5 style="margin:0 0 0.5rem 0; color:#DC2626;">Issue Statutory Credit Note (CDNR Table 9B)</h5>
                <p style="font-size:0.78rem; color:var(--text-secondary); margin-bottom:0.75rem;">
                    Reverses taxable turnover and output GST liability under CGST Rule 53. Reconciles directly into GSTR-1 Table 9B.
                </p>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:0.65rem; margin-bottom:0.75rem;">
                    <div>
                        <label style="font-size:0.75rem; color:var(--text-secondary);">Select Item to Return:</label>
                        <select id="cnItemSelect" class="form-input-sm" style="width:100%;">
                            ${itemOptions}
                        </select>
                    </div>
                    <div>
                        <label style="font-size:0.75rem; color:var(--text-secondary);">Return Quantity:</label>
                        <input type="number" id="cnQtyInput" class="form-input-sm" value="1" min="1" max="999" style="width:100%;">
                    </div>
                    <div>
                        <label style="font-size:0.75rem; color:var(--text-secondary);">Statutory Reason:</label>
                        <select id="cnReasonSelect" class="form-input-sm" style="width:100%;">
                            <option value="Damaged Goods / Quality Reject" selected>Damaged Goods / Quality Reject</option>
                            <option value="Post-Sale Volume Discount / Rebate">Post-Sale Volume Discount / Rebate</option>
                            <option value="Deficiency in Service / Transit Loss">Deficiency in Service / Transit Loss</option>
                            <option value="Correction in Invoice Value">Correction in Invoice Value</option>
                        </select>
                    </div>
                </div>
                <div style="display:flex; justify-content:flex-end; gap:0.5rem;">
                    <button type="button" class="btn btn-outline btn-xs" id="btnCancelCreditNote">Cancel</button>
                    <button type="button" class="btn btn-danger btn-xs" id="btnConfirmCreditNote">⚡ Confirm &amp; Issue Credit Note</button>
                </div>
            </div>
        ` : ""}
    `;

    // Bind dynamic QR code actions
    const copyBtn = document.getElementById("btnCopyUpiLink");
    if (copyBtn && inv.upi_payment?.intent_uri) {
        copyBtn.addEventListener("click", () => {
            navigator.clipboard?.writeText(inv.upi_payment.intent_uri).then(() => {
                showToast("UPI Link Copied", "Pasted payment URI to clipboard", "success");
            }).catch(() => {
                showToast("UPI URI", inv.upi_payment.intent_uri, "info");
            });
        });
    }

    // Bind E-Way bill button
    const ewbBtn = document.getElementById("btnViewEwayBillSlip");
    if (ewbBtn) {
        ewbBtn.addEventListener("click", () => {
            const supply = document.getElementById("taxSupplyStateSelect")?.value || "Karnataka";
            const url = nexusApiUrl(`/api/v1/invoices/${encodeURIComponent(inv.invoice_no)}/eway-bill/html?force=true&supply_state=${encodeURIComponent(supply)}`);
            window.open(url, "_blank", "noopener,noreferrer");
        });
    }

    // Bind Credit Note drawer actions
    const toggleCnBtn = document.getElementById("btnToggleCreditNoteDrawer");
    const drawer = document.getElementById("creditNoteDrawer");
    const cancelCnBtn = document.getElementById("btnCancelCreditNote");
    const confirmCnBtn = document.getElementById("btnConfirmCreditNote");

    if (toggleCnBtn && drawer) {
        toggleCnBtn.addEventListener("click", () => {
            drawer.style.display = drawer.style.display === "none" ? "block" : "none";
        });
    }
    if (cancelCnBtn && drawer) {
        cancelCnBtn.addEventListener("click", () => {
            drawer.style.display = "none";
        });
    }
    if (confirmCnBtn) {
        confirmCnBtn.addEventListener("click", async () => {
            const itemIdx = Number(document.getElementById("cnItemSelect")?.value || 0);
            const returnQty = Number(document.getElementById("cnQtyInput")?.value || 1);
            const reason = document.getElementById("cnReasonSelect")?.value || "Damaged Goods / Quality Reject";
            const item = (inv.items || [])[itemIdx];
            if (!item) {
                showToast("No Item Selected", "Please select an item to issue credit note for.", "alert");
                return;
            }

            confirmCnBtn.disabled = true;
            confirmCnBtn.textContent = "Issuing…";
            try {
                const supply = document.getElementById("taxSupplyStateSelect")?.value || "Karnataka";
                const res = await fetch(nexusApiUrl("/api/v1/invoices/credit-note"), {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify({
                        original_invoice_no: inv.invoice_no,
                        reason: reason,
                        customer_id: inv.buyer?.customer_id,
                        supply_state: supply,
                        items: [{
                            stock_code: item.stock_code,
                            description: item.description,
                            quantity: returnQty,
                            unit_price: item.unit_price,
                        }],
                    }),
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    showToast("Credit Note Failed", err.detail || `HTTP ${res.status}`, "alert");
                    confirmCnBtn.disabled = false;
                    confirmCnBtn.textContent = "⚡ Confirm & Issue Credit Note";
                    return;
                }

                const cnData = await res.json();
                const invInput = document.getElementById("taxInvoiceLookupInput");
                if (invInput) invInput.value = cnData.invoice_no;

                renderTaxInvoicePreview(cnData);
                refreshGstr1ReturnPanel();
                showToast("Credit Note Issued", `Generated #${cnData.invoice_no} linked to #${inv.invoice_no}`, "success");
                logAuditEvent("Credit Note", `Issued ${cnData.invoice_no} against original invoice ${inv.invoice_no}`);
            } catch (err) {
                showToast("Network Error", "Could not issue credit note.", "alert");
                confirmCnBtn.disabled = false;
                confirmCnBtn.textContent = "⚡ Confirm & Issue Credit Note";
            }
        });
    }
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

let ACTIVE_GSTR1_CACHE = null;

function _fmtInr(v) {
    return "₹" + Number(v || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function refreshGstr1ReturnPanel() {
    const periodSel = document.getElementById("gstr1PeriodSelect");
    const modeSel = document.getElementById("gstr1SupplyModeSelect");
    const tbody = document.getElementById("gstr1HsnTbody");
    const ribbon = document.getElementById("gstr1SectionsRibbon");
    if (!periodSel || !tbody) return;

    const period = periodSel.value || "All";
    const mode = modeSel ? modeSel.value : "MIXED";

    try {
        const res = await fetch(nexusApiUrl(`/api/v1/invoices/gstr1-return?period=${encodeURIComponent(period)}&supply_mode=${encodeURIComponent(mode)}`));
        if (!res.ok) return;
        const data = await res.json();
        ACTIVE_GSTR1_CACHE = data;

        // Hydrate period options once dynamically
        if (periodSel.options.length <= 1 && Array.isArray(data.available_periods)) {
            periodSel.innerHTML = data.available_periods
                .map(p => `<option value="${_escInv(p)}" ${p === data.selected_period ? "selected" : ""}>${p === "All" ? "All Periods (Full Ledger)" : _escInv(p)}</option>`)
                .join("");
        }

        const sum = data.summary || {};
        const elNet = document.getElementById("gstr1NetTaxableVal");
        const elGross = document.getElementById("gstr1GrossGstVal");
        const elCdnr = document.getElementById("gstr1CdnrOffsetVal");
        const elPay = document.getElementById("gstr1NetPayableVal");
        if (elNet) elNet.textContent = _fmtInr(sum.net_taxable_turnover_inr);
        if (elGross) elGross.textContent = _fmtInr(sum.gross_outward_gst_inr);
        if (elCdnr) elCdnr.textContent = `-${_fmtInr(sum.cdnr_gst_offset_inr)}`;
        if (elPay) elPay.textContent = _fmtInr(sum.net_gst_payable_inr);

        if (ribbon && Array.isArray(data.sections)) {
            ribbon.innerHTML = data.sections.map(sec => `
                <div class="btyd-stat-box" style="flex:1; min-width:190px;">
                    <strong>${_escInv(sec.table)}</strong>
                    <div class="stat-val" style="font-size:1.05rem;">${_fmtInr(sec.gst_inr)} GST</div>
                    <small style="color:var(--text-muted);">Taxable: ${_fmtInr(sec.taxable_inr)} &bull; ${_escInv(sec.notes)}</small>
                </div>
            `).join("");
        }

        const hsnRows = data.hsn_summary || [];
        tbody.innerHTML = hsnRows.map(row => `
            <tr>
                <th scope="row">${_escInv(row.hsn_code)}</th>
                <td data-label="GST Slab">${Number(row.gst_rate_pct).toFixed(0)}%</td>
                <td data-label="SKU Lines">${Number(row.sku_lines).toLocaleString("en-IN")}</td>
                <td data-label="Net Qty">${Number(row.total_qty).toLocaleString("en-IN")}</td>
                <td data-label="Taxable (₹)">${_fmtInr(row.taxable_value_inr)}</td>
                <td data-label="CGST (₹)">${_fmtInr(row.cgst_inr)}</td>
                <td data-label="SGST (₹)">${_fmtInr(row.sgst_inr)}</td>
                <td data-label="IGST (₹)">${_fmtInr(row.igst_inr)}</td>
                <td data-label="Total Tax (₹)"><strong>${_fmtInr(row.total_tax_inr)}</strong></td>
            </tr>
        `).join("");
    } catch (_e) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--text-muted);">Connect FastAPI backend to aggregate GSTR-1 return tables.</td></tr>`;
        }
    }
}

export function initTaxInvoiceStudio() {
    fetchActiveTaxInvoice();
    refreshGstr1ReturnPanel();
    if (TAX_INVOICE_WIRED) return;
    TAX_INVOICE_WIRED = true;

    const lookupBtn = document.getElementById("taxInvoiceLookupBtn");
    const issueBtn = document.getElementById("taxIssueFromPosBtn");
    const regimeSel = document.getElementById("taxRegimeSelect");
    const supplySel = document.getElementById("taxSupplyStateSelect");
    const printBtn = document.getElementById("taxPrintInvoiceBtn");
    const jsonBtn = document.getElementById("taxDownloadJsonBtn");

    if (lookupBtn) lookupBtn.addEventListener("click", fetchActiveTaxInvoice);
    if (issueBtn) {
        issueBtn.addEventListener("click", async () => {
            await issueTaxInvoiceFromPosForm();
            refreshGstr1ReturnPanel();
        });
    }
    if (regimeSel) regimeSel.addEventListener("change", fetchActiveTaxInvoice);
    if (supplySel) supplySel.addEventListener("change", fetchActiveTaxInvoice);

    const gstrPeriod = document.getElementById("gstr1PeriodSelect");
    const gstrMode = document.getElementById("gstr1SupplyModeSelect");
    const gstrRefreshBtn = document.getElementById("btnRefreshGstr1");
    const gstrJsonBtn = document.getElementById("btnDownloadGstr1Json");
    const gstrCsvBtn = document.getElementById("btnExportGstr1HsnCsv");

    if (gstrPeriod) gstrPeriod.addEventListener("change", refreshGstr1ReturnPanel);
    if (gstrMode) gstrMode.addEventListener("change", refreshGstr1ReturnPanel);
    if (gstrRefreshBtn) gstrRefreshBtn.addEventListener("click", refreshGstr1ReturnPanel);

    if (gstrJsonBtn) {
        gstrJsonBtn.addEventListener("click", () => {
            if (!ACTIVE_GSTR1_CACHE?.gstr1_json_payload) return;
            const blob = new Blob([JSON.stringify(ACTIVE_GSTR1_CACHE.gstr1_json_payload, null, 2)], { type: "application/json" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `gstr1_return_${ACTIVE_GSTR1_CACHE.selected_period || "all"}.json`;
            a.click();
            URL.revokeObjectURL(a.href);
            showToast("GSTR-1 JSON Exported", "Official GSTR-1 return filing JSON downloaded", "success");
            logAuditEvent("Tax Compliance", `Exported GSTR-1 JSON (${ACTIVE_GSTR1_CACHE.selected_period})`);
        });
    }

    if (gstrCsvBtn) {
        gstrCsvBtn.addEventListener("click", () => {
            if (!ACTIVE_GSTR1_CACHE?.hsn_summary?.length) return;
            downloadCSV(`gstr1_hsn_summary_${ACTIVE_GSTR1_CACHE.selected_period || "all"}.csv`, ACTIVE_GSTR1_CACHE.hsn_summary);
            showToast("HSN Table 12 Exported", "gstr1_hsn_summary CSV downloaded", "success");
        });
    }

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
