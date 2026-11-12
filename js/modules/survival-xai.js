/**
 * Phase 27: Survival Analysis, Weibull Hazard & Exact Shapley XAI
 * Loaded lazily on demand by app.js module router.
 */

let kmSurvivalChartInstance = null;
let xaiAttributionChartInstance = null;
let survivalCfChartInstance = null;
let SURVIVAL_LAB_WIRED = false;

function _escapeSurvivalText(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function _syncRangeProgress(sliderEl) {
    if (!sliderEl || CSS.supports("accent-color", "#2563EB")) return;
    const min = Number(sliderEl.min || 0);
    const max = Number(sliderEl.max || 100);
    const pct = max > min ? ((Number(sliderEl.value) - min) / (max - min)) * 100 : 0;
    sliderEl.style.setProperty("--progress", `${pct.toFixed(1)}%`);
}

async function refreshKaplanMeierCohortCharts() {
    const cohortSelect = document.getElementById("survivalCohortSelect");
    const medianEl = document.getElementById("survivalMedianVal");
    const s90El = document.getElementById("survival90Val");
    const driverEl = document.getElementById("survivalTopDriverVal");
    const tbody = document.getElementById("survivalCohortTbody");
    const kmCanvas = document.getElementById("kmSurvivalChart");
    if (!cohortSelect || !kmCanvas) return;

    const segment = cohortSelect.value || "All";
    try {
        const res = await fetch(nexusApiUrl(`/api/v1/survival/kaplan-meier-report?segment=${encodeURIComponent(segment)}`));
        if (!res.ok) return;
        const data = await res.json();
        const summary = data.summary || {};

        if (medianEl) {
            medianEl.textContent = summary.median_censored_flag ? `>${summary.median_cohort_days}d` : `${summary.median_cohort_days} days`;
        }
        if (s90El) s90El.textContent = `${summary.survival_90d_pct ?? 0}%`;
        if (driverEl) driverEl.textContent = summary.top_global_driver || "Recency";

        const isLight = document.documentElement.getAttribute("data-theme") === "light";
        const textCol = isLight ? "#334155" : "#D4D4D8";
        const gridCol = isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";

        const cohorts = data.cohorts || {};
        const selectedKm = cohorts[segment] || cohorts["All"];
        const vipKm = cohorts["Champions (VIP)"];
        const occKm = cohorts["Occasional / Hibernating"];

        if (typeof Chart !== "undefined" && selectedKm && selectedKm.curve) {
            if (kmSurvivalChartInstance) kmSurvivalChartInstance.destroy();
            const labels = selectedKm.curve.map(pt => `D${pt.day}`);
            const datasets = [
                {
                    label: `${segment} S(t)`,
                    data: selectedKm.curve.map(pt => +(pt.survival * 100).toFixed(1)),
                    borderColor: "#3B82F6",
                    backgroundColor: "rgba(59, 130, 246, 0.14)",
                    borderWidth: 2.5,
                    stepped: true,
                    fill: true,
                    tension: 0
                }
            ];
            if (segment === "All" && vipKm && occKm) {
                datasets.push({
                    label: "Champions (VIP) S(t)",
                    data: vipKm.curve.map(pt => +(pt.survival * 100).toFixed(1)),
                    borderColor: "#10B981",
                    borderWidth: 2,
                    borderDash: [5, 4],
                    stepped: true,
                    fill: false
                });
                datasets.push({
                    label: "Occasional / Hibernating S(t)",
                    data: occKm.curve.map(pt => +(pt.survival * 100).toFixed(1)),
                    borderColor: "#EF4444",
                    borderWidth: 2,
                    borderDash: [3, 3],
                    stepped: true,
                    fill: false
                });
            } else if (selectedKm.curve[0] && selectedKm.curve[0].ci_upper !== undefined) {
                datasets.push({
                    label: "Greenwood 95% Upper CI",
                    data: selectedKm.curve.map(pt => +(pt.ci_upper * 100).toFixed(1)),
                    borderColor: "rgba(16, 185, 129, 0.55)",
                    borderWidth: 1.2,
                    borderDash: [4, 4],
                    stepped: true,
                    fill: false
                });
                datasets.push({
                    label: "Greenwood 95% Lower CI",
                    data: selectedKm.curve.map(pt => +(pt.ci_lower * 100).toFixed(1)),
                    borderColor: "rgba(239, 68, 68, 0.55)",
                    borderWidth: 1.2,
                    borderDash: [4, 4],
                    stepped: true,
                    fill: false
                });
            }

            kmSurvivalChartInstance = new Chart(kmCanvas.getContext("2d"), {
                type: "line",
                data: { labels, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: textCol, font: { size: 11 } } } },
                    scales: {
                        x: { ticks: { color: textCol }, grid: { display: false } },
                        y: {
                            min: 0,
                            max: 100,
                            ticks: { color: textCol, callback: v => `${v}%` },
                            grid: { color: gridCol }
                        }
                    }
                }
            });
        }

        if (tbody) {
            const cohortNames = ["All", "Champions (VIP)", "Loyal Customers", "At-Risk / Lapsing", "Occasional / Hibernating"];
            tbody.innerHTML = cohortNames
                .filter(name => cohorts[name])
                .map(name => {
                    const c = cohorts[name];
                    const medTxt = c.median_censored_flag ? `>${c.median_survival_days}d` : `${c.median_survival_days}d`;
                    return `
                        <tr>
                            <th scope="row">${_escapeSurvivalText(name)}</th>
                            <td>${Number(c.n_subjects).toLocaleString("en-IN")}</td>
                            <td>${Number(c.n_events).toLocaleString("en-IN")}</td>
                            <td>${medTxt}</td>
                            <td><strong>${(c.s_90 * 100).toFixed(1)}%</strong></td>
                            <td>${(c.s_180 * 100).toFixed(1)}%</td>
                            <td>${c.rmst_365}d</td>
                        </tr>
                    `;
                })
                .join("");
        }
    } catch (_e) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--text-muted);">Connect FastAPI (:8000) to render Kaplan-Meier survival cohorts.</td></tr>`;
        }
    }
}

