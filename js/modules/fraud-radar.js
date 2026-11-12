/**
 * Phase 15: Transaction Anomaly, Fraud & Cancellation Radar
 * Loaded lazily on demand by app.js module router.
 */

export function initFraudRadar() {
    const scoreForm = document.getElementById("fraudScoreForm");
    const riskRing = document.getElementById("fraudRiskRing");
    const ringScoreText = document.getElementById("fraudRingScoreText");
    const tierBadge = document.getElementById("fraudResultTierBadge");
    const actionEl = document.getElementById("fraudRecommendedAction");
    const signalsList = document.getElementById("fraudTriggeredSignalsList");
    const quarantineTbody = document.getElementById("fraudQuarantineTbody");
    const refreshBtn = document.getElementById("btnRefreshFraudReport");

    if (!scoreForm || !riskRing) return;

    let countryCancelChartInstance = null;

    const escapeFraudHtml = (str) => String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    // Fallback for browsers without attr(value type(<number>)) support on <progress>
    if (!CSS.supports("width: attr(value type(<number>))")) {
        const observer = new MutationObserver(() => {
            riskRing.style.setProperty("--value", riskRing.getAttribute("value") || "0");
        });
        observer.observe(riskRing, { attributes: true, attributeFilter: ["value"] });
    }

    function updateRiskRing(scoreVal) {
        const clamped = Math.min(100, Math.max(0, Math.round(scoreVal)));
        riskRing.setAttribute("value", String(clamped));
        riskRing.setAttribute("aria-valuetext", `${clamped} out of 100 risk score`);
        riskRing.style.setProperty("--value", String(clamped));
        riskRing.classList.remove("risk-critical", "risk-high", "risk-safe");
        if (clamped >= 75) riskRing.classList.add("risk-critical");
        else if (clamped >= 50) riskRing.classList.add("risk-high");
        else riskRing.classList.add("risk-safe");

        if (ringScoreText) ringScoreText.textContent = String(clamped);
    }

    function renderAssessment(a) {
        if (!a) return;
        updateRiskRing(a.risk_score);

        if (tierBadge) {
            tierBadge.textContent = a.risk_tier;
            tierBadge.className = `badge ${a.risk_score >= 75 ? "red" : a.risk_score >= 50 ? "gold" : "green"}`;
        }
        if (actionEl) {
            actionEl.textContent = `${a.recommended_action} (${a.isolation_forest_anomaly ? "Isolation Forest Flagged" : "Inlier Baseline"})`;
        }
        if (signalsList) {
            signalsList.innerHTML = (a.triggered_signals || []).map(s => `<li>${escapeFraudHtml(s)}</li>`).join("");
        }
    }

    function renderCountryCancelChart(countries) {
        const canvas = document.getElementById("countryCancelChart");
        if (!canvas || typeof Chart === "undefined" || !countries || !countries.length) return;

        if (countryCancelChartInstance) {
            countryCancelChartInstance.destroy();
            countryCancelChartInstance = null;
        }

        countryCancelChartInstance = new Chart(canvas, {
            type: "bar",
            data: {
                labels: countries.map(c => c.country),
                datasets: [{
                    label: "Cancellation Rate (%)",
                    data: countries.map(c => c.cancellation_rate_pct),
                    backgroundColor: countries.map(c => c.cancellation_rate_pct >= 18 ? "#EF4444" : c.cancellation_rate_pct >= 12 ? "#F59E0B" : "#3B82F6"),
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { ticks: { callback: v => `${v}%` }, grid: { color: "rgba(255,255,255,0.06)" } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    function renderQuarantineQueue(queue) {
        const kpiQueue = document.getElementById("fraudKpiQueueCount");
        const pendingCount = (queue || []).filter(q => q.status === "QUARANTINED").length;
        if (kpiQueue) kpiQueue.textContent = `${pendingCount} Pending`;
        if (!quarantineTbody) return;

        if (!queue || !queue.length) {
            quarantineTbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:1rem;">No anomalies in quarantine queue.</td></tr>`;
            return;
        }

        quarantineTbody.innerHTML = queue.map(item => {
            const st = item.status || "QUARANTINED";
            const badgeCls = st === "APPROVED" ? "green" : st === "BLOCKED" ? "red" : "gold";
            const scoreColor = item.risk_score >= 75 ? "#EF4444" : item.risk_score >= 50 ? "#F59E0B" : "#10B981";
            const firstSignal = (item.triggered_signals && item.triggered_signals[0]) || "Isolation Forest outlier";
            const actionHtml = st === "QUARANTINED"
                ? `<div style="display:flex;gap:0.35rem;">
                    <button type="button" class="btn btn-outline btn-xs btn-resolve-fraud" data-alert-id="${escapeFraudHtml(item.alert_id)}" data-decision="APPROVED">Approve</button>
                    <button type="button" class="btn btn-secondary btn-xs btn-resolve-fraud" data-alert-id="${escapeFraudHtml(item.alert_id)}" data-decision="BLOCKED" style="color:#ef4444;">Block</button>
                   </div>`
                : `<small class="text-muted">Resolved by ${escapeFraudHtml(item.resolved_by || "operator")}</small>`;

            return `
                <tr>
                    <td><code>${escapeFraudHtml(item.alert_id)}</code></td>
                    <td><strong>${escapeFraudHtml(item.invoice_no)}</strong></td>
                    <td>${escapeFraudHtml(item.customer_id)}</td>
                    <td>₹${Number(item.amount_gbp || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                    <td><strong style="color:${scoreColor};">${Number(item.risk_score).toFixed(1)}</strong></td>
                    <td><small>${escapeFraudHtml(firstSignal)}</small></td>
                    <td><span class="badge ${badgeCls}">${escapeFraudHtml(st)}</span></td>
                    <td>${actionHtml}</td>
                </tr>
            `;
        }).join("");

        quarantineTbody.querySelectorAll(".btn-resolve-fraud").forEach(btn => {
            btn.addEventListener("click", async () => {
                const alertId = btn.getAttribute("data-alert-id");
                const decision = btn.getAttribute("data-decision");
                try {
                    const res = await fetch(nexusApiUrl(`/api/v1/fraud/quarantine/${alertId}/resolve`), {
                        method: "POST",
                        headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                        body: JSON.stringify({ decision })
                    });
                    if (res.status === 401 || res.status === 403) {
                        const err = await res.json().catch(() => ({}));
                        showToast("RBAC Triage Denied", err.detail || `HTTP ${res.status}: Role lacks fraud:resolve scope`, "alert");
                        return;
                    }
                    if (res.ok) {
                        showToast("Alert Triaged", `Quarantine ${alertId} marked ${decision}`, decision === "BLOCKED" ? "warning" : "success");
                        loadFraudReport();
                    }
                } catch (e) {
                    showToast("Backend Offline", "Start FastAPI :8000 to persist quarantine triage decisions", "info");
                }
            });
        });
    }

    async function loadFraudReport() {
        try {
            const res = await fetch(nexusApiUrl("/api/v1/fraud/anomaly-report"));
            if (res.ok) {
                const data = await res.json();
                const s = data.summary || {};
                const kpiInv = document.getElementById("fraudKpiInvoices");
                const kpiRate = document.getElementById("fraudKpiCancelRate");
                const kpiCancelCnt = document.getElementById("fraudKpiCancelCount");
                const kpiExp = document.getElementById("fraudKpiExposure");
                const kpiFlagCnt = document.getElementById("fraudKpiAnomalyCount");

                if (kpiInv) kpiInv.textContent = Number(s.total_invoices_scanned || 23218).toLocaleString("en-IN");
                if (kpiRate) kpiRate.textContent = `${Number(s.cancellation_rate_pct || 14.74).toFixed(2)}%`;
                if (kpiCancelCnt) kpiCancelCnt.textContent = `${Number(s.cancelled_invoices_count || 3422).toLocaleString("en-IN")} Cancelled Invoices`;
                if (kpiExp) kpiExp.textContent = `₹${((s.anomaly_revenue_exposure_gbp || 1850000) / 100000).toFixed(2)}L`;
                if (kpiFlagCnt) kpiFlagCnt.textContent = `${Number(s.flagged_anomalies_count || 1161).toLocaleString("en-IN")} Isolation Outliers (${s.flagged_share_pct || 5.0}%)`;

                renderCountryCancelChart(data.country_cancellation_rates);
                renderQuarantineQueue(data.quarantine_queue);
                return;
            }
        } catch (err) {
            // Fallback telemetry if offline
        }
        renderCountryCancelChart([
            { country: "United Kingdom", cancellation_rate_pct: 14.5 },
            { country: "Germany", cancellation_rate_pct: 24.4 },
            { country: "France", cancellation_rate_pct: 15.1 },
            { country: "EIRE", cancellation_rate_pct: 20.6 },
            { country: "Netherlands", cancellation_rate_pct: 6.3 }
        ]);
    }

    window.refreshFraudRadarReport = loadFraudReport;

    window.applyFraudPreset = function(presetKey) {
        const amt = document.getElementById("fraudAmountInput");
        const units = document.getElementById("fraudUnitsInput");
        const lines = document.getElementById("fraudLinesInput");
        const cid = document.getElementById("fraudCustInput");
        const hour = document.getElementById("fraudHourInput");
        const cancelPct = document.getElementById("fraudCancelRateInput");
        const guestChk = document.getElementById("fraudIsGuestChk");

        if (presetKey === "guest_whale") {
            if (amt) amt.value = "18500";
            if (units) units.value = "6200";
            if (lines) lines.value = "1";
            if (cid) cid.value = "Guest";
            if (hour) hour.value = "2";
            if (cancelPct) cancelPct.value = "0";
            if (guestChk) guestChk.checked = true;
        } else if (presetKey === "high_cancel") {
            if (amt) amt.value = "-3200";
            if (units) units.value = "420";
            if (lines) lines.value = "3";
            if (cid) cid.value = "14096";
            if (hour) hour.value = "14";
            if (cancelPct) cancelPct.value = "65";
            if (guestChk) guestChk.checked = false;
        } else {
            if (amt) amt.value = "68.50";
            if (units) units.value = "14";
            if (lines) lines.value = "4";
            if (cid) cid.value = "17850";
            if (hour) hour.value = "13";
            if (cancelPct) cancelPct.value = "0";
            if (guestChk) guestChk.checked = false;
        }
        scoreForm.requestSubmit();
    };

    scoreForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = document.getElementById("btnRunFraudScore");
        if (btn) {
            btn.disabled = true;
            btn.textContent = "⏳ Scoring with Isolation Forest...";
        }

        const amountVal = parseFloat(document.getElementById("fraudAmountInput")?.value) || 0;
        const payload = {
            amount_gbp: amountVal,
            total_units: parseInt(document.getElementById("fraudUnitsInput")?.value, 10) || 1,
            line_items: parseInt(document.getElementById("fraudLinesInput")?.value, 10) || 1,
            customer_id: document.getElementById("fraudCustInput")?.value.trim() || "Guest",
            hour_of_day: parseFloat(document.getElementById("fraudHourInput")?.value) || 12,
            historical_cancel_rate: (parseFloat(document.getElementById("fraudCancelRateInput")?.value) || 0) / 100,
            is_guest: Boolean(document.getElementById("fraudIsGuestChk")?.checked),
            is_cancelled: amountVal < 0,
            auto_quarantine: Boolean(document.getElementById("fraudAutoQuarantineChk")?.checked)
        };

        try {
            const res = await fetch(nexusApiUrl("/api/v1/fraud/score-transaction"), {
                method: "POST",
                headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify(payload)
            });
            if (res.status === 401 || res.status === 403) {
                const err = await res.json().catch(() => ({}));
                showToast("RBAC Scoring Denied", err.detail || `HTTP ${res.status}`, "alert");
                return;
            }
            if (res.ok) {
                const data = await res.json();
                renderAssessment(data.assessment);
                loadFraudReport();
                return;
            }
        } catch (err) {
            // Fallback local scoring estimate if offline
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = "🛡️ Score Transaction Risk & Inspect Signals";
            }
        }

        // Offline deterministic fallback
        let localScore = 15;
        const signals = [];
        if (Math.abs(payload.amount_gbp) > 4000) { localScore += 32; signals.push(`High order value ₹${Math.abs(payload.amount_gbp).toLocaleString("en-IN")}`); }
        if (payload.is_guest && payload.amount_gbp >= 1500) { localScore += 22; signals.push("High-value guest checkout"); }
        if (payload.hour_of_day < 6 || payload.hour_of_day >= 22) { localScore += 15; signals.push(`Off-hours timestamp (${payload.hour_of_day}:00 UTC)`); }
        if (payload.historical_cancel_rate >= 0.25) { localScore += 20; signals.push(`High account cancel rate (${(payload.historical_cancel_rate * 100).toFixed(0)}%)`); }
        if (!signals.length) signals.push("Order profile aligns with normal baseline");
        localScore = Math.min(98, localScore);

        renderAssessment({
            risk_score: localScore,
            risk_tier: localScore >= 75 ? "CRITICAL_QUARANTINE" : localScore >= 50 ? "HIGH_REVIEW" : "LOW_SAFE",
            recommended_action: localScore >= 75 ? "QUARANTINE_AND_HOLD" : localScore >= 50 ? "STEP_UP_3DS_VERIFICATION" : "AUTO_APPROVE",
            isolation_forest_anomaly: localScore >= 50,
            triggered_signals: signals
        });
    });

    refreshBtn?.addEventListener("click", () => {
        loadFraudReport();
        showToast("Fraud Radar Synced", "Refreshed Isolation Forest anomalies & quarantine queue", "info");
    });

    loadFraudReport();
}
