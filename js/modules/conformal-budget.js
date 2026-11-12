/**
 * Phase 30: Split-Conformal Demand Uncertainty (P10/P50/P90) & KKT Budget Optimizer
 * Loaded lazily on demand by app.js module router.
 */

let conformalBandChartInstance = null;
let budgetAllocChartInstance = null;
let CONFORMAL_WIRED = false;
let BUDGET_WIRED = false;

function _fmtInr(v, decimals = 0) {
    return "₹" + Number(v || 0).toLocaleString("en-IN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

function _esc(v) {
    return String(v ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

export async function refreshConformalIntervals() {
    const confSelect = document.getElementById("conformalConfidenceSelect");
    const covBadge = document.getElementById("conformalCoverageBadge");
    const canvas = document.getElementById("conformalBandChart");
    const varEl = document.getElementById("conformalVarBufferVal");
    const widthEl = document.getElementById("conformalWidthVal");
    const empEl = document.getElementById("conformalEmpiricalVal");
    if (!confSelect || !canvas) return;

    const conf = Number(confSelect.value || 80);
    try {
        const res = await fetch(nexusApiUrl(`/api/v1/forecast/conformal-intervals?confidence_pct=${encodeURIComponent(conf)}`));
        if (!res.ok) return;
        const data = await res.json();
        const s = data.summary || {};

        if (covBadge) {
            covBadge.textContent = `Calibrated ${s.empirical_eval_coverage_pct}% Eval Coverage (Target ${s.target_confidence_pct}%)`;
        }
        if (varEl) varEl.textContent = _fmtInr(s.downside_var_reserve_inr, 0);
        if (widthEl) widthEl.textContent = `±${_fmtInr((s.avg_interval_width_inr || 0) / 2, 0)}`;
        if (empEl) empEl.textContent = `${s.empirical_eval_coverage_pct}% (q=${s.conformal_multiplier_q})`;

        const series = (data.series || []).slice(-45);
        if (typeof Chart !== "undefined" && series.length) {
            if (conformalBandChartInstance) conformalBandChartInstance.destroy();
            const isLight = document.documentElement.getAttribute("data-theme") === "light";
            const textCol = isLight ? "#334155" : "#D4D4D8";
            const gridCol = isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";

            conformalBandChartInstance = new Chart(canvas.getContext("2d"), {
                type: "line",
                data: {
                    labels: series.map(d => d.date.slice(5)),
                    datasets: [
                        {
                            label: `${s.upper_percentile_label || "P90"} Conformal Upper`,
                            data: series.map(d => d.upper_inr),
                            borderColor: "rgba(59, 130, 246, 0.45)",
                            backgroundColor: "rgba(59, 130, 246, 0.14)",
                            borderDash: [4, 4],
                            borderWidth: 1.5,
                            fill: "+1",
                            pointRadius: 0,
                            tension: 0.25,
                        },
                        {
                            label: `${s.lower_percentile_label || "P10"} Conformal Lower`,
                            data: series.map(d => d.lower_inr),
                            borderColor: "rgba(245, 158, 11, 0.55)",
                            borderDash: [4, 4],
                            borderWidth: 1.5,
                            fill: false,
                            pointRadius: 0,
                            tension: 0.25,
                        },
                        {
                            label: "P50 Forecast",
                            data: series.map(d => d.point_p50_inr),
                            borderColor: "#3B82F6",
                            borderWidth: 2.2,
                            pointRadius: 0,
                            tension: 0.25,
                        },
                        {
                            label: "Actual Revenue (₹)",
                            data: series.map(d => d.actual_inr),
                            borderColor: "#10B981",
                            borderWidth: 1.8,
                            pointRadius: 2,
                            tension: 0.2,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: textCol, font: { size: 11 } } },
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.dataset.label}: ${_fmtInr(ctx.parsed.y, 0)}`,
                            },
                        },
                    },
                    scales: {
                        x: { ticks: { color: textCol, maxTicksLimit: 10 }, grid: { display: false } },
                        y: { ticks: { color: textCol, callback: v => `₹${(v / 1000).toFixed(0)}k` }, grid: { color: gridCol } },
                    },
                },
            });
        }
    } catch (_e) {}
}

export function initConformalForecastLab() {
    refreshConformalIntervals();
    if (CONFORMAL_WIRED) return;
    CONFORMAL_WIRED = true;

    const confSelect = document.getElementById("conformalConfidenceSelect");
    if (confSelect) confSelect.addEventListener("change", refreshConformalIntervals);
}

export async function refreshBudgetOptimizer() {
    const budgetSlider = document.getElementById("optBudgetSlider");
    const hurdleSlider = document.getElementById("optHurdleSlider");
    const budgetLbl = document.getElementById("optBudgetLbl");
    const hurdleLbl = document.getElementById("optHurdleLbl");
    const optMarginEl = document.getElementById("optMarginOutVal");
    const optLiftEl = document.getElementById("optLiftVsEqualVal");
    const optRoasEl = document.getElementById("optPortfolioRoasVal");
    const optReserveEl = document.getElementById("optReserveVal");
    const tbody = document.getElementById("budgetAllocationTbody");
    const canvas = document.getElementById("budgetAllocationChart");

    if (!budgetSlider || !hurdleSlider || !tbody) return;
    const budget = Number(budgetSlider.value || 250000);
    const hurdle = Number(hurdleSlider.value || 1.5);
    if (budgetLbl) budgetLbl.textContent = _fmtInr(budget, 0);
    if (hurdleLbl) hurdleLbl.textContent = `${hurdle.toFixed(1)}x`;

    try {
        const res = await fetch(nexusApiUrl("/api/v1/campaigns/optimize-budget"), {
            method: "POST",
            headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ total_budget_inr: budget, min_roi_multiple: hurdle }),
        });
        if (!res.ok) {
            if (res.status === 401 || res.status === 403) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">Sign in with predict:execute scope to run KKT Budget Optimization.</td></tr>`;
            }
            return;
        }
        const data = await res.json();
        const s = data.summary || {};
        if (optMarginEl) optMarginEl.textContent = _fmtInr(s.optimal_incremental_margin_inr, 0);
        if (optLiftEl) optLiftEl.textContent = `+${_fmtInr(s.optimizer_gain_over_equal_inr, 0)}`;
        if (optRoasEl) optRoasEl.textContent = `${s.portfolio_roas_x}x`;
        if (optReserveEl) optReserveEl.textContent = _fmtInr(s.unallocated_reserve_inr, 0);

        const rows = data.allocations || [];
        tbody.innerHTML = rows.map(r => `
            <tr>
                <th scope="row">${_esc(r.segment)}</th>
                <td data-label="Allocated Spend">${_fmtInr(r.allocated_budget_inr, 0)} (${r.budget_share_pct}%)</td>
                <td data-label="Equal Split">${_fmtInr(r.equal_split_budget_inr, 0)}</td>
                <td data-label="Expected Margin"><strong style="color:var(--success);">${_fmtInr(r.expected_incremental_margin_inr, 0)}</strong></td>
                <td data-label="Avg / Marginal ROAS">${r.avg_roas_x}x / <strong>${r.marginal_roas_x}x</strong></td>
                <td data-label="Strategy"><small>${_esc(r.channel_strategy)}</small></td>
            </tr>
        `).join("");

        if (typeof Chart !== "undefined" && canvas && rows.length) {
            if (budgetAllocChartInstance) budgetAllocChartInstance.destroy();
            const isLight = document.documentElement.getAttribute("data-theme") === "light";
            const textCol = isLight ? "#334155" : "#D4D4D8";
            const gridCol = isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";

            budgetAllocChartInstance = new Chart(canvas.getContext("2d"), {
                type: "bar",
                data: {
                    labels: rows.map(r => r.segment.split(" (")[0]),
                    datasets: [
                        {
                            label: "KKT Optimal Spend (₹)",
                            data: rows.map(r => r.allocated_budget_inr),
                            backgroundColor: "rgba(16, 185, 129, 0.80)",
                            borderColor: "#10B981",
                            borderWidth: 1,
                            borderRadius: 6,
                        },
                        {
                            label: "Naive Equal Split (₹)",
                            data: rows.map(r => r.equal_split_budget_inr),
                            backgroundColor: "rgba(148, 163, 184, 0.45)",
                            borderColor: "#94A3B8",
                            borderWidth: 1,
                            borderRadius: 6,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: textCol, font: { size: 11 } } },
                        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${_fmtInr(ctx.parsed.y, 0)}` } },
                    },
                    scales: {
                        x: { ticks: { color: textCol }, grid: { display: false } },
                        y: { ticks: { color: textCol, callback: v => `₹${(v / 1000).toFixed(0)}k` }, grid: { color: gridCol } },
                    },
                },
            });
        }
    } catch (_e) {}
}

export function initBudgetOptimizerLab() {
    refreshBudgetOptimizer();
    if (BUDGET_WIRED) return;
    BUDGET_WIRED = true;

    const budgetSlider = document.getElementById("optBudgetSlider");
    const hurdleSlider = document.getElementById("optHurdleSlider");
    const debouncedRun = typeof nexusDebounce === "function" ? nexusDebounce(refreshBudgetOptimizer, 140) : refreshBudgetOptimizer;

    [budgetSlider, hurdleSlider].forEach(el => {
        if (el) {
            el.addEventListener("input", () => {
                const bLbl = document.getElementById("optBudgetLbl");
                const hLbl = document.getElementById("optHurdleLbl");
                if (bLbl && budgetSlider) bLbl.textContent = _fmtInr(budgetSlider.value, 0);
                if (hLbl && hurdleSlider) hLbl.textContent = `${Number(hurdleSlider.value).toFixed(1)}x`;
                debouncedRun();
            });
            el.addEventListener("change", refreshBudgetOptimizer);
        }
    });
}