async function refreshCustomerXaiAndCounterfactual() {
    const custInput = document.getElementById("xaiCustomerInput");
    const recSlider = document.getElementById("xaiRecencySlider");
    const freqSlider = document.getElementById("xaiFreqSlider");
    const aovSlider = document.getElementById("xaiAovSlider");
    const recLbl = document.getElementById("xaiRecencyLbl");
    const freqLbl = document.getElementById("xaiFreqLbl");
    const aovLbl = document.getElementById("xaiAovLbl");
    const liftEl = document.getElementById("survivalLiftVal");
    const summaryEl = document.getElementById("survivalCounterfactualSummary");
    const xaiCanvas = document.getElementById("xaiAttributionChart");
    const cfCanvas = document.getElementById("survivalCounterfactualChart");

    if (!custInput || !recSlider || !freqSlider || !aovSlider) return;

    const customerId = String(custInput.value || "14096").trim() || "14096";
    const recDays = Number(recSlider.value || 45);
    const freqOrders = Number(freqSlider.value || 2);
    const aovPct = Number(aovSlider.value || 15);

    if (recLbl) recLbl.textContent = `${recDays} days`;
    if (freqLbl) freqLbl.textContent = `+${freqOrders} orders`;
    if (aovLbl) aovLbl.textContent = `+${aovPct}%`;
    _syncRangeProgress(recSlider);
    _syncRangeProgress(freqSlider);
    _syncRangeProgress(aovSlider);

    try {
        const [xaiRes, cfRes] = await Promise.all([
            fetch(nexusApiUrl(`/api/v1/survival/explain/${encodeURIComponent(customerId)}`)),
            fetch(nexusApiUrl("/api/v1/survival/simulate-intervention"), {
                method: "POST",
                headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify({
                    customer_id: customerId,
                    recency_reduction_days: recDays,
                    frequency_boost_orders: freqOrders,
                    aov_boost_pct: aovPct
                })
            })
        ]);

        const isLight = document.documentElement.getAttribute("data-theme") === "light";
        const textCol = isLight ? "#334155" : "#D4D4D8";
        const gridCol = isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";

        if (xaiRes.ok && xaiCanvas && typeof Chart !== "undefined") {
            const xaiData = await xaiRes.json();
            const contribs = xaiData.contributions || [];
            if (xaiAttributionChartInstance) xaiAttributionChartInstance.destroy();
            xaiAttributionChartInstance = new Chart(xaiCanvas.getContext("2d"), {
                type: "bar",
                data: {
                    labels: contribs.map(c => c.label),
                    datasets: [{
                        label: "Shapley Attribution (pp)",
                        data: contribs.map(c => c.shapley_pp),
                        backgroundColor: contribs.map(c => (c.shapley_pp >= 0 ? "rgba(239, 68, 68, 0.80)" : "rgba(16, 185, 129, 0.80)")),
                        borderColor: contribs.map(c => (c.shapley_pp >= 0 ? "#EF4444" : "#10B981")),
                        borderWidth: 1,
                        borderRadius: 5
                    }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: textCol, font: { size: 11 } } } },
                    scales: {
                        x: { ticks: { color: textCol, callback: v => `${v > 0 ? "+" : ""}${v}pp` }, grid: { color: gridCol } },
                        y: { ticks: { color: textCol, font: { size: 10 } }, grid: { display: false } }
                    }
                }
            });
        }

        if (cfRes.ok) {
            const cfData = await cfRes.json();
            const sum = cfData.summary || {};
            const deltaS90 = Number(sum.delta_s90_pp || 0);
            if (liftEl) liftEl.textContent = `${deltaS90 >= 0 ? "+" : ""}${deltaS90.toFixed(1)} pp`;

            if (cfCanvas && typeof Chart !== "undefined" && cfData.comparison_curve) {
                if (survivalCfChartInstance) survivalCfChartInstance.destroy();
                survivalCfChartInstance = new Chart(cfCanvas.getContext("2d"), {
                    type: "line",
                    data: {
                        labels: cfData.comparison_curve.map(pt => `D${pt.day}`),
                        datasets: [
                            {
                                label: "Baseline Weibull S(t)",
                                data: cfData.comparison_curve.map(pt => +(pt.baseline_survival * 100).toFixed(1)),
                                borderColor: "#94A3B8",
                                borderDash: [5, 4],
                                borderWidth: 2,
                                fill: false,
                                tension: 0.25
                            },
                            {
                                label: "Post-Intervention S(t)",
                                data: cfData.comparison_curve.map(pt => +(pt.counterfactual_survival * 100).toFixed(1)),
                                borderColor: "#10B981",
                                backgroundColor: "rgba(16, 185, 129, 0.14)",
                                borderWidth: 2.5,
                                fill: true,
                                tension: 0.25
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: textCol, font: { size: 11 } } } },
                        scales: {
                            x: { ticks: { color: textCol }, grid: { display: false } },
                            y: { min: 0, max: 100, ticks: { color: textCol, callback: v => `${v}%` }, grid: { color: gridCol } }
                        }
                    }
                });
            }

            if (summaryEl) {
                summaryEl.innerHTML = `
                    <div class="result-grid">
                        <div class="result-stat"><strong>Account Cohort</strong><span>${_escapeSurvivalText(cfData.cohort)}</span></div>
                        <div class="result-stat"><strong>Baseline → Treated S(90)</strong><span>${sum.baseline_s90_pct}% → ${sum.counterfactual_s90_pct}%</span></div>
                        <div class="result-stat"><strong>RMST-365 Lifespan Gain</strong><span style="color:#10B981;">+${sum.rmst_gain_days} days</span></div>
                        <div class="result-stat"><strong>Protected Annual Margin</strong><span style="color:#10B981;">₹${Number(sum.protected_margin_gbp || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span></div>
                    </div>
                `;
            }
        } else if (cfRes.status === 401 || cfRes.status === 403) {
            if (summaryEl) {
                summaryEl.innerHTML = `<div class="btyd-stat-box"><strong>Strict RBAC Active</strong><small>Sign in with predict:execute scope to simulate counterfactual retention curves.</small></div>`;
            }
        }
    } catch (_e) {
        if (summaryEl) {
            summaryEl.innerHTML = `<div class="btyd-stat-box"><strong>Survival Engine Offline</strong><small>Connect backend :8000 for live Weibull &amp; Shapley attribution.</small></div>`;
        }
    }
}

