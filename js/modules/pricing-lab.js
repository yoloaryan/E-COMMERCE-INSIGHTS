/**
 * Phase 13: Dynamic Pricing Elasticity & A/B Experimentation Lab
 * Loaded lazily on demand by app.js module router.
 */

const PRICING_OFFLINE_CATEGORIES = [
    { category: "Kitchen & Dining", elasticity_coefficient: -1.723, r_squared: 0.5066, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 2.24, baseline_total_units: 1112255, baseline_revenue_gbp: 2493143.89, baseline_cogs_ratio: 0.47, baseline_gross_margin_gbp: 1321366.26, optimal_price_change_pct: 12.0, optimal_price_gbp: 2.51, margin_uplift_gbp: 11719.37, margin_uplift_pct: 0.89 },
    { category: "Home Decor & Lighting", elasticity_coefficient: -1.757, r_squared: 0.5171, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 1.90, baseline_total_units: 1324278, baseline_revenue_gbp: 2511398.72, baseline_cogs_ratio: 0.44, baseline_gross_margin_gbp: 1406383.28, optimal_price_change_pct: 2.0, optimal_price_gbp: 1.93, margin_uplift_gbp: 419.31, margin_uplift_pct: 0.03 },
    { category: "Bags & Storage", elasticity_coefficient: -1.694, r_squared: 0.4242, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 2.09, baseline_total_units: 585811, baseline_revenue_gbp: 1222326.21, baseline_cogs_ratio: 0.49, baseline_gross_margin_gbp: 623386.37, optimal_price_change_pct: 20.0, optimal_price_gbp: 2.50, margin_uplift_gbp: 13867.44, margin_uplift_pct: 2.22 },
    { category: "Seasonal & Party", elasticity_coefficient: -1.628, r_squared: 0.5066, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 1.45, baseline_total_units: 294157, baseline_revenue_gbp: 427986.53, baseline_cogs_ratio: 0.36, baseline_gross_margin_gbp: 273911.38, optimal_price_change_pct: -7.0, optimal_price_gbp: 1.35, margin_uplift_gbp: 634.36, margin_uplift_pct: 0.23 },
    { category: "Stationery & Craft", elasticity_coefficient: -1.688, r_squared: 0.5001, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 1.09, baseline_total_units: 626868, baseline_revenue_gbp: 680314.90, baseline_cogs_ratio: 0.34, baseline_gross_margin_gbp: 449007.83, optimal_price_change_pct: -17.0, optimal_price_gbp: 0.90, margin_uplift_gbp: 7556.78, margin_uplift_pct: 1.68 },
    { category: "General Giftware", elasticity_coefficient: -1.643, r_squared: 0.5020, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 2.06, baseline_total_units: 1081846, baseline_revenue_gbp: 2225737.60, baseline_cogs_ratio: 0.43, baseline_gross_margin_gbp: 1268670.43, optimal_price_change_pct: 10.0, optimal_price_gbp: 2.26, margin_uplift_gbp: 6418.82, margin_uplift_pct: 0.51 }
];

