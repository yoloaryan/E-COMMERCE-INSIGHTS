/**
 * Phase 33: Multi-Armed Bandit (MAB) Reinforcement Learning Studio
 * Loaded lazily on demand by app.js module router.
 */

let BANDIT_INITIALIZED = false;
let ACTIVE_BANDIT_ARMS = [];
let ACTIVE_SIM_DATA = null;

function _esc(v) {
    return String(v ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function _fmtInr(val) {
    return "₹" + Number(val || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export async function fetchBanditArms() {
    const tbody = document.getElementById("banditArmsTbody");
    try {
        const res = await fetch(nexusApiUrl("/api/v1/bandit/arms"));
        if (!res.ok) return;
        const data = await res.json();
        ACTIVE_BANDIT_ARMS = data.arms || [];
        renderBanditArmsTable(ACTIVE_BANDIT_ARMS);
    } catch (err) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--text-muted);padding:1rem;">Connect FastAPI backend (:8000) to inspect Bayesian Bandit arms.</td></tr>`;
        }
    }
}

export function renderBanditArmsTable(arms) {
    const tbody = document.getElementById("banditArmsTbody");
    if (!tbody || !Array.isArray(arms)) return;

    tbody.innerHTML = arms.map(arm => {
        const ci = arm.credible_interval_95 || [0, 1];
        const ciStr = `[${(ci[0] * 100).toFixed(1)}% — ${(ci[1] * 100).toFixed(1)}%]`;
        const sharePct = Number(arm.pull_share_pct || 0).toFixed(1);
        const crPct = (Number(arm.mean_conversion_rate || 0) * 100).toFixed(1);

        return `
            <tr>
                <th scope="row"><code>${_esc(arm.arm_id)}</code></th>
                <td data-label="Tier / Strategy"><strong>${_esc(arm.label)}</strong></td>
                <td data-label="Price Multiplier">${Number(arm.price_multiplier).toFixed(2)}x</td>
                <td data-label="Offered Price"><strong>${_fmtInr(arm.unit_price_inr)}</strong></td>
                <td data-label="Traffic Pulls">${Number(arm.pull_count || 0).toLocaleString("en-IN")} (${sharePct}%)</td>
                <td data-label="Conversions">${Number(arm.conversion_count || 0).toLocaleString("en-IN")}</td>
                <td data-label="Conversion Rate"><strong>${crPct}%</strong></td>
                <td data-label="95% Credible Interval"><small class="text-muted">${ciStr}</small></td>
                <td data-label="Expected Rev/Visitor"><strong style="color:var(--accent-green, #10B981);">${_fmtInr(arm.expected_revenue_per_visitor_inr)}</strong></td>
            </tr>
        `;
    }).join("");
}

export function renderRegretSvgChart(trajectory) {
    const container = document.getElementById("banditRegretChartContainer");
    if (!container || !trajectory || trajectory.length === 0) return;

    const width = 680;
    const height = 260;
    const padX = 65;
    const padY = 35;
    const plotW = width - padX - 25;
    const plotH = height - padY - 35;

    const maxRound = trajectory[trajectory.length - 1].round || 1000;
    const maxRegret = Math.max(
        ...trajectory.map(d => Math.max(d.cumulative_regret_ab || 0, d.cumulative_regret_mab || 0, d.cumulative_regret_egreedy || 0)),
        100
    );

    function getX(r) { return padX + (r / maxRound) * plotW; }
    function getY(reg) { return height - padY - (reg / maxRegret) * plotH; }

    const ptsMab = trajectory.map(d => `${getX(d.round).toFixed(1)},${getY(d.cumulative_regret_mab).toFixed(1)}`).join(" ");
    const ptsAb = trajectory.map(d => `${getX(d.round).toFixed(1)},${getY(d.cumulative_regret_ab).toFixed(1)}`).join(" ");
    const ptsEgreedy = trajectory.map(d => `${getX(d.round).toFixed(1)},${getY(d.cumulative_regret_egreedy).toFixed(1)}`).join(" ");

    const finalMab = trajectory[trajectory.length - 1].cumulative_regret_mab || 0;
    const finalAb = trajectory[trajectory.length - 1].cumulative_regret_ab || 0;

    container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" style="width:100%; height:auto; overflow:visible; font-family:var(--font-sans, sans-serif); filter:drop-shadow(0 2px 8px rgba(0,0,0,0.15));">
            <defs>
                <linearGradient id="mabGlow" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stop-color="#059669"/>
                    <stop offset="100%" stop-color="#10B981"/>
                </linearGradient>
            </defs>

            <!-- Background Chart Region -->
            <rect x="${padX}" y="${padY}" width="${plotW}" height="${plotH}" fill="rgba(15,23,42,0.25)" rx="6"/>

            <!-- Grid Lines -->
            <line x1="${padX}" y1="${height - padY}" x2="${width - 25}" y2="${height - padY}" stroke="rgba(255,255,255,0.16)" stroke-width="1"/>
            <line x1="${padX}" y1="${getY(maxRegret * 0.5)}" x2="${width - 25}" y2="${getY(maxRegret * 0.5)}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4,4"/>
            <line x1="${padX}" y1="${padY}" x2="${width - 25}" y2="${padY}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4,4"/>

            <!-- Y-Axis Labels -->
            <text x="${padX - 10}" y="${padY + 4}" fill="#94A3B8" font-size="11" font-weight="600" text-anchor="end">₹${Math.round(maxRegret / 1000)}k</text>
            <text x="${padX - 10}" y="${getY(maxRegret * 0.5) + 4}" fill="#94A3B8" font-size="11" text-anchor="end">₹${Math.round(maxRegret * 0.5 / 1000)}k</text>
            <text x="${padX - 10}" y="${height - padY + 4}" fill="#94A3B8" font-size="11" text-anchor="end">₹0</text>

            <!-- X-Axis Labels -->
            <text x="${padX}" y="${height - 12}" fill="#94A3B8" font-size="11" text-anchor="start">0</text>
            <text x="${padX + plotW * 0.5}" y="${height - 12}" fill="#94A3B8" font-size="11" text-anchor="middle">${Math.round(maxRound / 2)} Visits</text>
            <text x="${width - 25}" y="${height - 12}" fill="#94A3B8" font-size="11" text-anchor="end">${maxRound} Visits</text>

            <!-- Line Trajectories -->
            <!-- 1. Traditional A/B Test (High Linear Regret - Red Dashed) -->
            <polyline fill="none" stroke="#EF4444" stroke-width="2.5" stroke-dasharray="6,4" points="${ptsAb}"/>
            
            <!-- 2. Epsilon-Greedy (Decaying Exploration - Amber) -->
            <polyline fill="none" stroke="#F59E0B" stroke-width="2" points="${ptsEgreedy}"/>

            <!-- 3. MAB Selected Policy (Logarithmic / Sub-Linear - Emerald) -->
            <polyline fill="none" stroke="url(#mabGlow)" stroke-width="3.5" points="${ptsMab}"/>

            <!-- Final Markers & Badges -->
            <circle cx="${getX(maxRound)}" cy="${getY(finalMab)}" r="5" fill="#10B981" stroke="#FFFFFF" stroke-width="1.5"/>
            <text x="${getX(maxRound) - 8}" y="${getY(finalMab) - 8}" fill="#10B981" font-size="10" font-weight="700" text-anchor="end">MAB: ₹${Math.round(finalMab / 1000)}k</text>

            <circle cx="${getX(maxRound)}" cy="${getY(finalAb)}" r="4" fill="#EF4444"/>
            <text x="${getX(maxRound) - 8}" y="${getY(finalAb) - 8}" fill="#EF4444" font-size="10" font-weight="600" text-anchor="end">A/B: ₹${Math.round(finalAb / 1000)}k</text>
        </svg>
    `;
}

export function renderAllocationBarChart(trajectory) {
    const container = document.getElementById("banditAllocationChartContainer");
    if (!container || !trajectory || trajectory.length === 0) return;

    const lastStep = trajectory[trajectory.length - 1];
    const shares = lastStep.arm_allocation_shares || {};
    const armEntries = Object.entries(shares);

    const colors = ["#3B82F6", "#8B5CF6", "#10B981", "#EC4899", "#F59E0B"];

    container.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:0.65rem; padding:0.5rem 0;">
            ${armEntries.map(([armId, pct], idx) => {
                const color = colors[idx % colors.length];
                const armObj = ACTIVE_BANDIT_ARMS.find(a => a.arm_id === armId);
                const label = armObj ? armObj.label : armId;
                return `
                    <div>
                        <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.25rem;">
                            <span><strong>${_esc(label)}</strong> <code style="font-size:0.75rem;">(${_esc(armId)})</code></span>
                            <strong style="color:${color};">${pct}%</strong>
                        </div>
                        <div class="progress-bar-bg" style="height:8px; background:rgba(255,255,255,0.08); border-radius:4px; overflow:hidden;">
                            <div style="width:${pct}%; height:100%; background:${color}; border-radius:4px; transition:width 0.4s ease;"></div>
                        </div>
                    </div>
                `;
            }).join("")}
        </div>
    `;
}

export async function runBanditSimulation() {
    const btn = document.getElementById("btnRunBanditSim");
    const stratSel = document.getElementById("banditStrategySelect");
    const roundsSel = document.getElementById("banditRoundsSelect");
    const expSlider = document.getElementById("banditExplorationSlider");

    const strategy = stratSel ? stratSel.value : "thompson";
    const rounds = Number(roundsSel ? roundsSel.value : 1000);
    const factor = Number(expSlider ? expSlider.value : 1.0);

    if (btn) {
        btn.disabled = true;
        btn.textContent = "Simulating Arrivals…";
    }

    try {
        const res = await fetch(nexusApiUrl("/api/v1/bandit/simulate"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                rounds,
                strategy,
                exploration_factor: factor,
                seed: Math.floor(Math.random() * 10000),
            }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast("Simulation Failed", err.detail || `HTTP ${res.status}`, "alert");
            return;
        }

        const data = await res.json();
        ACTIVE_SIM_DATA = data;

        // Update Top KPI Cards
        const elRevMab = document.getElementById("banditKpiMabRevenue");
        const elRegretSaved = document.getElementById("banditKpiRegretSaved");
        const elWinner = document.getElementById("banditKpiWinnerArm");
        const elOracleRev = document.getElementById("banditKpiOracleRev");

        if (elRevMab) elRevMab.textContent = _fmtInr(data.total_revenue_mab_inr);
        if (elRegretSaved) elRegretSaved.textContent = `+${data.regret_saved_pct}% Saved`;
        if (elWinner) elWinner.textContent = data.oracle_best_label || data.oracle_best_arm;
        if (elOracleRev) elOracleRev.textContent = `Oracle Benchmark: ${_fmtInr(data.total_revenue_oracle_inr)} (vs A/B ${_fmtInr(data.total_revenue_ab_inr)})`;

        // Render SVG Regret Curves and Allocation distribution
        renderRegretSvgChart(data.trajectory);
        renderAllocationBarChart(data.trajectory);

        // Update table with simulation arm states
        if (data.final_mab_arms) {
            ACTIVE_BANDIT_ARMS = data.final_mab_arms;
            renderBanditArmsTable(ACTIVE_BANDIT_ARMS);
        }

        showToast(
            "MAB Simulation Complete",
            `${data.rounds_simulated} visits evaluated. Saved ${data.regret_saved_pct}% regret vs static A/B testing!`,
            "success"
        );
        logAuditEvent(
            "Bandit Simulation",
            `Simulated ${rounds} visits with ${strategy}. Saved ${data.regret_saved_pct}% regret.`
        );
    } catch (err) {
        showToast("Backend Error", "Could not execute bandit simulation.", "alert");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = "⚡ Run MAB Simulation";
        }
    }
}