export function initSurvivalXaiLab() {
    refreshKaplanMeierCohortCharts();
    refreshCustomerXaiAndCounterfactual();

    if (SURVIVAL_LAB_WIRED) return;
    SURVIVAL_LAB_WIRED = true;

    const cohortSelect = document.getElementById("survivalCohortSelect");
    const explainBtn = document.getElementById("xaiExplainBtn");
    const recSlider = document.getElementById("xaiRecencySlider");
    const freqSlider = document.getElementById("xaiFreqSlider");
    const aovSlider = document.getElementById("xaiAovSlider");

    if (cohortSelect) cohortSelect.addEventListener("change", refreshKaplanMeierCohortCharts);
    if (explainBtn) explainBtn.addEventListener("click", refreshCustomerXaiAndCounterfactual);
    const debouncedSurvival = nexusDebounce(refreshCustomerXaiAndCounterfactual, 150);
    [recSlider, freqSlider, aovSlider].forEach(el => {
        if (el) {
            el.addEventListener("input", () => {
                const rLbl = document.getElementById("xaiRecencyLbl");
                const fLbl = document.getElementById("xaiFreqLbl");
                const aLbl = document.getElementById("xaiAovLbl");
                if (rLbl && recSlider) rLbl.textContent = `${recSlider.value} days`;
                if (fLbl && freqSlider) fLbl.textContent = `+${freqSlider.value} orders`;
                if (aLbl && aovSlider) aLbl.textContent = `+${aovSlider.value}%`;
                debouncedSurvival();
            });
            el.addEventListener("change", refreshCustomerXaiAndCounterfactual);
        }
    });
}