export function initPricingLab() {
    const tbody = document.getElementById("pricingElasticityTbody");
    const catSelect = document.getElementById("pricingCategorySelect");
    const priceSlider = document.getElementById("pricingChangeSlider");
    const cogsSlider = document.getElementById("pricingCogsSlider");
    const lblPriceChange = document.getElementById("lblPricingChange");
    const lblCogs = document.getElementById("lblPricingCogs");
    const btnApplyOptimal = document.getElementById("btnPricingApplyOptimal");
    const btnRefresh = document.getElementById("btnRefreshElasticity");

    if (!tbody || !catSelect || !priceSlider || !cogsSlider) return;

    let elasticityReport = {
        avg_portfolio_elasticity: -1.689,
        total_skus_analyzed: 3804,
        total_transactions_analyzed: 527573,
        data_source: "calibrated_matrix",
        categories: PRICING_OFFLINE_CATEGORIES,
        experiments_ledger: []
    };

    let payoffChartInstance = null;
    let powerChartInstance = null;
    let simTimer = null;

    function escapePricingHtml(str) {
        return String(str ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function syncModernSlider(slider) {
        if (!slider) return;
        slider.style.setProperty("--attr-min", slider.min || 0);
        slider.style.setProperty("--attr-max", slider.max || 100);
        slider.style.setProperty("--control-value", slider.value);
    }

    function getSelectedCategoryMeta() {
        const cats = elasticityReport.categories || PRICING_OFFLINE_CATEGORIES;
        return cats.find(c => c.category === catSelect.value) || cats[0];
    }

    function renderElasticityTable() {
        const cats = elasticityReport.categories || [];
        const selectedName = catSelect.value;

        const kpiAvgE = document.getElementById("pricingKpiAvgElasticity");
        const kpiSource = document.getElementById("pricingKpiDataSource");
        const kpiUplift = document.getElementById("pricingKpiTotalUplift");
        const kpiSkus = document.getElementById("pricingKpiSkuCount");
        const kpiTxns = document.getElementById("pricingKpiTxnCount");
        const kpiExps = document.getElementById("pricingKpiExpCount");

        if (kpiAvgE) kpiAvgE.textContent = Number(elasticityReport.avg_portfolio_elasticity || -1.69).toFixed(2);
        if (kpiSource) kpiSource.textContent = elasticityReport.data_source === "production_parquet" ? "Live Parquet Fixed-Effects OLS" : "Within-SKU Log-Log OLS";
        if (kpiUplift) {
            const totalGain = cats.reduce((acc, c) => acc + (c.margin_uplift_gbp || 0), 0);
            kpiUplift.textContent = `+₹${Math.round(totalGain).toLocaleString("en-IN")}`;
        }
        if (kpiSkus) kpiSkus.textContent = Number(elasticityReport.total_skus_analyzed || 3804).toLocaleString("en-IN");
        if (kpiTxns) kpiTxns.textContent = `${Number(elasticityReport.total_transactions_analyzed || 527573).toLocaleString("en-IN")} Valid Rows`;
        if (kpiExps) kpiExps.textContent = `${(elasticityReport.experiments_ledger || []).length} Recorded`;

        tbody.innerHTML = cats.map(c => {
            const isSelected = c.category === selectedName;
            const optSign = c.optimal_price_change_pct > 0 ? `+${c.optimal_price_change_pct}%` : `${c.optimal_price_change_pct}%`;
            const optBadgeColor = c.optimal_price_change_pct > 0 ? "green" : c.optimal_price_change_pct < 0 ? "gold" : "blue";

            return `
                <tr class="${isSelected ? "selected-category-row" : ""}" data-pricing-category="${c.category}">
                    <th scope="row">${c.category}</th>
                    <td><code>${Number(c.elasticity_coefficient).toFixed(3)}</code></td>
                    <td>${Number(c.r_squared || 0.48).toFixed(2)}</td>
                    <td>₹${Number(c.baseline_avg_price_gbp).toFixed(2)}</td>
                    <td>₹${Math.round(c.baseline_revenue_gbp).toLocaleString("en-IN")}</td>
                    <td><span class="badge ${optBadgeColor}">${optSign} → ₹${Number(c.optimal_price_gbp).toFixed(2)}</span></td>
                    <td style="color: var(--success); font-weight: 700;">+₹${Math.round(c.margin_uplift_gbp).toLocaleString("en-IN")} (+${Number(c.margin_uplift_pct).toFixed(2)}%)</td>
                    <td><button type="button" class="btn btn-outline btn-xs btn-select-pricing-cat" data-cat="${c.category}">Simulate</button></td>
                </tr>
            `;
        }).join("");

        tbody.querySelectorAll("tr[data-pricing-category]").forEach(row => {
            row.addEventListener("click", () => {
                const catName = row.getAttribute("data-pricing-category");
                if (catName) selectPricingCategory(catName);
            });
        });

        renderExperimentLedger(elasticityReport.experiments_ledger || []);
    }

    function selectPricingCategory(catName, applyOptimal = false) {
        catSelect.value = catName;
        const meta = getSelectedCategoryMeta();
        if (meta) {
            cogsSlider.value = Math.round((meta.baseline_cogs_ratio || 0.45) * 100);
            syncModernSlider(cogsSlider);
            if (applyOptimal) {
                priceSlider.value = meta.optimal_price_change_pct;
                syncModernSlider(priceSlider);
            }
        }
        renderElasticityTable();
        runPriceSimulation();
    }

    async function loadElasticityReport() {
        try {
            const res = await fetch(nexusApiUrl("/api/v1/pricing/elasticity-report"));
            if (res.ok) {
                const data = await res.json();
                if (data.categories && data.categories.length > 0) {
                    elasticityReport = data;
                    const optCats = data.categories.map(c => `<option value="${c.category}">${c.category}</option>`).join("");
                    const prevCat = catSelect.value;
                    catSelect.innerHTML = optCats;
                    if (data.categories.some(c => c.category === prevCat)) catSelect.value = prevCat;

                    const abCat = document.getElementById("abExpCategory");
                    if (abCat) {
                        const prevAb = abCat.value;
                        abCat.innerHTML = optCats;
                        if (data.categories.some(c => c.category === prevAb)) abCat.value = prevAb;
                    }
                }
            }
        } catch (err) {
            console.warn("[PricingLab] Backend offline, using calibrated dataset metrics.");
        }
        const meta = getSelectedCategoryMeta();
        if (meta) {
            cogsSlider.value = Math.round((meta.baseline_cogs_ratio || 0.47) * 100);
        }
        syncModernSlider(priceSlider);
        syncModernSlider(cogsSlider);
        renderElasticityTable();
        runPriceSimulation();
    }

    function computeLocalSimulation(catMeta, priceChangePct, cogsRatio) {
        const e = catMeta.elasticity_coefficient;
        const basePrice = catMeta.baseline_avg_price_gbp;
        const baseUnits = catMeta.baseline_total_units;
        const unitCost = basePrice * cogsRatio;

        const pointAt = (pct) => {
            const mult = Math.max(0.2, 1 + pct / 100);
            const p = basePrice * mult;
            const u = baseUnits * Math.pow(mult, e);
            const rev = p * u;
            const profit = (p - unitCost) * u;
            return {
                price_change_pct: pct,
                unit_price_gbp: Number(p.toFixed(2)),
                projected_units: Math.round(u),
                revenue_gbp: Number(rev.toFixed(2)),
                gross_profit_gbp: Number(profit.toFixed(2)),
                margin_pct: Number((((p - unitCost) / p) * 100).toFixed(2))
            };
        };

        const baseline = pointAt(0);
        const sim = pointAt(priceChangePct);
        const curve = [];
        let optPt = baseline;
        for (let pct = -20; pct <= 20; pct += 2) {
            const pt = pointAt(pct);
            curve.push(pt);
            if (pt.gross_profit_gbp > optPt.gross_profit_gbp) optPt = pt;
        }

        const revDelta = sim.revenue_gbp - baseline.revenue_gbp;
        const profitDelta = sim.gross_profit_gbp - baseline.gross_profit_gbp;

        return {
            category: catMeta.category,
            demand_regime: catMeta.demand_regime,
            elasticity_used: e,
            baseline: { avg_price_gbp: baseline.unit_price_gbp, total_units: baseline.projected_units, revenue_gbp: baseline.revenue_gbp, gross_profit_gbp: baseline.gross_profit_gbp },
            simulated: {
                new_price_gbp: sim.unit_price_gbp,
                projected_units: sim.projected_units,
                projected_revenue_gbp: sim.revenue_gbp,
                projected_gross_profit_gbp: sim.gross_profit_gbp,
                margin_pct: sim.margin_pct,
                unit_delta_pct: Number((((sim.projected_units - baseline.projected_units) / baseline.projected_units) * 100).toFixed(2)),
                revenue_delta_gbp: Number(revDelta.toFixed(2)),
                revenue_delta_pct: Number(((revDelta / baseline.revenue_gbp) * 100).toFixed(2)),
                profit_delta_gbp: Number(profitDelta.toFixed(2)),
                profit_delta_pct: Number(((profitDelta / baseline.gross_profit_gbp) * 100).toFixed(2))
            },
            optimal_point: {
                price_change_pct: optPt.price_change_pct,
                optimal_price_gbp: optPt.unit_price_gbp,
                max_gross_profit_gbp: optPt.gross_profit_gbp,
                profit_gain_gbp: Number((optPt.gross_profit_gbp - baseline.gross_profit_gbp).toFixed(2))
            },
            payoff_curve: curve,
            recommendation: `${catMeta.category} (ε=${e.toFixed(2)}) maximizes bounded gross profit at ${optPt.price_change_pct > 0 ? "+" : ""}${optPt.price_change_pct}% adjustment (+₹${Math.round(optPt.gross_profit_gbp - baseline.gross_profit_gbp).toLocaleString("en-IN")}).`
        };
    }

    async function runPriceSimulation() {
        const deltaPct = parseFloat(priceSlider.value) || 0;
        const cogsPct = parseFloat(cogsSlider.value) || 47;
        const cogsRatio = cogsPct / 100;

        syncModernSlider(priceSlider);
        syncModernSlider(cogsSlider);

        if (lblPriceChange) {
            lblPriceChange.textContent = `${deltaPct > 0 ? "+" : ""}${deltaPct.toFixed(1)}%`;
            priceSlider.setAttribute("aria-valuetext", `${deltaPct > 0 ? "plus " : ""}${deltaPct.toFixed(1)} percent price adjustment`);
        }
        if (lblCogs) {
            lblCogs.textContent = `${Math.round(cogsPct)}%`;
            cogsSlider.setAttribute("aria-valuetext", `${Math.round(cogsPct)} percent cost of goods sold`);
        }

        const meta = getSelectedCategoryMeta();
        let simData = null;

        try {
            const res = await fetch(nexusApiUrl("/api/v1/pricing/simulate-price-change"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    category: catSelect.value,
                    price_change_pct: deltaPct,
                    cogs_ratio: cogsRatio
                })
            });
            if (res.ok) simData = await res.json();
        } catch (err) {
            // Fallback below
        }

        if (!simData && meta) {
            simData = computeLocalSimulation(meta, deltaPct, cogsRatio);
        }
        if (!simData) return;

        const s = simData.simulated;
        const opt = simData.optimal_point;

        const outPrice = document.getElementById("simUnitPriceOut");
        const outUnits = document.getElementById("simUnitsOut");
        const outRev = document.getElementById("simRevOut");
        const outProfit = document.getElementById("simProfitOut");
        const regimeBadge = document.getElementById("pricingRegimeBadge");
        const optBadge = document.getElementById("pricingOptimalBadge");
        const recBox = document.getElementById("pricingRecommendationBox");

        if (outPrice) outPrice.innerHTML = `₹${Number(s.new_price_gbp).toFixed(2)} <small style="font-size:0.72rem;color:var(--text-muted);">${deltaPct >= 0 ? "+" : ""}${deltaPct}%</small>`;
        if (outUnits) outUnits.innerHTML = `${Number(s.projected_units).toLocaleString("en-IN")} <small style="font-size:0.72rem;color:${s.unit_delta_pct >= 0 ? "var(--success)" : "var(--warning)"};">(${s.unit_delta_pct >= 0 ? "+" : ""}${s.unit_delta_pct}%)</small>`;
        if (outRev) outRev.innerHTML = `₹${Math.round(s.projected_revenue_gbp).toLocaleString("en-IN")} <small style="font-size:0.72rem;color:${s.revenue_delta_gbp >= 0 ? "var(--success)" : "var(--warning)"};">(${s.revenue_delta_pct >= 0 ? "+" : ""}${s.revenue_delta_pct}%)</small>`;
        if (outProfit) {
            outProfit.style.color = s.profit_delta_gbp >= 0 ? "var(--success)" : "var(--danger)";
            outProfit.innerHTML = `₹${Math.round(s.projected_gross_profit_gbp).toLocaleString("en-IN")} <small style="font-size:0.72rem;">(${s.profit_delta_gbp >= 0 ? "+" : "-"}₹${Math.abs(Math.round(s.profit_delta_gbp)).toLocaleString("en-IN")})</small>`;
        }
        if (regimeBadge) regimeBadge.textContent = `${simData.demand_regime} (ε=${Number(simData.elasticity_used).toFixed(2)})`;
        if (optBadge) optBadge.textContent = `Optimal: ${opt.price_change_pct > 0 ? "+" : ""}${opt.price_change_pct}% (₹${Number(opt.optimal_price_gbp).toFixed(2)})`;
        if (recBox) recBox.innerHTML = `<strong>💡 Pricing Strategy Insight:</strong> ${simData.recommendation}`;

        renderPayoffCurveChart(simData.payoff_curve, deltaPct, opt.price_change_pct);
    }

    function renderPayoffCurveChart(curve, activeDelta, optDelta) {
        const canvas = document.getElementById("pricingPayoffChart");
        if (!canvas || typeof Chart === "undefined") return;

        const labels = curve.map(pt => `${pt.price_change_pct > 0 ? "+" : ""}${pt.price_change_pct}%`);
        const revs = curve.map(pt => pt.revenue_gbp);
        const profits = curve.map(pt => pt.gross_profit_gbp);

        const profitRadii = curve.map(pt => {
            if (Math.abs(pt.price_change_pct - activeDelta) <= 1.0) return 7;
            if (Math.abs(pt.price_change_pct - optDelta) <= 1.0) return 6;
            return 2.5;
        });

        const profitColors = curve.map(pt => {
            if (Math.abs(pt.price_change_pct - activeDelta) <= 1.0) return "#F59E0B";
            if (Math.abs(pt.price_change_pct - optDelta) <= 1.0) return "#10B981";
            return "#34D399";
        });

        if (payoffChartInstance) {
            payoffChartInstance.destroy();
            payoffChartInstance = null;
        }

        payoffChartInstance = new Chart(canvas, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Projected Gross Revenue (₹)",
                        data: revs,
                        borderColor: "#38BDF8",
                        backgroundColor: "rgba(56, 189, 248, 0.08)",
                        borderWidth: 2,
                        tension: 0.25,
                        pointRadius: 2
                    },
                    {
                        label: "Projected Gross Profit (₹)",
                        data: profits,
                        borderColor: "#10B981",
                        backgroundColor: "rgba(16, 185, 129, 0.14)",
                        fill: true,
                        borderWidth: 3,
                        tension: 0.25,
                        pointRadius: profitRadii,
                        pointBackgroundColor: profitColors
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", labels: { color: "#94A3B8" } },
                    tooltip: {
                        callbacks: {
                            label: ctx => `${ctx.dataset.label}: ₹${Math.round(ctx.parsed.y).toLocaleString("en-IN")}`
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: { callback: v => `₹${(v / 100000).toFixed(1)}L` },
                        grid: { color: "rgba(255,255,255,0.06)" }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    function scheduleSimulation() {
        syncModernSlider(priceSlider);
        syncModernSlider(cogsSlider);
        const deltaPct = parseFloat(priceSlider.value) || 0;
        if (lblPriceChange) lblPriceChange.textContent = `${deltaPct > 0 ? "+" : ""}${deltaPct.toFixed(1)}%`;
        if (lblCogs) lblCogs.textContent = `${Math.round(parseFloat(cogsSlider.value) || 47)}%`;

        clearTimeout(simTimer);
        simTimer = setTimeout(runPriceSimulation, 80);
    }

    priceSlider.addEventListener("input", scheduleSimulation);
    cogsSlider.addEventListener("input", scheduleSimulation);
    catSelect.addEventListener("change", () => selectPricingCategory(catSelect.value, false));

    if (btnApplyOptimal) {
        btnApplyOptimal.addEventListener("click", () => {
            const meta = getSelectedCategoryMeta();
            if (meta) {
                priceSlider.value = meta.optimal_price_change_pct;
                syncModernSlider(priceSlider);
                runPriceSimulation();
                showToast("Optimal Price Loaded", `Applied ${meta.optimal_price_change_pct > 0 ? "+" : ""}${meta.optimal_price_change_pct}% margin-maximizing price for ${meta.category}`, "success");
            }
        });
    }

    if (btnRefresh) {
        btnRefresh.addEventListener("click", () => {
            loadElasticityReport();
            showToast("Matrix Recalculated", "Refreshed category within-SKU log-log elasticity regressions", "info");
        });
    }

    window.setPricingDeltaPreset = function(pct) {
        priceSlider.value = pct;
        syncModernSlider(priceSlider);
        runPriceSimulation();
    };

    // Accessible A/B Testing Sub-tabs (focusgroup + keyboard fallback + until-found sync)
    const abTabs = [
        { btn: document.getElementById("abRunTabBtn"), panel: document.getElementById("abRunPanel") },
        { btn: document.getElementById("abPowerTabBtn"), panel: document.getElementById("abPowerPanel") }
    ];

    function activateAbTab(targetIndex, moveFocus = false) {
        abTabs.forEach((item, idx) => {
            const isSelected = idx === targetIndex;
            if (item.btn) {
                item.btn.setAttribute("aria-selected", String(isSelected));
                item.btn.toggleAttribute("focusgroupstart", isSelected);
                if (isSelected && moveFocus) item.btn.focus();
            }
            if (item.panel) {
                if (isSelected) {
                    item.panel.removeAttribute("hidden");
                    item.panel.setAttribute("tabindex", "0");
                } else {
                    item.panel.setAttribute("hidden", "until-found");
                    item.panel.removeAttribute("tabindex");
                }
            }
        });
    }

    abTabs.forEach((item, idx) => {
        if (item.btn) {
            item.btn.addEventListener("click", () => activateAbTab(idx));
            item.btn.addEventListener("keydown", (e) => {
                if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                    e.preventDefault();
                    const nextIdx = (idx + 1) % abTabs.length;
                    activateAbTab(nextIdx, true);
                } else if (e.key === "Home") {
                    e.preventDefault();
                    activateAbTab(0, true);
                } else if (e.key === "End") {
                    e.preventDefault();
                    activateAbTab(abTabs.length - 1, true);
                }
            });
        }
        if (item.panel) {
            item.panel.addEventListener("beforematch", () => activateAbTab(idx));
        }
    });

    // Controlled Holdout A/B Experiment Form
    const abExpForm = document.getElementById("abExperimentForm");
    const abResultArea = document.getElementById("abExperimentResultArea");

    function renderExperimentLedger(list) {
        const ledgerBody = document.getElementById("abExperimentsLedgerBody");
        const kpiExps = document.getElementById("pricingKpiExpCount");
        if (kpiExps) kpiExps.textContent = `${list.length} Recorded`;
        if (!ledgerBody) return;

        if (!list.length) {
            ledgerBody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:1rem;">No experiments executed in this session yet.</td></tr>`;
            return;
        }

        ledgerBody.innerHTML = list.map(exp => {
            const st = exp.statistics || {};
            const w = st.winner || "INCONCLUSIVE";
            const badgeCls = w === "VARIANT" ? "green" : w === "CONTROL" ? "gold" : "blue";
            const uplift = Number(st.relative_profit_per_visitor_uplift_pct || 0);
            return `
                <tr>
                    <td><code>${escapePricingHtml(exp.experiment_id)}</code></td>
                    <td><strong>${escapePricingHtml(exp.experiment_name)}</strong></td>
                    <td>${escapePricingHtml(exp.category)}</td>
                    <td>${exp.price_change_pct > 0 ? "+" : ""}${exp.price_change_pct}%</td>
                    <td style="color:${uplift >= 0 ? "var(--success)" : "var(--danger)"};font-weight:600;">${uplift >= 0 ? "+" : ""}${uplift.toFixed(2)}%</td>
                    <td><code>p=${Number(st.p_value).toFixed(4)}</code></td>
                    <td><span class="badge ${badgeCls}">${escapePricingHtml(w)}</span></td>
                </tr>
            `;
        }).join("");
    }

    function renderAbExperimentResult(exp) {
        if (!abResultArea || !exp) return;
        const c = exp.control;
        const v = exp.variant;
        const st = exp.statistics;
        const verdictColor = st.winner === "VARIANT" ? "var(--success)" : st.winner === "CONTROL" ? "var(--warning)" : "var(--primary)";

        abResultArea.innerHTML = `
            <div class="ab-arms-comparison-grid">
                <div class="ab-arm-card ${st.winner === "CONTROL" ? "winner-arm" : ""}">
                    <div class="ab-arm-header">
                        <strong>🅰️ Control Holdout (${exp.holdout_pct}%)</strong>
                        <span class="badge blue">₹${Number(c.unit_price_gbp).toFixed(2)}</span>
                    </div>
                    <div class="ab-arm-stats-list">
                        <div class="ab-arm-stat-row"><span>Visitors:</span><strong>${c.visitors.toLocaleString("en-IN")}</strong></div>
                        <div class="ab-arm-stat-row"><span>Conversions (CVR):</span><strong>${c.conversions.toLocaleString("en-IN")} (${c.conversion_rate_pct}%)</strong></div>
                        <div class="ab-arm-stat-row"><span>Revenue / Visitor:</span><strong>₹${Number(c.revenue_per_visitor_gbp).toFixed(2)}</strong></div>
                        <div class="ab-arm-stat-row"><span>Profit / Visitor:</span><strong>₹${Number(c.profit_per_visitor_gbp).toFixed(2)}</strong></div>
                    </div>
                </div>
                <div class="ab-arm-card ${st.winner === "VARIANT" ? "winner-arm" : ""}">
                    <div class="ab-arm-header">
                        <strong>🅱️ Price Variant (${exp.price_change_pct > 0 ? "+" : ""}${exp.price_change_pct}%)</strong>
                        <span class="badge ${st.winner === "VARIANT" ? "green" : "gold"}">₹${Number(v.unit_price_gbp).toFixed(2)}</span>
                    </div>
                    <div class="ab-arm-stats-list">
                        <div class="ab-arm-stat-row"><span>Visitors:</span><strong>${v.visitors.toLocaleString("en-IN")}</strong></div>
                        <div class="ab-arm-stat-row"><span>Conversions (CVR):</span><strong>${v.conversions.toLocaleString("en-IN")} (${v.conversion_rate_pct}%)</strong></div>
                        <div class="ab-arm-stat-row"><span>Revenue / Visitor:</span><strong>₹${Number(v.revenue_per_visitor_gbp).toFixed(2)}</strong></div>
                        <div class="ab-arm-stat-row"><span>Profit / Visitor:</span><strong>₹${Number(v.profit_per_visitor_gbp).toFixed(2)}</strong></div>
                    </div>
                </div>
            </div>
            <div style="padding:0.85rem 1rem;background:var(--bg-surface-alt);border-radius:var(--radius-sm);border-left:4px solid ${verdictColor};">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.35rem;">
                    <strong style="color:${verdictColor};">VERDICT: ${escapePricingHtml(st.winner)} (Z = ${st.z_statistic}, p = ${st.p_value})</strong>
                    <span class="badge ${st.statistically_significant ? "green" : "gold"}">${st.statistically_significant ? "✓ p < 0.05 Significant" : "Inconclusive"} • Power ${st.achieved_power_pct}%</span>
                </div>
                <p style="margin:0;font-size:0.84rem;color:var(--text-primary);">${escapePricingHtml(st.verdict)}</p>
                <small style="color:var(--text-muted);display:block;margin-top:0.25rem;">95% CVR Uplift CI: [${st.ci_95_cvr_uplift_pct[0]}%, ${st.ci_95_cvr_uplift_pct[1]}%]</small>
            </div>
        `;
    }

    if (abExpForm) {
        abExpForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById("btnLaunchAbExp");
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "⏳ Running Randomized Holdout Split...";
            }

            const payload = {
                experiment_name: document.getElementById("abExpName").value.trim(),
                category: document.getElementById("abExpCategory").value,
                price_change_pct: parseFloat(document.getElementById("abExpPriceChange").value) || 0,
                holdout_pct: parseFloat(document.getElementById("abExpHoldoutPct").value) || 20,
                sample_size: parseInt(document.getElementById("abExpSampleSize").value, 10) || 10000,
                baseline_conversion_rate: (parseFloat(document.getElementById("abExpBaseCvr").value) || 4.5) / 100,
                cogs_ratio: (parseFloat(cogsSlider.value) || 47) / 100,
                seed: Math.floor(Math.random() * 100000)
            };

            try {
                const res = await fetch(nexusApiUrl("/api/v1/pricing/run-ab-experiment"), {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify(payload)
                });
                if (res.status === 401 || res.status === 403) {
                    const errBody = await res.json().catch(() => ({}));
                    showToast("RBAC Access Denied", errBody.detail || `HTTP ${res.status} on A/B Experiment`, "alert");
                    return;
                }
                if (res.ok) {
                    const data = await res.json();
                    const exp = data.experiment;
                    renderAbExperimentResult(exp);
                    elasticityReport.experiments_ledger = [exp, ...(elasticityReport.experiments_ledger || [])].slice(0, 25);
                    renderExperimentLedger(elasticityReport.experiments_ledger);
                    showToast("A/B Experiment Complete", `${exp.experiment_name}: Verdict ${exp.statistics.winner}`, "success");
                } else {
                    showToast("Experiment Error", `Server returned HTTP ${res.status}`, "alert");
                }
            } catch (err) {
                showToast("Experiment Offline Notice", "Start FastAPI :8000 to persist live Z-test holdout splits.", "info");
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "⚡ Execute Controlled A/B Experiment";
                }
            }
        });
    }

    // Statistical Power Calculator Form
    const abPowerForm = document.getElementById("abPowerForm");

    async function computeAbPower() {
        const baseCvr = (parseFloat(document.getElementById("powerBaseCvr")?.value) || 4.5) / 100;
        const mdePct = parseFloat(document.getElementById("powerMdePct")?.value) || 10;
        const alpha = parseFloat(document.getElementById("powerAlphaSelect")?.value) || 0.05;
        const power = parseFloat(document.getElementById("powerTargetSelect")?.value) || 0.80;
        const dailyTraffic = parseInt(document.getElementById("powerDailyTraffic")?.value, 10) || 2500;
        const holdoutRatio = parseFloat(document.getElementById("powerHoldoutSplit")?.value) || 0.50;

        let powerData = null;
        try {
            const url = nexusApiUrl(`/api/v1/pricing/ab-test-calculator?baseline_conversion_rate=${baseCvr}&minimum_detectable_effect_pct=${mdePct}&alpha=${alpha}&power=${power}&daily_traffic=${dailyTraffic}&holdout_ratio=${holdoutRatio}`);
            const res = await fetch(url);
            if (res.ok) powerData = await res.json();
        } catch (err) {
            // Normal approximation fallback
            const p1 = baseCvr;
            const p2 = p1 * (1 + mdePct / 100);
            const nA = Math.ceil((15.6 * p1 * (1 - p1)) / Math.pow(p2 - p1, 2));
            const k = (1 - holdoutRatio) / holdoutRatio;
            const nB = Math.ceil(nA * k);
            powerData = {
                sample_size_control: nA,
                sample_size_variant: nB,
                total_sample_size: nA + nB,
                estimated_duration_days: Math.ceil((nA + nB) / dailyTraffic),
                power_curve: [0.25, 0.5, 0.75, 1.0, 1.25, 1.5].map(m => ({
                    total_visitors: Math.round((nA + nB) * m),
                    power_pct: Math.min(99, Math.round(power * 100 * Math.sqrt(m)))
                }))
            };
        }

        if (!powerData) return;
        const ctrlOut = document.getElementById("powerCtrlNOut");
        const varOut = document.getElementById("powerVarNOut");
        const totOut = document.getElementById("powerTotalNOut");
        const daysOut = document.getElementById("powerDaysOut");

        if (ctrlOut) ctrlOut.textContent = `${Number(powerData.sample_size_control).toLocaleString("en-IN")} visitors`;
        if (varOut) varOut.textContent = `${Number(powerData.sample_size_variant).toLocaleString("en-IN")} visitors`;
        if (totOut) totOut.textContent = `${Number(powerData.total_sample_size).toLocaleString("en-IN")} total`;
        if (daysOut) daysOut.textContent = `${powerData.estimated_duration_days} Days`;

        const powerCanvas = document.getElementById("abPowerCurveChart");
        if (powerCanvas && typeof Chart !== "undefined" && powerData.power_curve) {
            if (powerChartInstance) {
                powerChartInstance.destroy();
                powerChartInstance = null;
            }
            powerChartInstance = new Chart(powerCanvas, {
                type: "line",
                data: {
                    labels: powerData.power_curve.map(pt => `${(pt.total_visitors / 1000).toFixed(1)}k`),
                    datasets: [{
                        label: "Achieved Statistical Power (%)",
                        data: powerData.power_curve.map(pt => pt.power_pct),
                        borderColor: "#8B5CF6",
                        backgroundColor: "rgba(139, 92, 246, 0.16)",
                        fill: true,
                        tension: 0.3,
                        borderWidth: 2.5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { min: 0, max: 100, ticks: { callback: v => `${v}%` }, grid: { color: "rgba(255,255,255,0.06)" } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
    }

    if (abPowerForm) {
        abPowerForm.addEventListener("submit", (e) => {
            e.preventDefault();
            computeAbPower();
            showToast("Sample Size Computed", "Updated statistical power curve & duration estimate", "info");
        });
    }

    loadElasticityReport();
    computeAbPower();
}
