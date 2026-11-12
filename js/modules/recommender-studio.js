/**
 * Phase 31: Hybrid SVD Latent Factor Matrix Factorization & Next-Best-SKU Recommender Studio.
 * Loaded dynamically on demand by app.js module router.
 */

let RECOMMENDER_STUDIO_WIRED = false;
let CURRENT_EXPLAIN_CACHE = {};

function _fmtInr(val, decimals = 2) {
    const num = Number(val || 0);
    return "₹" + num.toLocaleString("en-IN", {
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

export async function refreshRecommenderDiagnostics() {
    const archEl = document.getElementById("svdArchVal");
    const varEl = document.getElementById("svdVarSub");
    const catEl = document.getElementById("svdCatalogVal");
    const custEl = document.getElementById("svdCustomerVal");
    const marginEl = document.getElementById("svdMarginVal");

    try {
        const res = await fetch(nexusApiUrl("/api/v1/recommend/stats"));
        if (!res.ok) return;
        const d = await res.json();

        if (archEl) archEl.textContent = `TruncatedSVD (k=${d.svd_latent_dimensions || 20})`;
        if (varEl) varEl.textContent = `${d.explained_variance_pct || 24.2}% Explained Variance`;
        if (catEl) catEl.textContent = `${(d.catalog_skus_indexed || 3360).toLocaleString()} SKUs`;
        if (custEl) custEl.textContent = `${(d.customer_profiles_indexed || 4330).toLocaleString()} Profiles`;
        if (marginEl) marginEl.textContent = `${d.avg_catalog_margin_pct || 46.3}%`;
    } catch (err) {
        console.warn("[Recommender Studio] Diagnostics fetch failed:", err);
    }
}

export async function refreshActiveRecommendations() {
    const modeSelect = document.getElementById("recModeSelect");
    const skuSelect = document.getElementById("skuSelect");
    const custSelect = document.getElementById("custSelect");
    const objSelect = document.getElementById("recObjectiveSelect");
    const titleEl = document.getElementById("recsTitle");
    const subEl = document.getElementById("recsSubtitle");
    const gridEl = document.getElementById("recsGrid");

    if (!modeSelect || !gridEl) return;

    const mode = modeSelect.value;
    const objective = objSelect ? objSelect.value : "balanced";
    const objLabel = objective === "margin_max" ? "Margin-Max (Profit Boost)" : (objective === "discovery" ? "Discovery & Latent Persona" : "Balanced Hybrid (Relevance + Margin)");

    gridEl.innerHTML = `<div class="recs-loading" style="padding: 2rem; text-align: center; color: var(--text-secondary); width: 100%;">
        <span class="loading-spinner"></span> Computing latent SVD factors & profit-weighted hybrid scores...
    </div>`;

    try {
        let endpoint = "";
        let headerTitle = "";
        let headerSub = "";

        if (mode === "item") {
            const sku = skuSelect ? skuSelect.value : "22423";
            endpoint = `/api/v1/recommend/item/${encodeURIComponent(sku)}?top_n=6`;
            headerTitle = `Frequently Bought Together with: [${_esc(sku)}]`;
            headerSub = `Derived via Sparse Item-Item Cosine Similarity & Cross-Sell Co-Purchase Frequencies.`;
        } else {
            const cid = custSelect ? custSelect.value : "17850";
            endpoint = `/api/v1/recommend/customer/${encodeURIComponent(cid)}?objective=${encodeURIComponent(objective)}&top_n=6`;
            headerTitle = `Next-Best-SKU Recommendations for Customer #${_esc(cid)}`;
            headerSub = `Powered by 20-Factor TruncatedSVD Latent Space + Collaborative Filtering + ${objLabel}.`;
        }

        const res = await fetch(nexusApiUrl(endpoint));
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const recs = data.recommendations || [];
        if (titleEl) {
            if (mode === "item" && data.query_description) {
                titleEl.textContent = `Frequently Bought Together with: [${data.query_stock_code}] ${data.query_description}`;
            } else {
                titleEl.textContent = headerTitle;
            }
        }
        if (subEl) subEl.textContent = headerSub;

        if (!recs.length) {
            gridEl.innerHTML = `<div class="text-muted" style="padding: 2rem; text-align: center; width: 100%;">No recommendations found for this selection.</div>`;
            return;
        }

        CURRENT_EXPLAIN_CACHE = {};
        gridEl.innerHTML = recs.map(item => {
            const sku = _esc(item.StockCode);
            const desc = _esc(item.Description);
            const cat = _esc(item.Category || "Merchandise");
            const priceInr = Number(item.UnitPriceINR || (item.UnitPrice * 105));
            const marginInr = Number(item.EstimatedUnitMarginINR || (priceInr * (item.GrossMarginRate || 0.42)));
            const badge = _esc(item.ExplanationBadge || (item.SimilarityScore ? `${Math.round(item.SimilarityScore * 100)}% Co-Purchase` : "Best Match"));
            const score = item.HybridScore ? `Score: ${Number(item.HybridScore).toFixed(3)}` : (item.SimilarityScore ? `Sim: ${Number(item.SimilarityScore).toFixed(3)}` : "");

            CURRENT_EXPLAIN_CACHE[sku] = item;

            return `
                <div class="rec-card modern-rec-card" data-sku="${sku}">
                    <div class="rec-card-top">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <span class="rec-sku">SKU: ${sku}</span>
                            <span class="rec-cat-pill">${cat}</span>
                        </div>
                        <h4 class="rec-title">${desc}</h4>
                    </div>
                    <div class="rec-card-bottom">
                        <div class="rec-price-row" style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:0.4rem;">
                            <div class="rec-price">${_fmtInr(priceInr)}</div>
                            <div class="rec-margin-tag" title="Calibrated Gross Unit Profit">Margin: <strong style="color:var(--accent-green);">${_fmtInr(marginInr)}</strong></div>
                        </div>
                        <div class="rec-meta-row" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                            <span class="rec-badge" style="font-size:0.72rem;">${badge}</span>
                            <span class="text-muted" style="font-size:0.72rem; font-family:var(--font-mono);">${score}</span>
                        </div>
                        <div style="display:flex; gap:0.4rem;">
                            <button type="button" class="btn btn-outline btn-xs add-cart-btn" style="flex:1;" data-sku="${sku}" data-desc="${desc}" data-price="${priceInr / 105}">+ Add to Basket</button>
                            <button type="button" class="btn btn-secondary btn-xs explain-sku-btn" data-sku="${sku}" title="Inspect SVD & Margin Attribution">🔬 Explain</button>
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        // Bind Add to Cart buttons
        gridEl.querySelectorAll(".add-cart-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const sku = btn.getAttribute("data-sku");
                const desc = btn.getAttribute("data-desc");
                const priceGbp = parseFloat(btn.getAttribute("data-price"));
                if (typeof window.addToCart === "function") {
                    window.addToCart(sku, desc, priceGbp);
                }
            });
        });

        // Bind Explain buttons
        gridEl.querySelectorAll(".explain-sku-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const sku = btn.getAttribute("data-sku");
                const item = CURRENT_EXPLAIN_CACHE[sku];
                if (item) {
                    showRecommendationExplanation(item);
                }
            });
        });

    } catch (err) {
        console.warn("[Recommender Studio] Failed to fetch live recommendations:", err);
        gridEl.innerHTML = `<div class="text-muted" style="padding: 1.5rem; color: var(--accent-red); width: 100%;">
            Error contacting Recommender API service. Please verify backend is running on port 8000.
        </div>`;
    }
}

export function showRecommendationExplanation(item) {
    const sku = _esc(item.StockCode);
    const desc = _esc(item.Description);
    const bd = item.ScoreBreakdown || {};
    const svd = Number(bd.svd_latent_affinity ?? 0.85);
    const cf = Number(bd.collaborative_cross_sell ?? 0.75);
    const margin = Number(bd.margin_contribution ?? 0.60);
    const cat = Number(bd.category_affinity ?? 0.70);

    const content = `
        <div style="padding: 0.5rem 0;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                <strong>[${sku}] ${desc}</strong>
                <span class="badge badge-primary">${_esc(item.ExplanationBadge || "Hybrid Match")}</span>
            </div>
            <p style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:1rem;">
                ${_esc(item.Explanation || "Recommended via mathematical convergence across 20 SVD latent dimensions and customer basket affinities.")}
            </p>
            <div style="display:flex; flex-direction:column; gap:0.6rem;">
                <div>
                    <div style="display:flex; justify-content:space-between; font-size:0.78rem; margin-bottom:0.2rem;">
                        <span>SVD Latent Persona Alignment:</span>
                        <strong>${(svd * 100).toFixed(1)}%</strong>
                    </div>
                    <div class="progress-bar-bg" style="height:6px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
                        <div style="width:${Math.round(svd * 100)}%; height:100%; background:var(--accent-blue);"></div>
                    </div>
                </div>
                <div>
                    <div style="display:flex; justify-content:space-between; font-size:0.78rem; margin-bottom:0.2rem;">
                        <span>Co-Purchase / Basket Collaborative Fit:</span>
                        <strong>${(cf * 100).toFixed(1)}%</strong>
                    </div>
                    <div class="progress-bar-bg" style="height:6px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
                        <div style="width:${Math.round(cf * 100)}%; height:100%; background:var(--accent-purple);"></div>
                    </div>
                </div>
                <div>
                    <div style="display:flex; justify-content:space-between; font-size:0.78rem; margin-bottom:0.2rem;">
                        <span>Profit Margin Contribution (${_fmtInr(item.EstimatedUnitMarginINR || 0)} unit margin):</span>
                        <strong>${(margin * 100).toFixed(1)}%</strong>
                    </div>
                    <div class="progress-bar-bg" style="height:6px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
                        <div style="width:${Math.round(margin * 100)}%; height:100%; background:var(--accent-green);"></div>
                    </div>
                </div>
                <div>
                    <div style="display:flex; justify-content:space-between; font-size:0.78rem; margin-bottom:0.2rem;">
                        <span>Category Preference Match (${_esc(item.Category || "Merchandise")}):</span>
                        <strong>${(cat * 100).toFixed(1)}%</strong>
                    </div>
                    <div class="progress-bar-bg" style="height:6px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
                        <div style="width:${Math.round(cat * 100)}%; height:100%; background:var(--accent-amber);"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (typeof window.showCustomModal === "function") {
        window.showCustomModal("🔬 SVD & Margin Attribution Scorecard", content);
    } else if (typeof window.showToast === "function") {
        window.showToast(item.ExplanationBadge || "SVD Match", item.Explanation || desc, "info");
    }
}

export async function scoreLiveCartWithBackend(cartItems, customerId = "17850") {
    const recsListEl = document.getElementById("basketRecsList");
    if (!recsListEl) return;

    if (!cartItems || !cartItems.length) {
        recsListEl.innerHTML = `<p class="text-muted" style="font-size:0.85rem; padding:1rem 0;">Add products to the basket to calculate composite vector affinities.</p>`;
        return;
    }

    const objSelect = document.getElementById("recObjectiveSelect");
    const objective = objSelect ? objSelect.value : "balanced";
    const cartSkus = cartItems.map(it => it.sku);

    try {
        const res = await fetch(nexusApiUrl("/api/v1/recommend/next-best-sku"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: customerId,
                current_cart_skus: cartSkus,
                objective: objective,
                top_n: 4,
            }),
        });

        if (!res.ok) return;
        const data = await res.json();
        const recs = data.recommendations || [];

        if (!recs.length) {
            recsListEl.innerHTML = `<p class="text-muted" style="font-size:0.85rem; padding:1rem 0;">No further complementary add-ons found.</p>`;
            return;
        }

        const liftInr = _fmtInr(data.projected_top2_margin_lift_inr || 0);
        recsListEl.innerHTML = `
            <div style="margin-bottom:0.6rem; font-size:0.78rem; color:var(--text-secondary); display:flex; justify-content:space-between; align-items:center;">
                <span>Projected Add-on Margin Lift:</span>
                <strong style="color:var(--accent-green); font-family:var(--font-mono);">${liftInr}</strong>
            </div>
            ${recs.map(r => `
                <div class="basket-rec-item" style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem; background:rgba(255,255,255,0.03); border-radius:6px; margin-bottom:0.4rem;">
                    <div style="flex:1; min-width:0; margin-right:0.5rem;">
                        <div style="font-weight:600; font-size:0.82rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${_esc(r.Description)}</div>
                        <div style="font-size:0.72rem; color:var(--text-secondary);">
                            <span class="text-primary font-mono">${_fmtInr(r.UnitPriceINR)}</span> · <span style="color:var(--accent-green);">${_esc(r.ExplanationBadge)}</span>
                        </div>
                    </div>
                    <button type="button" class="btn btn-outline btn-xs add-cart-btn" data-sku="${_esc(r.StockCode)}" data-desc="${_esc(r.Description)}" data-price="${(r.UnitPriceINR / 105).toFixed(2)}">+ Add</button>
                </div>
            `).join("")}
        `;

        recsListEl.querySelectorAll(".add-cart-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const sku = btn.getAttribute("data-sku");
                const desc = btn.getAttribute("data-desc");
                const price = parseFloat(btn.getAttribute("data-price"));
                if (typeof window.addToCart === "function") {
                    window.addToCart(sku, desc, price);
                }
            });
        });

    } catch (err) {
        console.warn("[Recommender Studio] Cart scoring failed:", err);
    }
}

export function initRecommenderStudio() {
    if (RECOMMENDER_STUDIO_WIRED) return;
    RECOMMENDER_STUDIO_WIRED = true;

    const modeSelect = document.getElementById("recModeSelect");
    const skuGroup = document.getElementById("skuSelectorGroup");
    const custGroup = document.getElementById("custSelectorGroup");
    const objGroup = document.getElementById("recObjectiveGroup");
    const skuSelect = document.getElementById("skuSelect");
    const custSelect = document.getElementById("custSelect");
    const objSelect = document.getElementById("recObjectiveSelect");

    function updateControlVisibility() {
        if (!modeSelect) return;
        const mode = modeSelect.value;
        if (mode === "item") {
            if (skuGroup) skuGroup.style.display = "flex";
            if (custGroup) custGroup.style.display = "none";
            if (objGroup) objGroup.style.display = "none";
        } else {
            if (skuGroup) skuGroup.style.display = "none";
            if (custGroup) custGroup.style.display = "flex";
            if (objGroup) objGroup.style.display = "flex";
        }
        refreshActiveRecommendations();
    }

    if (modeSelect) modeSelect.addEventListener("change", updateControlVisibility);
    if (skuSelect) skuSelect.addEventListener("change", refreshActiveRecommendations);
    if (custSelect) custSelect.addEventListener("change", refreshActiveRecommendations);
    if (objSelect) objSelect.addEventListener("change", refreshActiveRecommendations);

    // Patch global quickSelectSku to work with live backend
    window.quickSelectSku = function(sku) {
        if (modeSelect) modeSelect.value = "item";
        if (skuSelect) skuSelect.value = sku;
        updateControlVisibility();
        if (typeof window.showToast === "function") {
            window.showToast("Catalog SKU", `Loaded hybrid cross-sell for SKU [${sku}]`, "info");
        }
        if (typeof window.logAuditEvent === "function") {
            window.logAuditEvent("Recommender", `Quick-selected SKU [${sku}]`);
        }
    };

    // Hook into global cart updates so adding/removing items calls scoreLiveCartWithBackend
    const originalRenderCart = window.renderCart;
    if (typeof originalRenderCart === "function") {
        window.renderCart = function() {
            originalRenderCart.apply(this, arguments);
            const cartItems = window.CART_ITEMS || [];
            const custId = (custSelect ? custSelect.value : "17850") || "17850";
            scoreLiveCartWithBackend(cartItems, custId);
        };
    }

    updateControlVisibility();
    refreshRecommenderDiagnostics();
}