let LAST_SELECTED_BANDIT_ARM = null;

export async function sampleLiveCustomerVisit() {
    const stratSel = document.getElementById("banditStrategySelect");
    const personaSel = document.getElementById("banditCustomerPersonaSelect");
    const resultBox = document.getElementById("banditVisitResultBox");

    const strategy = stratSel ? stratSel.value : "thompson";
    const persona = personaSel ? personaSel.value : "balanced";

    // Persona feature vectors: [intercept=1.0, recency_norm, log_spend_norm, cart_size_norm]
    const personaVectors = {
        loyal_whale: [1.0, 0.90, 0.95, 0.70],
        bargain_hunter: [1.0, 0.35, 0.25, 0.85],
        dormant_risk: [1.0, 0.10, 0.40, 0.20],
        guest_shopper: [1.0, 0.50, 0.30, 0.25],
        balanced: [1.0, 0.55, 0.60, 0.40],
    };

    const ctx = personaVectors[persona] || personaVectors.balanced;

    try {
        const res = await fetch(nexusApiUrl("/api/v1/bandit/select-arm"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                strategy,
                customer_context: ctx,
                exploration_factor: 1.0,
            }),
        });

        if (!res.ok) return;
        const d = await res.json();
        LAST_SELECTED_BANDIT_ARM = d;

        if (resultBox) {
            resultBox.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.6rem;">
                    <div>
                        <span class="badge-tag" style="background:#10B98122; color:#10B981; border:1px solid #10B981; font-size:0.75rem;">
                            ${d.is_exploration ? "🎲 Exploration Pull" : "🎯 Exploitation Winner"}
                        </span>
                        <h4 style="margin:0.25rem 0;">${_esc(d.arm_label)}</h4>
                        <small class="text-muted">Arm: <code>${_esc(d.selected_arm_id)}</code> &bull; Multiplier: ${d.price_multiplier}x</small>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.15rem; font-weight:700; color:var(--text-primary);">${_fmtInr(d.offered_price_inr)}</div>
                        <small class="text-muted">Exp. Rev: ${_fmtInr(d.expected_revenue_inr)}</small>
                    </div>
                </div>
                <p style="font-size:0.8rem; color:var(--text-secondary); margin:0 0 0.75rem 0; background:rgba(255,255,255,0.03); padding:0.4rem 0.6rem; border-radius:4px;">
                    💡 <em>${_esc(d.decision_reason)}</em>
                </p>
                <div style="display:flex; justify-content:flex-end; gap:0.5rem;">
                    <button type="button" class="btn btn-outline btn-xs" id="btnRewardBounce">❌ Customer Bounces (0 Rev)</button>
                    <button type="button" class="btn btn-primary btn-xs" id="btnRewardPurchase">✅ Customer Purchases (${_fmtInr(d.offered_price_inr)})</button>
                </div>
            `;

            // Wire reward feedback buttons
            const bounceBtn = document.getElementById("btnRewardBounce");
            const purchaseBtn = document.getElementById("btnRewardPurchase");

            if (bounceBtn) {
                bounceBtn.addEventListener("click", () => sendLiveReward(d.selected_arm_id, false, 0.0, ctx));
            }
            if (purchaseBtn) {
                purchaseBtn.addEventListener("click", () => sendLiveReward(d.selected_arm_id, true, d.offered_price_inr, ctx));
            }
        }
    } catch (_e) {
        showToast("Error", "Could not sample bandit decision.", "alert");
    }
}

async function sendLiveReward(armId, converted, revenue, context) {
    try {
        const res = await fetch(nexusApiUrl("/api/v1/bandit/reward"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                arm_id: armId,
                converted,
                revenue,
                customer_context: context,
            }),
        });

        if (!res.ok) return;
        const d = await res.json();
        showToast(
            converted ? "Reward Recorded (+Conversion)" : "Feedback Recorded (Bounce)",
            `Arm ${armId} updated: alpha=${d.alpha}, beta=${d.beta}, conversion=${(d.mean_conversion_rate * 100).toFixed(1)}%`,
            converted ? "success" : "info"
        );
        fetchBanditArms();
    } catch (_e) {
        showToast("Error", "Could not send reward update.", "alert");
    }
}

export function initBanditStudio() {
    if (BANDIT_INITIALIZED) return;
    BANDIT_INITIALIZED = true;

    fetchBanditArms();

    const simBtn = document.getElementById("btnRunBanditSim");
    const sampleBtn = document.getElementById("btnSampleBanditVisit");
    const resetBtn = document.getElementById("btnResetBandit");

    if (simBtn) simBtn.addEventListener("click", runBanditSimulation);
    if (sampleBtn) sampleBtn.addEventListener("click", sampleLiveCustomerVisit);

    if (resetBtn) {
        resetBtn.addEventListener("click", async () => {
            try {
                const res = await fetch(nexusApiUrl("/api/v1/bandit/reset"), {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                });
                if (res.ok) {
                    showToast("Priors Reset", "Bandit arms restored to uniform uninformative priors.", "success");
                    fetchBanditArms();
                }
            } catch (_e) {
                showToast("Error", "Could not reset bandit priors.", "alert");
            }
        });
    }

    // Run initial baseline simulation to populate charts
    runBanditSimulation();
}

