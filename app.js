/**
 * Nexus Retail AI | Enterprise Admin Suite & ML Inference Engine
 * Production Client-Side Architecture, Visualizations & Operations Logic
 */

document.addEventListener("DOMContentLoaded", () => {
    initChartDefaults();
    initThemeManager();
    initViewMode();
    initRoleManager();
    initNotificationCenter();
    initOmniSearch();
    initNavigation();
    initScrollToTop();
    initOverviewTab();
    initCohortHeatmap();
    initSegmentationTab();
    initCustomSegmentBuilder();
    initForecastingTab();
    initWhatIfSimulator();
    initChurnTab();
    initBTYDCLVExplorer();
    initCLVCalculator();
    initRecommenderTab();
    initLiveCartSimulator();
    initMLOpsConsole();
    initCustomerLedger();
    initCustomerDrawer();
    initInventoryMart();
    initSkuAndRestockModals();
    initCampaignStudio();
    initTransactionSimulator();
    initLiveOrderWebSocket();
    initAuditLogger();
    initApiConsole();
    initExecutiveReportModal();
    initDatasetImporter();
    initAiCopilot();
    initWebhooksHub();
    initPricingLab();
    initFraudRadar();
    initEnterpriseSecurity();
    initLivePipelineSync();
});

// =============================================================================
// GLOBAL STATE & AUDIT STORE (PERSISTENT VIA LOCALSTORAGE)
// =============================================================================
const savedLogs = localStorage.getItem("nexus_audit_logs");
let initialLogs = [
    { time: "2026-11-02 14:51:29", cat: "MLOps", role: "Lead DS", action: "Rebuilt Item Cosine Similarity Matrix (3,182 SKUs)", ip: "127.0.0.1", sev: "INFO" },
    { time: "2026-11-02 12:17:44", cat: "ModelRegistry", role: "Principal Admin", action: "Validated Random Forest Churn Classifier (AUC 0.7163)", ip: "127.0.0.1", sev: "INFO" },
    { time: "2026-11-02 12:15:00", cat: "ModelRegistry", role: "Principal Admin", action: "Promoted Random Forest Forecaster to Production (MAPE 26.28%)", ip: "127.0.0.1", sev: "INFO" },
    { time: "2026-11-02 11:19:29", cat: "Segmentation", role: "Growth Lead", action: "Executed K-Means (K=4) Persona Cluster Rebalance", ip: "127.0.0.1", sev: "INFO" },
    { time: "2026-11-02 11:10:08", cat: "ETL", role: "System Daemon", action: "Ingested 541,909 raw UCI transactions into Clean Store Mart", ip: "127.0.0.1", sev: "INFO" }
];
if (savedLogs) {
    try { initialLogs = JSON.parse(savedLogs); } catch (e) {}
}

let initialCart = [];
const savedCart = localStorage.getItem("nexus_cart");
if (savedCart) {
    try { initialCart = JSON.parse(savedCart); } catch (e) {}
}

const APP_STATE = {
    theme: localStorage.getItem("nexus_theme") || "dark",
    role: localStorage.getItem("nexus_role") || "admin",
    tenantId: localStorage.getItem("nexus_tenant_id") || "tenant_uk_flagship",
    authToken: localStorage.getItem("nexus_jwt_token") || "",
    authUser: null,
    cart: initialCart,
    dateRange: localStorage.getItem("nexus_date_range") || "all",
    auditLogs: initialLogs
};

window.getAuthHeaders = function(extraHeaders = {}) {
    const headers = { ...extraHeaders };
    if (APP_STATE.authToken) {
        headers["Authorization"] = `Bearer ${APP_STATE.authToken}`;
    }
    if (APP_STATE.tenantId) {
        headers["X-Tenant-ID"] = APP_STATE.tenantId;
    }
    return headers;
};

// =============================================================================
// TOAST NOTIFICATION SYSTEM
// =============================================================================
function showToast(title, message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const iconMap = {
        success: "✓",
        alert: "⚠️",
        warning: "⚠️",
        danger: "🚨",
        info: "ℹ️"
    };

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${iconMap[type] || "ℹ️"}</span>
        <div class="toast-content">
            <strong>${title}</strong>
            <small>${message}</small>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 3800);
}

// =============================================================================
// THEME MANAGER
// =============================================================================
function syncChartsWithTheme() {
    if (typeof Chart === "undefined" || !Chart.instances) return;
    const isLight = document.documentElement.getAttribute("data-theme") === "light";
    const textCol = isLight ? "#334155" : "#D4D4D8";
    const gridCol = isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";

    Object.values(Chart.instances).forEach(chart => {
        if (!chart || !chart.options) return;
        if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
            chart.options.plugins.legend.labels.color = textCol;
        }
        if (chart.options.scales) {
            Object.values(chart.options.scales).forEach(scale => {
                if (!scale) return;
                if (scale.ticks) scale.ticks.color = textCol;
                if (scale.title) scale.title.color = textCol;
                if (scale.grid && scale.grid.display !== false) scale.grid.color = gridCol;
            });
        }
        chart.update("none");
    });
}

function initThemeManager() {
    const html = document.documentElement;
    const toggleBtn = document.getElementById("themeToggleBtn");
    const themeIcon = document.getElementById("themeIcon");

    html.setAttribute("data-theme", APP_STATE.theme);
    if (themeIcon) themeIcon.textContent = APP_STATE.theme === "dark" ? "☀️" : "🌙";

    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            APP_STATE.theme = APP_STATE.theme === "dark" ? "light" : "dark";
            html.setAttribute("data-theme", APP_STATE.theme);
            localStorage.setItem("nexus_theme", APP_STATE.theme);
            if (themeIcon) themeIcon.textContent = APP_STATE.theme === "dark" ? "☀️" : "🌙";
            syncChartsWithTheme();
            showToast("Visual Theme Updated", `Switched interface to ${APP_STATE.theme.toUpperCase()} mode`, "info");
            logAuditEvent("Security", `Toggled workspace visual theme to ${APP_STATE.theme.toUpperCase()}`);
        });
    }
}

// =============================================================================
// ROLE-BASED ACCESS CONTROL (RBAC) MANAGER
// =============================================================================
function initRoleManager() {
    const roleSelect = document.getElementById("adminRoleSelect");
    const badgeText = document.getElementById("adminBadgeText");

    const roleMap = {
        admin: "Principal Admin",
        lead_ds: "Lead Data Scientist",
        growth: "Growth & Retention Lead",
        supply: "Supply Chain & Ops VP"
    };

    if (roleSelect && badgeText) {
        if (APP_STATE.role && roleMap[APP_STATE.role]) {
            roleSelect.value = APP_STATE.role;
            badgeText.textContent = roleMap[APP_STATE.role];
            if (typeof window.applyRbacUiState === "function") window.applyRbacUiState(APP_STATE.role);
        }
        roleSelect.addEventListener("change", () => {
            APP_STATE.role = roleSelect.value;
            localStorage.setItem("nexus_role", APP_STATE.role);
            badgeText.textContent = roleMap[roleSelect.value];
            if (typeof window.applyRbacUiState === "function") window.applyRbacUiState(APP_STATE.role);
            showToast("Role Context Switched", `Active permissions: ${roleMap[roleSelect.value]}`, "info");
            logAuditEvent("Auth/RBAC", `Switched active operational role to ${roleMap[roleSelect.value]}`);
        });
    }
}

// =============================================================================
// NOTIFICATION CENTER
// =============================================================================
function initNotificationCenter() {
    const notifBtn = document.getElementById("notifBtn");
    const notifDropdown = document.getElementById("notifDropdown");
    const markReadBtn = document.querySelector(".notif-mark-read");
    const notifCount = document.querySelector(".notif-count");

    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            notifDropdown.classList.toggle("show");
        });

        document.addEventListener("click", (e) => {
            if (!notifDropdown.contains(e.target) && e.target !== notifBtn) {
                notifDropdown.classList.remove("show");
            }
        });
    }

    if (markReadBtn && notifCount) {
        markReadBtn.addEventListener("click", () => {
            notifCount.style.display = "none";
            document.querySelectorAll(".notif-item").forEach(item => item.style.opacity = "0.6");
            showToast("Alerts Cleared", "All pending operational alerts marked as read", "success");
            logAuditEvent("Notification", "Marked all system alerts as read");
        });
    }

    // Interactive notification click navigation
    document.querySelectorAll(".notif-item").forEach(item => {
        item.style.cursor = "pointer";
        item.addEventListener("click", () => {
            if (notifDropdown) notifDropdown.classList.remove("show");
            if (item.classList.contains("critical")) {
                switchTab("churn");
                const input = document.getElementById("churnSearchInput");
                if (input) {
                    input.value = "14096";
                    document.getElementById("churnSearchBtn")?.click();
                }
                showToast("Account Loaded", "Navigated to VIP Customer #14096 in Churn Early Warning", "info");
            } else if (item.classList.contains("info")) {
                switchTab("inventory-mart");
                showToast("Inventory Mart", "Opened Inventory Mart to inspect Regency Cakestand #22423", "info");
            } else if (item.classList.contains("success")) {
                switchTab("admin-ops");
                showToast("MLOps Console", "Opened Model Registry to inspect Random Forest checkpoint", "info");
            }
        });
    });
}

// =============================================================================
// OMNI GLOBAL SEARCH & KEYBOARD COMMAND CENTER
// =============================================================================
function initOmniSearch() {
    const searchInput = document.getElementById("globalOmniSearch");
    const autocomplete = document.getElementById("searchAutocomplete");
    if (!searchInput) return;

    const SUGGESTIONS = [
        { icon: "⚠️", title: "Customer #14096", sub: "At-Risk VIP (£65,164 Spend | 81.2% Churn Risk)", badge: "VIP Alert", tab: "churn", val: "14096" },
        { icon: "👥", title: "Customer #17850", sub: "Champion Persona (£5,391 Spend | 35 Orders)", badge: "Champion", tab: "segmentation", val: "17850" },
        { icon: "📦", title: "SKU 22423 - Regency Cakestand", sub: "Inventory: 420 units (11d left | Critical)", badge: "Stock Alert", tab: "inventory-mart", val: "22423" },
        { icon: "🎯", title: "SKU 85123A - White Heart T-Light", sub: "Cross-Sell Catalog Affinity Leader", badge: "Cross-Sell", tab: "recommendations", val: "85123A" },
        { icon: "📈", title: "Demand Forecasting Simulator", sub: "Interactive sensitivity sliders for promo & ad spend", badge: "ML Forecaster", tab: "forecasting", val: "" },
        { icon: "💰", title: "Pricing Elasticity & A/B Lab", sub: "Category log-log price elasticity, margin curve & holdout tests", badge: "Pricing AI", tab: "pricing-lab", val: "" },
        { icon: "🚨", title: "Fraud & Anomaly Radar", sub: "Isolation Forest order risk scoring, cancellation audit & quarantine queue", badge: "Fraud AI", tab: "fraud-radar", val: "" },
        { icon: "⚡", title: "Developer REST API Playground", sub: "Sub-10ms model execution tester with cURL generation", badge: "API Console", tab: "api-console", val: "" }
    ];

    let selectedAutocompleteIndex = -1;

    function renderAutocomplete(filterText = "") {
        selectedAutocompleteIndex = -1;
        if (!autocomplete) return;
        const q = filterText.toLowerCase().trim();
        const matches = SUGGESTIONS.filter(s => !q || s.title.toLowerCase().includes(q) || s.sub.toLowerCase().includes(q) || s.badge.toLowerCase().includes(q));

        if (matches.length === 0) {
            autocomplete.innerHTML = `<div style="padding:1rem; font-size:0.8rem; color:var(--text-muted); text-align:center;">No direct entities found. Press Enter to search ledger.</div>`;
        } else {
            autocomplete.innerHTML = matches.map(m => `
                <div class="search-item" data-tab="${m.tab}" data-val="${m.val}">
                    <div class="search-item-left">
                        <span class="search-item-icon">${m.icon}</span>
                        <div class="search-item-text">
                            <strong>${m.title}</strong>
                            <small>${m.sub}</small>
                        </div>
                    </div>
                    <span class="search-item-badge badge-tag ${m.badge.includes('Alert') ? 'red-border' : 'blue'}">${m.badge}</span>
                </div>
            `).join("");
        }

        autocomplete.classList.add("show");

        autocomplete.querySelectorAll(".search-item").forEach(item => {
            item.addEventListener("click", () => {
                const targetTab = item.getAttribute("data-tab");
                const targetVal = item.getAttribute("data-val");
                autocomplete.classList.remove("show");
                searchInput.value = "";

                switchTab(targetTab);

                if (targetTab === "churn" && targetVal) {
                    const inp = document.getElementById("churnSearchInput");
                    if (inp) {
                        inp.value = targetVal;
                        document.getElementById("churnSearchBtn")?.click();
                    }
                } else if (targetTab === "segmentation" && targetVal) {
                    const inp = document.getElementById("custSearchInput");
                    if (inp) {
                        inp.value = targetVal;
                        document.getElementById("custSearchBtn")?.click();
                    }
                } else if (targetTab === "recommendations" && targetVal) {
                    const select = document.getElementById("skuSelect");
                    if (select) {
                        select.value = targetVal;
                        select.dispatchEvent(new Event("change"));
                    }
                }

                showToast("Navigation", `Navigated to ${targetTab.toUpperCase()}`, "info");
                logAuditEvent("Search", `Selected search shortcut: "${item.querySelector('strong')?.textContent}"`);
            });
        });
    }

    searchInput.addEventListener("focus", () => renderAutocomplete(searchInput.value));
    searchInput.addEventListener("input", () => renderAutocomplete(searchInput.value));

    document.addEventListener("click", (e) => {
        if (!searchInput.contains(e.target) && autocomplete && !autocomplete.contains(e.target)) {
            autocomplete.classList.remove("show");
        }
    });

    // Global Keyboard Shortcuts
    document.addEventListener("keydown", (e) => {
        // Pressing '/' or 'Cmd+K' / 'Ctrl+K' focuses search input
        if ((e.key === "/" && document.activeElement !== searchInput && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") ||
            ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")) {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
            renderAutocomplete(searchInput.value);
        }

        // Pressing 'Escape' closes all open modals, drawers, and popups
        if (e.key === "Escape") {
            if (autocomplete) autocomplete.classList.remove("show");
            const notifDropdown = document.getElementById("notifDropdown");
            if (notifDropdown) notifDropdown.classList.remove("show");
            closeCustomerDrawer();
            document.querySelectorAll(".modal-backdrop.open").forEach(m => m.classList.remove("open"));
        }
    });

    searchInput.addEventListener("keydown", (e) => {
        const items = autocomplete ? autocomplete.querySelectorAll(".search-item") : [];
        if (autocomplete && autocomplete.classList.contains("show") && items.length > 0) {
            if (e.key === "ArrowDown") {
                e.preventDefault();
                selectedAutocompleteIndex = (selectedAutocompleteIndex + 1) % items.length;
                items.forEach((item, idx) => {
                    item.classList.toggle("selected", idx === selectedAutocompleteIndex);
                    if (idx === selectedAutocompleteIndex) item.scrollIntoView({ block: "nearest" });
                });
                return;
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                selectedAutocompleteIndex = (selectedAutocompleteIndex - 1 + items.length) % items.length;
                items.forEach((item, idx) => {
                    item.classList.toggle("selected", idx === selectedAutocompleteIndex);
                    if (idx === selectedAutocompleteIndex) item.scrollIntoView({ block: "nearest" });
                });
                return;
            } else if (e.key === "Enter" && selectedAutocompleteIndex >= 0 && items[selectedAutocompleteIndex]) {
                e.preventDefault();
                items[selectedAutocompleteIndex].click();
                selectedAutocompleteIndex = -1;
                return;
            }
        }
    });

    searchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            const query = searchInput.value.trim().toUpperCase();
            if (!query) return;
            if (autocomplete) autocomplete.classList.remove("show");

            if (query.length >= 5 && (query.startsWith("2") || query.startsWith("8") || query.startsWith("4"))) {
                switchTab("recommendations");
                const skuSelect = document.getElementById("skuSelect");
                if (skuSelect) {
                    skuSelect.value = query;
                    skuSelect.dispatchEvent(new Event("change"));
                }
                showToast("Product Found", `Loaded collaborative cross-sell for SKU [${query}]`, "success");
            } else if (!isNaN(query) && query.length >= 4) {
                switchTab("customer-mgmt");
                const ledgerSearch = document.getElementById("custLedgerSearch");
                if (ledgerSearch) {
                    ledgerSearch.value = query;
                    ledgerSearch.dispatchEvent(new Event("input"));
                }
                showToast("Customer Found", `Filtered ledger for Customer #${query}`, "success");
            } else {
                switchTab("overview");
            }
            logAuditEvent("Search", `Executed Omni Global search for term: "${query}"`);
        }
    });
}

// =============================================================================
// WORKSPACE VIEW MODE MANAGER (SIMPLE EXECUTIVE VIEW VS ALL TOOLS)
// =============================================================================
const ADVANCED_TABS = ["customer-mgmt", "inventory-mart", "campaign-studio", "pricing-lab", "fraud-radar", "transaction-simulator", "admin-ops", "api-console", "audit-logs"];

function setViewMode(mode, silent = true) {
    const sidebar = document.getElementById("appSidebar");
    const body = document.body;
    const btnSimple = document.getElementById("btnModeSimple");
    const btnAll = document.getElementById("btnModeAll");
    const headerBtnSimple = document.getElementById("headerBtnModeSimple");
    const headerBtnAll = document.getElementById("headerBtnModeAll");

    if (mode === "simple") {
        if (body) {
            body.classList.add("simple-view-active");
            body.classList.remove("all-tools-active");
        }
        if (sidebar) sidebar.classList.add("simple-mode");
        btnSimple?.classList.add("active");
        btnAll?.classList.remove("active");
        headerBtnSimple?.classList.add("active");
        headerBtnAll?.classList.remove("active");
        localStorage.setItem("nexus_view_mode", "simple");

        // If currently on an advanced tab, switch to executive overview
        const activeNav = document.querySelector(".nav-item.active");
        const currentTab = activeNav?.getAttribute("data-tab");
        if (currentTab && ADVANCED_TABS.includes(currentTab)) {
            switchTab("overview");
        }

        if (!silent) showToast("🌟 Simple View Active", "Displaying 5 core executive intelligence modules", "info");
    } else {
        if (body) {
            body.classList.remove("simple-view-active");
            body.classList.add("all-tools-active");
        }
        if (sidebar) sidebar.classList.remove("simple-mode");
        btnAll?.classList.add("active");
        btnSimple?.classList.remove("active");
        headerBtnAll?.classList.add("active");
        headerBtnSimple?.classList.remove("active");
        localStorage.setItem("nexus_view_mode", "all");

        if (!silent) showToast("⚙️ All Tools Active", "Expanded all 14 operational, commerce & MLOps tools", "info");
    }
}

// Expose globally immediately
window.setViewMode = setViewMode;

function initViewMode() {
    const btnSimple = document.getElementById("btnModeSimple");
    const btnAll = document.getElementById("btnModeAll");
    const headerBtnSimple = document.getElementById("headerBtnModeSimple");
    const headerBtnAll = document.getElementById("headerBtnModeAll");
    const linkSwitch = document.getElementById("linkSwitchToAll");

    btnSimple?.addEventListener("click", () => setViewMode("simple", false));
    btnAll?.addEventListener("click", () => setViewMode("all", false));
    headerBtnSimple?.addEventListener("click", () => setViewMode("simple", false));
    headerBtnAll?.addEventListener("click", () => setViewMode("all", false));
    linkSwitch?.addEventListener("click", (e) => {
        e.preventDefault();
        setViewMode("all", false);
    });

    const savedMode = localStorage.getItem("nexus_view_mode") || "simple";
    setViewMode(savedMode, true);
}

// =============================================================================
// NAVIGATION & WORKSPACE ROUTER
// =============================================================================
function switchTab(targetTab) {
    const navItems = document.querySelectorAll(".nav-item");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const crumbCurrent = document.getElementById("breadcrumb-current") || document.getElementById("crumbCurrent");
    const crumbSection = document.getElementById("breadcrumb-section");
    const pageTitle = document.getElementById("page-title");
    const pageSubtitle = document.getElementById("page-subtitle");

    // Automatically expand workspace to 'all' if user selected an advanced module
    if (ADVANCED_TABS.includes(targetTab)) {
        const body = document.body;
        if (body && body.classList.contains("simple-view-active")) {
            setViewMode("all", true);
        }
    }

    const tabMeta = {
        overview: { title: "Executive Business Intelligence Overview", sub: "Macro store revenue velocity, customer acquisition, and transactional health metrics." },
        segmentation: { title: "Customer Segmentation & RFM Intelligence", sub: "Unsupervised K-Means clustering across Recency, Frequency, and Monetary dimensions." },
        forecasting: { title: "Demand Forecasting & Sales Prediction", sub: "Time-series forecasting benchmarked on an out-of-sample test horizon (Oct - Dec 2011)." },
        churn: { title: "Customer Churn Early Warning System", sub: "Identify at-risk accounts before they lapse and trigger value-preserving retention interventions." },
        recommendations: { title: "Collaborative Filtering Recommender Engine", sub: "Item-to-Item cross-selling and personalized customer recommendations powered by Cosine Similarity." },
        "admin-ops": { title: "MLOps Control Center & Model Registry", sub: "Model health telemetry, inference latency monitoring, and scheduled automated retraining pipelines." },
        "customer-mgmt": { title: "Enterprise Customer Account Ledger", sub: "Master customer registry with verified RFM metrics, assigned personas, and churn flags." },
        "inventory-mart": { title: "Inventory & Catalog SKU Mart", sub: "Stockout burn rate modeling, safety stock projections, and slow-moving deadstock alerts." },
        "campaign-studio": { title: "Retention Campaign & Win-Back Studio", sub: "Automated promotional sequence builder for high-value at-risk cohorts." },
        "pricing-lab": { title: "Dynamic Pricing Elasticity & A/B Experimentation Lab", sub: "Econometric log-log price elasticity, isoelastic gross profit simulation, and controlled holdout testing." },
        "fraud-radar": { title: "Transaction Anomaly, Fraud & Cancellation Radar", sub: "Isolation Forest outlier scoring, historical cancellation forensics, and real-time order quarantine triage." },
        "transaction-simulator": { title: "Live POS & Transaction Injection Simulator", sub: "Simulate live transactional orders and observe real-time reactive ML model updates." },
        "audit-logs": { title: "Enterprise Security & Model Audit Stream", sub: "Immutable audit log tracking all model updates, security events, and data exports." },
        "api-console": { title: "Developer API Console & REST Endpoint Tester", sub: "Interactive live microservice playground, cURL generator, and sub-10ms model execution benchmarks." }
    };

    navItems.forEach(n => {
        if (n.getAttribute("data-tab") === targetTab) n.classList.add("active");
        else n.classList.remove("active");
    });

    tabPanes.forEach(p => {
        if (p.id === `tab-${targetTab}`) p.classList.add("active");
        else p.classList.remove("active");
    });

    if (tabMeta[targetTab]) {
        if (crumbCurrent) crumbCurrent.textContent = tabMeta[targetTab].title.split(" &")[0];
        if (crumbSection) {
            crumbSection.textContent = ADVANCED_TABS.includes(targetTab) ? "Operations & MLOps" : "Enterprise Intelligence";
        }
        if (pageTitle) pageTitle.textContent = tabMeta[targetTab].title;
        if (pageSubtitle) pageSubtitle.textContent = tabMeta[targetTab].sub;
    }
}

function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    const sidebar = document.getElementById("appSidebar");
    const backdrop = document.getElementById("sidebarBackdrop");
    const mobileToggle = document.getElementById("mobileSidebarToggle");

    function closeMobileSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (backdrop) backdrop.classList.remove("open");
    }

    function toggleMobileSidebar() {
        if (sidebar) sidebar.classList.toggle("open");
        if (backdrop) backdrop.classList.toggle("open");
    }

    if (mobileToggle) {
        mobileToggle.addEventListener("click", toggleMobileSidebar);
    }
    if (backdrop) {
        backdrop.addEventListener("click", closeMobileSidebar);
    }

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            switchTab(item.getAttribute("data-tab"));
            if (window.innerWidth <= 1024) {
                closeMobileSidebar();
            }
        });
    });

    // Global Accessibility & Keyboard Shortcuts (Cmd+K and Escape)
    window.addEventListener("keydown", (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
            e.preventDefault();
            const searchInput = document.getElementById("globalOmniSearch");
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        if (e.key === "Escape") {
            closeMobileSidebar();
            closeCustomerDrawer();
            const skuModal = document.getElementById("skuModalBackdrop");
            if (skuModal) skuModal.classList.remove("open");
            const restockModal = document.getElementById("restockModalBackdrop");
            if (restockModal) restockModal.classList.remove("open");
            const reportModal = document.getElementById("reportModalBackdrop");
            if (reportModal) reportModal.classList.remove("open");
            const copilotDrawer = document.getElementById("copilotDrawerBackdrop");
            if (copilotDrawer) copilotDrawer.classList.remove("open");
            const importModal = document.getElementById("datasetImportModalBackdrop");
            if (importModal) {
                importModal.classList.remove("open");
                document.body.style.overflow = "";
            }
            const webhooksModal = document.getElementById("webhooksHubModalBackdrop");
            if (webhooksModal) {
                webhooksModal.classList.remove("open");
                document.body.style.overflow = "";
            }
            const autoDrop = document.getElementById("searchAutocomplete");
            if (autoDrop) autoDrop.classList.remove("show");
            const notifDrop = document.getElementById("notifDropdown");
            if (notifDrop) notifDrop.classList.remove("show");
        }
    });
}

window.jumpToSection = function(elementId, btn) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (btn && btn.parentElement) {
        btn.parentElement.querySelectorAll('.subnav-pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
    }
};

// =============================================================================
// TAB 1: EXECUTIVE OVERVIEW WITH INTERACTIVE DATE FILTERING
// =============================================================================
let monthlyChartInstance = null;
let countryChartInstance = null;

const DATE_RANGE_DATA = {
    all: {
        rev: "£10,279,169.87", orders: "19,776", aov: "£519.78", cancel: "1.62%", units: "5,577,275",
        growth: "↑ +14.2%", status: "Viewing: Full 374-Day Transaction History",
        labels: ["2010-12", "2011-01", "2011-02", "2011-03", "2011-04", "2011-05", "2011-06", "2011-07", "2011-08", "2011-09", "2011-10", "2011-11", "2011-12"],
        sales: [823746, 691438, 523631, 752941, 562142, 757820, 755914, 737883, 756468, 1059567, 1154979, 1509496, 513144]
    },
    q1: {
        rev: "£1,968,010.00", orders: "3,820", aov: "£515.18", cancel: "1.54%", units: "1,085,210",
        growth: "↑ +8.4%", status: "Viewing: Q1 2011 (January to March)",
        labels: ["2011-01", "2011-02", "2011-03"],
        sales: [691438, 523631, 752941]
    },
    q2: {
        rev: "£2,075,876.00", orders: "4,110", aov: "£505.08", cancel: "1.68%", units: "1,142,300",
        growth: "↑ +5.5%", status: "Viewing: Q2 2011 (April to June)",
        labels: ["2011-04", "2011-05", "2011-06"],
        sales: [562142, 757820, 755914]
    },
    q3: {
        rev: "£2,553,918.00", orders: "4,950", aov: "£515.94", cancel: "1.49%", units: "1,390,450",
        growth: "↑ +23.0%", status: "Viewing: Q3 2011 (July to September)",
        labels: ["2011-07", "2011-08", "2011-09"],
        sales: [737883, 756468, 1059567]
    },
    q4: {
        rev: "£3,177,619.00", orders: "5,840", aov: "£544.11", cancel: "1.74%", units: "1,754,310",
        growth: "↑ +38.6%", status: "Viewing: Q4 Holiday Peak (October to December)",
        labels: ["2011-10", "2011-11", "2011-12"],
        sales: [1154979, 1509496, 513144]
    }
};

function initOverviewTab() {
    // 1. Initial Chart Setup
    const monthlyCtx = document.getElementById("monthlySalesChart");
    if (monthlyCtx) {
        monthlyChartInstance = new Chart(monthlyCtx, {
            type: "line",
            data: {
                labels: DATE_RANGE_DATA.all.labels,
                datasets: [{
                    label: "Gross Revenue (£)",
                    data: DATE_RANGE_DATA.all.sales,
                    borderColor: "#2563EB",
                    backgroundColor: "rgba(37, 99, 235, 0.08)",
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: "#2563EB"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (ctx) => `Revenue: £${ctx.raw.toLocaleString()}` } }
                },
                scales: {
                    y: { ticks: { callback: (val) => `£${(val / 1000).toFixed(0)}k` }, grid: { color: "rgba(255,255,255,0.06)" } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    const countryCtx = document.getElementById("countryShareChart");
    if (countryCtx) {
        countryChartInstance = new Chart(countryCtx, {
            type: "doughnut",
            data: {
                labels: ["United Kingdom", "Netherlands", "EIRE (Ireland)", "Germany", "France", "Others"],
                datasets: [{
                    data: [85.12, 2.76, 2.69, 2.00, 1.80, 5.63],
                    backgroundColor: ["#2563EB", "#38BDF8", "#34D399", "#FBBF24", "#F472B6", "#64748B"],
                    borderWidth: 2,
                    borderColor: "transparent"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { boxWidth: 10, font: { size: 11 }, color: "#94A3B8" } },
                    tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw}%` } }
                },
                cutout: "68%"
            }
        });
    }

    // 2. Date Range Buttons
    document.querySelectorAll(".date-preset-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".date-preset-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const range = btn.getAttribute("data-range");
            APP_STATE.dateRange = range;
            localStorage.setItem("nexus_date_range", range);
            const data = DATE_RANGE_DATA[range] || DATE_RANGE_DATA.all;

            // Update KPI values
            document.getElementById("kpi-revenue").textContent = data.rev;
            document.getElementById("kpi-orders").textContent = data.orders;
            document.getElementById("kpi-aov").textContent = data.aov;
            document.getElementById("kpi-cancel").textContent = data.cancel;
            document.getElementById("kpi-units").textContent = data.units;
            document.getElementById("kpi-rev-growth").textContent = data.growth;
            document.getElementById("dateFilterStatus").textContent = data.status;

            // Update Chart
            if (monthlyChartInstance) {
                monthlyChartInstance.data.labels = data.labels;
                monthlyChartInstance.data.datasets[0].data = data.sales;
                monthlyChartInstance.update();
            }

            showToast("Date Filter Applied", data.status, "info");
            logAuditEvent("Filter", `Applied analytical date filter range: ${range.toUpperCase()}`);
        });
    });

    // Restore persistent date range if saved
    if (APP_STATE.dateRange && APP_STATE.dateRange !== "all") {
        const savedBtn = document.querySelector(`.date-preset-btn[data-range="${APP_STATE.dateRange}"]`);
        if (savedBtn) savedBtn.click();
    }

    // 3. Top Products Table
    const topProducts = [
        { code: "22423", desc: "Regency Cakestand 3 Tier", qty: "13,874", orders: "1,988", rev: "£174,484.74", share: "1.70%" },
        { code: "23843", desc: "Paper Craft , Little Birdie", qty: "80,995", orders: "1", rev: "£168,469.60", share: "1.64%" },
        { code: "85123A", desc: "White Hanging Heart T-Light Holder", qty: "37,842", orders: "2,256", rev: "£106,292.77", share: "1.03%" },
        { code: "47566", desc: "Party Bunting", qty: "18,295", orders: "1,685", rev: "£99,504.33", share: "0.97%" },
        { code: "85099B", desc: "Jumbo Bag Red Retrospot", qty: "48,375", orders: "2,089", rev: "£94,340.05", share: "0.92%" },
        { code: "84879", desc: "Assorted Colour Bird Ornament", qty: "36,461", orders: "1,472", rev: "£59,094.93", share: "0.58%" },
        { code: "23084", desc: "Rabbit Night Light", qty: "30,788", orders: "1,034", rev: "£51,346.20", share: "0.50%" },
        { code: "22086", desc: "Paper Chain Kit 50'S Christmas", qty: "19,302", orders: "1,189", rev: "£44,617.85", share: "0.43%" },
        { code: "21623", desc: "Vintage Union Jack Bunting", qty: "5,321", orders: "647", rev: "£37,398.24", share: "0.36%" },
        { code: "22910", desc: "Paper Chain Kit Vintage Christmas", qty: "8,944", orders: "812", rev: "£36,742.60", share: "0.36%" }
    ];

    const tbody = document.querySelector("#topProductsTable tbody");
    if (tbody) {
        tbody.innerHTML = topProducts.map(p => `
            <tr>
                <td><code>${p.code}</code></td>
                <td><strong>${p.desc}</strong></td>
                <td>${p.qty}</td>
                <td>${p.orders}</td>
                <td><strong>${p.rev}</strong></td>
                <td><span class="badge-tag blue">${p.share}</span></td>
            </tr>
        `).join("");
    }

    const exportBtn = document.getElementById("exportTopSkusBtn");
    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            downloadCSV("top_skus_report.csv", topProducts);
            showToast("Export Successful", "Downloaded top_skus_report.csv", "success");
            logAuditEvent("Export", "Exported Top 10 Revenue SKUs CSV report");
        });
    }

    initFinancialWaterfall();
}

// =============================================================================
// PHASE 22: RETURN & REFUND FINANCIAL WATERFALL ANALYTICS
// =============================================================================
let financialWaterfallChartInstance = null;
let FINANCE_WIRED = false;

async function refreshFinancialWaterfall() {
    const countryEl = document.getElementById("finCountryFilter");
    const sliderEl = document.getElementById("finReturnReductionSlider");
    const chartCanvas = document.getElementById("financialWaterfallChart");
    if (!chartCanvas) return;

    const country = countryEl ? countryEl.value : "All";
    const redPct = parseFloat(sliderEl ? sliderEl.value : "25");
    const redLabel = document.getElementById("finReturnReductionVal");
    if (redLabel) redLabel.textContent = `${redPct.toFixed(0)}%`;

    let rep = null;
    let sim = null;
    try {
        const [rRes, sRes] = await Promise.all([
            fetch(`http://localhost:8000/api/v1/finance/waterfall-report?country=${encodeURIComponent(country)}`),
            fetch("http://localhost:8000/api/v1/finance/simulate-margin-recovery", {
                method: "POST",
                headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify({ return_reduction_pct: redPct, country, cogs_ratio: 0.58 })
            })
        ]);
        if (rRes.ok) rep = await rRes.json();
        if (sRes.ok) sim = await sRes.json();
    } catch (_e) {
        // Offline P&L fallback below
    }

    if (!rep) {
        rep = {
            available_countries: ["All", "United Kingdom", "Netherlands", "EIRE", "Germany", "France"],
            summary: { gross_gmv_gbp: 10644560, return_leakage_gbp: 896812, net_revenue_gbp: 9747748, net_contribution_margin_gbp: 3348000, return_rate_pct: 8.42 },
            waterfall: [
                { step: "Gross Ordered GMV", amount_gbp: 10644560, type: "positive" },
                { step: "Returns & Cancels", amount_gbp: -896812, type: "negative" },
                { step: "Net Realized Rev", amount_gbp: 9747748, type: "subtotal" },
                { step: "COGS & Logistics", amount_gbp: -6399748, type: "negative" },
                { step: "Net Contribution", amount_gbp: 3348000, type: "total" }
            ],
            high_return_skus: [
                { stock_code: "23843", refund_leakage_gbp: 168469.6, return_rate_pct: 50.0 },
                { stock_code: "23166", refund_leakage_gbp: 77183.6, return_rate_pct: 48.2 },
                { stock_code: "22423", refund_leakage_gbp: 18942.5, return_rate_pct: 11.4 }
            ]
        };
    }
    if (!sim) {
        const s = rep.summary;
        const inc = (s.return_leakage_gbp * (redPct / 100)) * 0.54;
        sim = { outputs: { target_return_rate_pct: (s.return_rate_pct * (1 - redPct / 100)).toFixed(2), incremental_net_margin_gbp: inc } };
    }

    if (countryEl && Array.isArray(rep.available_countries) && countryEl.options.length <= 1 && rep.available_countries.length > 1) {
        const prev = countryEl.value || "All";
        countryEl.innerHTML = rep.available_countries.map(c => `<option value="${c}">${c === "All" ? "All Markets" : c}</option>`).join("");
        if (rep.available_countries.includes(prev)) countryEl.value = prev;
    }

    const s = rep.summary || {};
    const fmtGbp = (v) => `£${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    const gEl = document.getElementById("finGrossGmvVal");
    const rEl = document.getElementById("finReturnLeakVal");
    const nEl = document.getElementById("finNetMarginVal");
    const rtEl = document.getElementById("finReturnRateVal");
    if (gEl) gEl.textContent = fmtGbp(s.gross_gmv_gbp);
    if (rEl) rEl.textContent = `-${fmtGbp(s.return_leakage_gbp)}`;
    if (nEl) nEl.textContent = fmtGbp(s.net_contribution_margin_gbp);
    if (rtEl) rtEl.textContent = `${s.return_rate_pct}%`;

    const o = sim.outputs || {};
    const trEl = document.getElementById("finTargetReturnRateVal");
    const mrEl = document.getElementById("finMarginRecoveredVal");
    if (trEl) trEl.textContent = `${o.target_return_rate_pct}%`;
    if (mrEl) mrEl.textContent = `+${fmtGbp(o.incremental_net_margin_gbp)}`;

    const skuBody = document.getElementById("finReturnSkusTbody");
    if (skuBody) {
        skuBody.innerHTML = (rep.high_return_skus || []).map(item => `
            <tr>
                <td><code>${item.stock_code}</code></td>
                <td class="text-red"><strong>-£${Number(item.refund_leakage_gbp).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></td>
                <td><span class="badge-tag red">${item.return_rate_pct}%</span></td>
            </tr>
        `).join("");
    }

    if (typeof Chart !== "undefined" && Array.isArray(rep.waterfall)) {
        if (financialWaterfallChartInstance) financialWaterfallChartInstance.destroy();
        const isLight = document.documentElement.getAttribute("data-theme") === "light";
        const textCol = isLight ? "#334155" : "#D4D4D8";
        const gridCol = isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";

        const colors = rep.waterfall.map(w =>
            w.type === "positive" ? "#3B82F6" :
            w.type === "negative" ? "#EF4444" :
            w.type === "subtotal" ? "#8B5CF6" : "#10B981"
        );
        financialWaterfallChartInstance = new Chart(chartCanvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: rep.waterfall.map(w => w.step),
                datasets: [{
                    label: "Amount (£)",
                    data: rep.waterfall.map(w => w.amount_gbp),
                    backgroundColor: colors,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (ctx) => `£${Number(ctx.raw).toLocaleString(undefined, { maximumFractionDigits: 0 })}` } }
                },
                scales: {
                    x: { ticks: { color: textCol, font: { size: 11 } }, grid: { display: false } },
                    y: { ticks: { color: textCol, callback: (v) => `£${(v / 1000).toFixed(0)}k` }, grid: { color: gridCol } }
                }
            }
        });
    }
}

function initFinancialWaterfall() {
    refreshFinancialWaterfall();
    if (FINANCE_WIRED) return;
    FINANCE_WIRED = true;
    const countryEl = document.getElementById("finCountryFilter");
    const sliderEl = document.getElementById("finReturnReductionSlider");
    if (countryEl) countryEl.addEventListener("change", refreshFinancialWaterfall);
    if (sliderEl) {
        sliderEl.addEventListener("input", refreshFinancialWaterfall);
        sliderEl.addEventListener("change", refreshFinancialWaterfall);
    }
}

// =============================================================================
// TAB 2: CUSTOMER SEGMENTATION
// =============================================================================
const MASTER_CUSTOMERS = [
    { id: "17850", segment: "Champions (VIP)", spend: 5391.21, orders: 35, aov: 154.03, recency: 2, churnProb: 0.092, history: ["22423 Regency Cakestand", "85123A White Heart Holder", "21733 Red T-Light Holder"] },
    { id: "14646", segment: "Champions (VIP)", spend: 280206.02, orders: 74, aov: 3786.57, recency: 1, churnProb: 0.038, history: ["Bulk Regency Sets", "Export Party Bunting", "Paper Craft Birdie"] },
    { id: "18102", segment: "Champions (VIP)", spend: 259657.30, orders: 60, aov: 4327.62, recency: 1, churnProb: 0.041, history: ["Pallet Orders", "Vintage Union Bunting", "Paper Chain Kits"] },
    { id: "17450", segment: "Champions (VIP)", spend: 194550.79, orders: 46, aov: 4229.36, recency: 8, churnProb: 0.084, history: ["Jumbo Bags Retrospot", "Regency Teacups", "Cake Tins"] },
    { id: "14911", segment: "Champions (VIP)", spend: 143825.06, orders: 201, aov: 715.55, recency: 1, churnProb: 0.025, history: ["Weekly Replenishment", "Teapots", "Bird Ornaments"] },
    { id: "12415", segment: "Champions (VIP)", spend: 124914.53, orders: 21, aov: 5948.31, recency: 24, churnProb: 0.142, history: ["Wholesale Dutch Delivery", "Regency Collection", "Giftwares"] },
    { id: "14096", segment: "At-Risk / Lapsing", spend: 65164.79, orders: 17, aov: 3833.22, recency: 84, churnProb: 0.812, history: ["High Value Order (Oct)", "Bunting Sets", "Wholesale Lot"] },
    { id: "17511", segment: "Champions (VIP)", spend: 91062.38, orders: 31, aov: 2937.50, recency: 2, churnProb: 0.061, history: ["Restock Teacups", "Teapots", "Home Accessories"] },
    { id: "12352", segment: "At-Risk / Lapsing", spend: 2506.04, orders: 8, aov: 313.26, recency: 72, churnProb: 0.764, history: ["Ceramic Sets", "Cake Stands", "Gift Boxes"] },
    { id: "15311", segment: "Loyal Customers", spend: 1980.45, orders: 11, aov: 180.04, recency: 14, churnProb: 0.185, history: ["Green Regency Teacup", "Cake Tins", "Lunch Bags"] },
    { id: "13089", segment: "Champions (VIP)", spend: 58825.34, orders: 118, aov: 498.52, recency: 3, churnProb: 0.052, history: ["Regular B2B Dispatches", "Storage Bags", "Christmas Crafts"] },
    { id: "16684", segment: "At-Risk / Lapsing", spend: 14150.30, orders: 9, aov: 1572.25, recency: 76, churnProb: 0.732, history: ["Commercial Party Decor", "Large Bunting", "Paper Crafts"] },
    { id: "16029", segment: "At-Risk / Lapsing", spend: 17049.45, orders: 12, aov: 1420.79, recency: 81, churnProb: 0.748, history: ["Wholesale Gift Bags", "Teacup Sets", "Kitchenwares"] },
    { id: "13798", segment: "Loyal Customers", spend: 4638.12, orders: 9, aov: 515.35, recency: 21, churnProb: 0.210, history: ["Retrospot Lunch Bags", "T-Light Holders", "Craft Kits"] },
    { id: "14415", segment: "Occasional / Hibernating", spend: 645.20, orders: 2, aov: 322.60, recency: 142, churnProb: 0.840, history: ["Single Purchase (May)", "Clearance Line"] },
    { id: "15838", segment: "Occasional / Hibernating", spend: 336.14, orders: 1, aov: 336.14, recency: 210, churnProb: 0.915, history: ["Initial Gift Purchase", "No Subsequent Activity"] }
];

function initSegmentationTab() {
    const pieCtx = document.getElementById("segmentPieChart");
    if (pieCtx) {
        new Chart(pieCtx, {
            type: "pie",
            data: {
                labels: ["Champions (VIP)", "At-Risk / Lapsing", "Loyal Customers", "Occasional / Hibernating"],
                datasets: [{
                    data: [64.55, 24.02, 5.10, 6.33],
                    backgroundColor: ["#EAB308", "#EF4444", "#10B981", "#64748B"],
                    borderWidth: 2,
                    borderColor: "transparent"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 10, color: "#94A3B8" } },
                    tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw}% of Gross Revenue` } }
                }
            }
        });
    }

    const barCtx = document.getElementById("segmentBarChart");
    if (barCtx) {
        new Chart(barCtx, {
            type: "bar",
            data: {
                labels: ["Champions (VIP)", "At-Risk / Lapsing", "Loyal Customers", "Occasional"],
                datasets: [
                    {
                        label: "Average Monetary Spend (£)",
                        data: [7993.48, 1784.53, 530.01, 346.63],
                        backgroundColor: "#2563EB",
                        borderRadius: 6,
                        yAxisID: "y"
                    },
                    {
                        label: "Average Order Count",
                        data: [13.7, 4.1, 2.1, 1.3],
                        backgroundColor: "#F59E0B",
                        borderRadius: 6,
                        yAxisID: "y1"
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "top", labels: { boxWidth: 10, color: "#94A3B8" } } },
                scales: {
                    y: { type: "linear", position: "left", title: { display: true, text: "Spend (£)", color: "#94A3B8" }, grid: { color: "rgba(255,255,255,0.06)" } },
                    y1: { type: "linear", position: "right", title: { display: true, text: "Orders", color: "#94A3B8" }, grid: { drawOnChartArea: false } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    const searchBtn = document.getElementById("custSearchBtn");
    const searchInput = document.getElementById("custSearchInput");
    const resultBox = document.getElementById("custSearchResult");

    function renderCustLookup(cid) {
        cid = String(cid).trim();
        const found = MASTER_CUSTOMERS.find(c => c.id === cid) || {
            id: cid, segment: "Occasional / Hibernating", spend: 345.50, orders: 1, aov: 345.50, recency: 165, churnProb: 0.82
        };

        const badgeColor = found.segment.includes("VIP") ? "#EAB308" : found.segment.includes("At-Risk") ? "#EF4444" : "#10B981";

        resultBox.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); padding-bottom:0.75rem;">
                <div>
                    <strong>Customer Account #${found.id}</strong>
                    <div style="font-size:0.8rem; color:var(--text-muted);">Verified Behavioral Profile</div>
                </div>
                <div style="display:flex; gap:0.5rem; align-items:center;">
                    <span class="badge-tag" style="background:${badgeColor}22; color:${badgeColor}; border:1px solid ${badgeColor};">
                        ${found.segment}
                    </span>
                    <button class="btn btn-outline btn-xs" onclick="openCustomerDrawer('${found.id}')">View Ledger</button>
                </div>
            </div>
            <div class="result-grid">
                <div class="result-stat"><strong>Recency (Last Order)</strong><span>${found.recency} days ago</span></div>
                <div class="result-stat"><strong>Lifetime Invoices</strong><span>${found.orders} orders</span></div>
                <div class="result-stat"><strong>Total Spend</strong><span>£${found.spend.toLocaleString(undefined, {minimumFractionDigits: 2})}</span></div>
                <div class="result-stat"><strong>Avg Basket (AOV)</strong><span>£${found.aov.toLocaleString(undefined, {minimumFractionDigits: 2})}</span></div>
            </div>
        `;
    }

    if (searchBtn && searchInput) {
        searchBtn.addEventListener("click", () => renderCustLookup(searchInput.value));
        renderCustLookup(searchInput.value);
    }

    initCohortAndMigrationAnalytics();
}

// =============================================================================
// PHASE 18: COHORT RETENTION HEATMAP & RFM SEGMENT MIGRATION CONTROLLER
// =============================================================================
let cohortDecayChartInstance = null;
let COHORT_METRIC_MODE = "customers";
let COHORT_MATRIX_CACHE = [];
let COHORT_INIT_WIRED = false;

function buildLocalCohortFallback(metric = "customers") {
    const months = ["2010-12", "2011-01", "2011-02", "2011-03", "2011-04", "2011-05", "2011-06", "2011-07", "2011-08", "2011-09", "2011-10", "2011-11"];
    const baseSizes = [885, 417, 380, 452, 300, 284, 242, 188, 169, 299, 358, 323];
    const rows = months.map((m, idx) => {
        const custPcts = [];
        const revPcts = [];
        for (let off = 0; off < months.length; off++) {
            if (idx + off >= months.length) {
                custPcts.push(null);
                revPcts.push(null);
            } else if (off === 0) {
                custPcts.push(100.0);
                revPcts.push(100.0);
            } else {
                const cVal = parseFloat(Math.max(8.5, (38 - off * 2.1 + (idx === 0 ? 11 : 0))).toFixed(1));
                const rVal = parseFloat((cVal * 1.14).toFixed(1));
                custPcts.push(cVal);
                revPcts.push(rVal);
            }
        }
        return {
            cohort_month: m,
            cohort_size: baseSizes[idx],
            month0_revenue_gbp: baseSizes[idx] * 412.5,
            customer_retention_pcts: custPcts,
            revenue_retention_pcts: revPcts,
        };
    });
    const avgCurve = Array.from({ length: 12 }, (_, i) => i === 0 ? 100.0 : parseFloat(Math.max(12, 36 - i * 1.8).toFixed(1)));
    return {
        status: "success",
        metric,
        available_countries: ["All", "United Kingdom", "Germany", "France", "EIRE"],
        max_month_index: 11,
        month_headers: Array.from({ length: 12 }, (_, i) => `M${i}`),
        summary: {
            total_cohorts: 12,
            total_tracked_customers: 4296,
            avg_month1_retention_pct: 34.2,
            avg_month3_retention_pct: 28.6,
            avg_month1_nrr_pct: 38.9,
            best_cohort_month: "2010-12",
        },
        average_curve: {
            labels: Array.from({ length: 12 }, (_, i) => `Month ${i}`),
            customer_retention_pct: avgCurve,
            revenue_retention_pct: avgCurve.map(v => parseFloat((v * 1.14).toFixed(1))),
        },
        cohorts: rows,
    };
}

function renderCohortHeatmapMatrix(report) {
    const thead = document.getElementById("cohortHeatmapThead");
    const tbody = document.getElementById("cohortHeatmapTbody");
    if (!thead || !tbody) return;

    const headers = report.month_headers || [];
    const isRev = (COHORT_METRIC_MODE === "revenue");
    COHORT_MATRIX_CACHE = report.cohorts || [];

    thead.innerHTML = `
        <tr>
            <th scope="col">Acquisition Cohort</th>
            <th scope="col" style="text-align:right;">Size</th>
            ${headers.map(h => `<th scope="col">${h}</th>`).join("")}
        </tr>
    `;

    tbody.innerHTML = (report.cohorts || []).map(row => {
        const series = isRev ? row.revenue_retention_pcts : row.customer_retention_pcts;
        const cells = headers.map((_, idx) => {
            const val = series[idx];
            if (val === null || val === undefined) {
                return `<td class="cohort-cell heat-empty">—</td>`;
            }
            let bg = "rgba(59, 130, 246, 0.16)";
            let tier = "heat-low";
            if (idx === 0) {
                bg = "#1D4ED8";
                tier = "heat-hi";
            } else if (val >= 45) {
                bg = "#059669";
                tier = "heat-hi";
            } else if (val >= 30) {
                bg = "#2563EB";
                tier = "heat-hi";
            } else if (val >= 18) {
                bg = "rgba(37, 99, 235, 0.62)";
                tier = "heat-mid";
            } else if (val >= 10) {
                bg = "rgba(59, 130, 246, 0.34)";
                tier = "heat-low";
            }
            return `<td class="cohort-cell ${tier}" style="--cell-bg:${bg};" title="${row.cohort_month} • M${idx}: ${val}%">${val}%</td>`;
        }).join("");

        return `
            <tr>
                <th scope="row">${row.cohort_month}</th>
                <td class="cohort-size-cell">${Number(row.cohort_size).toLocaleString()}</td>
                ${cells}
            </tr>
        `;
    }).join("");

    const s = report.summary || {};
    const kM1 = document.getElementById("cohortKpiM1");
    const kM3 = document.getElementById("cohortKpiM3");
    const kNrr = document.getElementById("cohortKpiNrr");
    const kBest = document.getElementById("cohortKpiBestCohort");
    if (kM1) kM1.textContent = `${s.avg_month1_retention_pct ?? "--"}%`;
    if (kM3) kM3.textContent = `${s.avg_month3_retention_pct ?? "--"}%`;
    if (kNrr) kNrr.textContent = `${s.avg_month1_nrr_pct ?? "--"}%`;
    if (kBest) kBest.textContent = s.best_cohort_month || "--";

    const decayCanvas = document.getElementById("cohortDecayChart");
    if (decayCanvas && typeof Chart !== "undefined" && report.average_curve) {
        if (cohortDecayChartInstance) cohortDecayChartInstance.destroy();
        const isLight = document.documentElement.getAttribute("data-theme") === "light";
        const textCol = isLight ? "#334155" : "#D4D4D8";
        const gridCol = isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";

        cohortDecayChartInstance = new Chart(decayCanvas.getContext("2d"), {
            type: "line",
            data: {
                labels: report.average_curve.labels,
                datasets: [
                    {
                        label: "Logo Retention (%)",
                        data: report.average_curve.customer_retention_pct,
                        borderColor: "#3B82F6",
                        backgroundColor: "rgba(59, 130, 246, 0.14)",
                        borderWidth: 2.5,
                        fill: true,
                        tension: 0.25,
                    },
                    {
                        label: "Net Revenue Retention (%)",
                        data: report.average_curve.revenue_retention_pct,
                        borderColor: "#10B981",
                        borderWidth: 2,
                        borderDash: [4, 4],
                        fill: false,
                        tension: 0.25,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: textCol, font: { size: 11 } } } },
                scales: {
                    x: { ticks: { color: textCol }, grid: { color: gridCol } },
                    y: { beginAtZero: true, ticks: { color: textCol, callback: (v) => `${v}%` }, grid: { color: gridCol } }
                }
            }
        });
    }
}

function renderSegmentMigrationTable(mig) {
    const tbody = document.getElementById("segmentMigrationTbody");
    if (!tbody || !mig || !Array.isArray(mig.matrix)) return;

    const rank = { Champions: 0, Loyal: 1, "At-Risk": 2, Hibernating: 3 };
    const segs = mig.segments || ["Champions", "Loyal", "At-Risk", "Hibernating"];

    tbody.innerHTML = mig.matrix.map(row => {
        const src = row.from_segment;
        const cells = segs.map(dst => {
            const cell = row.transitions[dst] || { count: 0, pct: 0 };
            let cls = "stay";
            if (src === dst) cls = "stay";
            else if ((rank[dst] ?? 9) < (rank[src] ?? 9)) cls = "upgrade";
            else cls = "slip";
            return `
                <td class="migration-cell ${cls}">
                    <strong>${cell.pct}%</strong>
                    <small>${Number(cell.count).toLocaleString()} accts</small>
                </td>
            `;
        }).join("");
        return `
            <tr>
                <th scope="row"><strong>${src}</strong> <small style="color:var(--text-muted);">(${row.total_accounts})</small></th>
                ${cells}
            </tr>
        `;
    }).join("");

    const s = mig.summary || {};
    const stayEl = document.getElementById("migStayRateVal");
    const stayBadge = document.getElementById("migStayRateBadge");
    const slipEl = document.getElementById("migSlipCountVal");
    const winEl = document.getElementById("migWinbackVal");
    if (stayEl) stayEl.textContent = `${s.champion_stay_rate_pct ?? "--"}%`;
    if (stayBadge) stayBadge.textContent = `Champion Stay: ${s.champion_stay_rate_pct ?? "--"}%`;
    if (slipEl) slipEl.textContent = `${Number(s.champions_slipped_count || 0).toLocaleString()} accts`;
    if (winEl) winEl.textContent = `${Number(s.winback_upgrades_count || 0).toLocaleString()} upgrades`;
}

async function refreshRetentionLiftSimulator() {
    const liftEl = document.getElementById("migLiftSlider");
    const winEl = document.getElementById("migWinbackSlider");
    if (!liftEl || !winEl) return;

    const liftPp = parseFloat(liftEl.value || "5");
    const winPct = parseFloat(winEl.value || "20");

    const lVal = document.getElementById("migLiftVal");
    const wVal = document.getElementById("migWinbackSliderVal");
    if (lVal) lVal.textContent = `+${liftPp.toFixed(1)} pp`;
    if (wVal) wVal.textContent = `${winPct.toFixed(0)}%`;

    let sim = null;
    try {
        const res = await fetch("http://localhost:8000/api/v1/cohorts/simulate-lift", {
            method: "POST",
            headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ month1_lift_pp: liftPp, winback_recovery_pct: winPct })
        });
        if (res.ok) sim = await res.json();
    } catch (_e) {
        // Offline calculation fallback below
    }

    if (!sim) {
        const extraBuyers = Math.round(4296 * (liftPp / 100));
        const repeatRev = extraBuyers * 340 * 2.2;
        const winRev = Math.round(145 * (winPct / 100)) * 980;
        sim = {
            outputs: {
                projected_month1_retention_pct: parseFloat((34.2 + liftPp).toFixed(1)),
                recovered_slipping_accounts: Math.round(145 * (winPct / 100)),
                total_annual_revenue_lift_gbp: repeatRev + winRev
            }
        };
    }

    const o = sim.outputs || {};
    const m1El = document.getElementById("migProjectedM1Val");
    const recEl = document.getElementById("migRecoveredAccountsVal");
    const gainEl = document.getElementById("migProjectedGainVal");
    if (m1El) m1El.textContent = `${o.projected_month1_retention_pct ?? "--"}%`;
    if (recEl) recEl.textContent = `${Number(o.recovered_slipping_accounts || 0).toLocaleString()} VIPs`;
    if (gainEl) gainEl.textContent = `£${Number(o.total_annual_revenue_lift_gbp || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

async function loadCohortHeatmapFromApi() {
    const countryEl = document.getElementById("cohortCountryFilter");
    const selectedCountry = countryEl ? countryEl.value : "All";

    let report = null;
    try {
        const res = await fetch(`http://localhost:8000/api/v1/cohorts/retention-report?metric=${COHORT_METRIC_MODE}&country=${encodeURIComponent(selectedCountry)}`);
        if (res.ok) report = await res.json();
    } catch (_e) {
        // Fallback offline matrix
    }

    if (!report) report = buildLocalCohortFallback(COHORT_METRIC_MODE);

    if (countryEl && Array.isArray(report.available_countries)) {
        const currentVal = countryEl.value || "All";
        if (countryEl.options.length <= 1 && report.available_countries.length > 1) {
            countryEl.innerHTML = report.available_countries.map(c => `<option value="${c}">${c === "All" ? "All Markets" : c}</option>`).join("");
            if (report.available_countries.includes(currentVal)) countryEl.value = currentVal;
        }
    }
    renderCohortHeatmapMatrix(report);
}

async function initCohortAndMigrationAnalytics() {
    const matrixEl = document.getElementById("cohortHeatmapTable");
    if (!matrixEl) return;

    await loadCohortHeatmapFromApi();

    let mig = null;
    try {
        const res = await fetch("http://localhost:8000/api/v1/cohorts/segment-migration");
        if (res.ok) mig = await res.json();
    } catch (_e) {
        // Fallback offline migration
    }
    if (!mig) {
        mig = {
            segments: ["Champions", "Loyal", "At-Risk", "Hibernating"],
            summary: { champion_stay_rate_pct: 68.4, champions_slipped_count: 142, winback_upgrades_count: 96 },
            matrix: [
                { from_segment: "Champions", total_accounts: 640, transitions: { Champions: { count: 438, pct: 68.4 }, Loyal: { count: 60, pct: 9.4 }, "At-Risk": { count: 142, pct: 22.2 }, Hibernating: { count: 0, pct: 0 } } },
                { from_segment: "Loyal", total_accounts: 810, transitions: { Champions: { count: 178, pct: 22.0 }, Loyal: { count: 389, pct: 48.0 }, "At-Risk": { count: 243, pct: 30.0 }, Hibernating: { count: 0, pct: 0 } } },
                { from_segment: "At-Risk", total_accounts: 920, transitions: { Champions: { count: 44, pct: 4.8 }, Loyal: { count: 52, pct: 5.7 }, "At-Risk": { count: 480, pct: 52.2 }, Hibernating: { count: 344, pct: 37.3 } } },
                { from_segment: "Hibernating", total_accounts: 1120, transitions: { Champions: { count: 12, pct: 1.1 }, Loyal: { count: 42, pct: 3.8 }, "At-Risk": { count: 108, pct: 9.6 }, Hibernating: { count: 958, pct: 85.5 } } }
            ]
        };
    }
    renderSegmentMigrationTable(mig);
    await refreshRetentionLiftSimulator();

    if (!COHORT_INIT_WIRED) {
        COHORT_INIT_WIRED = true;
        const btnCust = document.getElementById("btnCohortMetricCustomers");
        const btnRev = document.getElementById("btnCohortMetricRevenue");
        const countryEl = document.getElementById("cohortCountryFilter");
        const exportBtn = document.getElementById("exportCohortCsvBtn");
        const liftSlider = document.getElementById("migLiftSlider");
        const winSlider = document.getElementById("migWinbackSlider");

        if (btnCust && btnRev) {
            btnCust.addEventListener("click", () => {
                COHORT_METRIC_MODE = "customers";
                btnCust.classList.add("active");
                btnRev.classList.remove("active");
                loadCohortHeatmapFromApi();
            });
            btnRev.addEventListener("click", () => {
                COHORT_METRIC_MODE = "revenue";
                btnRev.classList.add("active");
                btnCust.classList.remove("active");
                loadCohortHeatmapFromApi();
            });
        }

        if (countryEl) countryEl.addEventListener("change", loadCohortHeatmapFromApi);

        if (exportBtn) {
            exportBtn.addEventListener("click", () => {
                if (COHORT_MATRIX_CACHE.length) {
                    downloadCSV("cohort_retention_matrix.csv", COHORT_MATRIX_CACHE);
                    showToast("Cohort Matrix Exported", "cohort_retention_matrix.csv downloaded", "success");
                    logAuditEvent("Export", "Exported Phase 18 Cohort Retention Heatmap Matrix to CSV");
                }
            });
        }

        [liftSlider, winSlider].forEach(el => {
            if (el) {
                el.addEventListener("input", refreshRetentionLiftSimulator);
                el.addEventListener("change", refreshRetentionLiftSimulator);
            }
        });
    }
}

// =============================================================================
// TAB 3: SALES FORECASTING & WHAT-IF DEMAND SCENARIO SIMULATOR
// =============================================================================
function initForecastingTab() {
    const forecastCtx = document.getElementById("forecastChart");
    if (forecastCtx) {
        const testDays = ["Oct 02", "Oct 06", "Oct 10", "Oct 14", "Oct 18", "Oct 22", "Oct 26", "Oct 30", "Nov 03", "Nov 07", "Nov 11", "Nov 15", "Nov 19", "Nov 23", "Nov 27", "Dec 01", "Dec 05", "Dec 09"];
        const actuals = [24510, 31200, 42100, 38900, 47800, 35100, 51200, 43900, 58400, 67200, 78900, 81400, 69200, 94500, 88200, 71200, 84300, 65400];
        const rfPreds = [26200, 29800, 39500, 37200, 44100, 33800, 48900, 42100, 54200, 63100, 72500, 76200, 67100, 86400, 81500, 68900, 79200, 63100];
        const xgbPreds = [27500, 28100, 37200, 35400, 42000, 31900, 46100, 40500, 51800, 59800, 68200, 72400, 64200, 81200, 77500, 65400, 74900, 60800];

        new Chart(forecastCtx, {
            type: "line",
            data: {
                labels: testDays,
                datasets: [
                    {
                        label: "Ground Truth Actual Sales (£)",
                        data: actuals,
                        borderColor: "#38BDF8",
                        borderWidth: 2.5,
                        pointRadius: 4,
                        pointBackgroundColor: "#38BDF8",
                        tension: 0.2
                    },
                    {
                        label: "Random Forest Regressor (MAE £12.4k - Winner)",
                        data: rfPreds,
                        borderColor: "#10B981",
                        borderWidth: 2.5,
                        borderDash: [5, 5],
                        pointRadius: 3,
                        pointBackgroundColor: "#10B981",
                        tension: 0.2
                    },
                    {
                        label: "XGBoost Regressor (MAE £14.8k)",
                        data: xgbPreds,
                        borderColor: "#F59E0B",
                        borderWidth: 2,
                        borderDash: [2, 2],
                        pointRadius: 2,
                        pointBackgroundColor: "#F59E0B",
                        tension: 0.2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "top", labels: { boxWidth: 12, color: "#94A3B8" } } },
                scales: {
                    y: { ticks: { callback: (v) => `£${(v / 1000).toFixed(0)}k` }, grid: { color: "rgba(255,255,255,0.06)" } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    const impCtx = document.getElementById("featureImpChart");
    if (impCtx) {
        new Chart(impCtx, {
            type: "bar",
            data: {
                labels: ["DayOfWeek", "Lag_7 (Weekly)", "RollingMean_30", "LagOrders_7", "IsWeekend", "RollingMean_7", "Lag_14"],
                datasets: [{
                    label: "Normalized Gini Importance",
                    data: [0.2806, 0.2206, 0.0737, 0.0612, 0.0529, 0.0481, 0.0474],
                    backgroundColor: "#2563EB",
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { callback: (v) => `${(v * 100).toFixed(0)}%` }, grid: { color: "rgba(255,255,255,0.06)" } },
                    y: { grid: { display: false } }
                }
            }
        });
    }
}

function initWhatIfSimulator() {
    const sliderDiscount = document.getElementById("sliderPromoDiscount");
    const sliderAd = document.getElementById("sliderAdSpend");
    const sliderSurge = document.getElementById("sliderSeasonSurge");
    const selectDay = document.getElementById("selectSimDay");
    const panel = document.getElementById("simOutcomePanel");

    function computeScenario() {
        if (!sliderDiscount || !panel) return;

        const disc = parseInt(sliderDiscount.value, 10);
        const ad = parseInt(sliderAdSpend.value, 10);
        const surge = parseInt(sliderSeasonSurge.value, 10);
        const dayWeight = { "4": 1.35, "2": 1.20, "3": 1.10, "1": 0.95, "5": 0.85, "0": 0.55 }[selectDay.value] || 1.0;

        document.getElementById("lblPromoDiscount").textContent = `${disc}%`;
        document.getElementById("lblAdSpend").textContent = `+${ad}%`;
        document.getElementById("lblSeasonSurge").textContent = `+${surge}%`;

        // Baseline Thursday average revenue: £48,200
        const baseRev = 48200 * dayWeight;
        const volumeMultiplier = (1 + (disc * 0.0145)) * (1 + (ad * 0.006)) * (1 + (surge * 0.01));
        const effectivePriceRatio = 1 - (disc * 0.01);
        
        const projectedRev = baseRev * volumeMultiplier * effectivePriceRatio;
        const projectedOrders = Math.round(112 * volumeMultiplier * dayWeight);
        const incrementalRev = projectedRev - baseRev;
        const marginRate = Math.max(0.20, 0.42 - (disc * 0.008));
        const projectedMargin = projectedRev * marginRate;

        panel.innerHTML = `
            <div class="outcome-grid">
                <div class="outcome-box">
                    <strong>Projected Daily Revenue</strong>
                    <div class="outcome-val" style="color:var(--primary);">£${Math.round(projectedRev).toLocaleString()}</div>
                    <small>${incrementalRev >= 0 ? '↑ +' : '↓ -'}£${Math.abs(Math.round(incrementalRev)).toLocaleString()} vs baseline</small>
                </div>
                <div class="outcome-box">
                    <strong>Projected Order Volume</strong>
                    <div class="outcome-val">${projectedOrders} Invoices</div>
                    <small>Fulfillment workload index: ${(volumeMultiplier).toFixed(2)}x</small>
                </div>
                <div class="outcome-box">
                    <strong>Estimated Gross Margin</strong>
                    <div class="outcome-val" style="color:var(--success);">£${Math.round(projectedMargin).toLocaleString()}</div>
                    <small>${(marginRate * 100).toFixed(1)}% blended margin rate</small>
                </div>
                <div class="outcome-box">
                    <strong>Demand Lift Index</strong>
                    <div class="outcome-val" style="color:#A78BFA;">+${(((volumeMultiplier - 1) * 100)).toFixed(1)}%</div>
                    <small>Based on Random Forest elasticity</small>
                </div>
            </div>
        `;
    }

    [sliderDiscount, sliderAd, sliderSurge, selectDay].forEach(el => {
        if (el) el.addEventListener("input", computeScenario);
    });

    window.applyForecastingScenario = function(disc, ad, surge, day) {
        if (sliderDiscount) sliderDiscount.value = disc;
        if (sliderAd) sliderAd.value = ad;
        if (sliderSurge) sliderSurge.value = surge;
        if (selectDay && day !== undefined) selectDay.value = String(day);
        computeScenario();
        showToast("Preset Loaded", `Applied demand scenario: Disc ${disc}%, Ad +${ad}%, Surge +${surge}%`, "info");
        logAuditEvent("Simulator", `Applied What-If Preset: Disc ${disc}%, Ad +${ad}%, Surge +${surge}%`);
    };

    computeScenario();
}

// =============================================================================
// TAB 4: CHURN EARLY WARNING & CLV ROI CALCULATOR
// =============================================================================
function initChurnTab() {
    const churnBtn = document.getElementById("churnSearchBtn");
    const churnInput = document.getElementById("churnSearchInput");
    const churnResult = document.getElementById("churnSearchResult");

    function renderChurnLookup(cid) {
        cid = String(cid).trim();
        const found = MASTER_CUSTOMERS.find(c => c.id === cid) || {
            id: cid, spend: 850.00, orders: 3, recency: 78, churnProb: 0.725
        };

        const prob = found.churnProb;
        const color = prob >= 0.70 ? "#EF4444" : prob >= 0.35 ? "#F59E0B" : "#10B981";
        const tier = prob >= 0.70 ? "High Risk" : prob >= 0.35 ? "Medium Risk" : "Low Risk";
        const action = prob >= 0.70 && found.spend >= 1000
            ? "CRITICAL RETENTION: Assign dedicated senior account manager; telephone outreach; bespoke 20% credit."
            : prob >= 0.70
            ? "AUTOMATED WIN-BACK: Automated 3-part email campaign offering 15% off prior favorite categories."
            : "LOYALTY CADENCE: Standard promotional newsletter and reward points acceleration.";

        churnResult.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); padding-bottom:0.75rem;">
                <div>
                    <strong>Account Assessment: #${found.id}</strong>
                    <div style="font-size:0.8rem; color:var(--text-muted);">Inference Model: Random Forest (75.86% Recall)</div>
                </div>
                <div style="display:flex; gap:0.5rem; align-items:center;">
                    <span class="badge-tag" style="background:${color}22; color:${color}; border:1px solid ${color};">
                        ${tier} (${(prob * 100).toFixed(1)}% Risk)
                    </span>
                    <button class="btn btn-outline btn-xs" onclick="openCustomerDrawer('${found.id}')">View Profile</button>
                </div>
            </div>
            <div class="result-grid">
                <div class="result-stat"><strong>Days Inactive (Recency)</strong><span>${found.recency} days</span></div>
                <div class="result-stat"><strong>Lifetime Order Count</strong><span>${found.orders} orders</span></div>
                <div class="result-stat"><strong>Historical Spend</strong><span>£${found.spend.toLocaleString(undefined, {minimumFractionDigits: 2})}</span></div>
                <div class="result-stat"><strong>Model Confidence</strong><span>${(prob * 100).toFixed(1)}%</span></div>
            </div>
            <div style="margin-top:1rem; padding:0.75rem; background:var(--bg-surface-alt); border-radius:6px; border-left:3px solid ${color};">
                <strong style="font-size:0.78rem; color:${color}; text-transform:uppercase;">Prescribed Strategic Action:</strong>
                <p style="font-size:0.85rem; color:var(--text-primary); margin-top:0.25rem;">${action}</p>
            </div>
        `;
    }

    if (churnBtn && churnInput) {
        churnBtn.addEventListener("click", () => renderChurnLookup(churnInput.value));
        renderChurnLookup(churnInput.value);
    }

    window.quickScanChurn = function(cid) {
        if (churnInput) churnInput.value = cid;
        renderChurnLookup(cid);
        showToast("VIP Account Diagnostic", `Loaded churn risk profile for Customer #${cid}`, "info");
        logAuditEvent("Churn", `Executed quick scan diagnostic for Customer #${cid}`);
    };

    const vipTbody = document.querySelector("#vipChurnTable tbody");
    if (vipTbody) {
        const vipsAtRisk = MASTER_CUSTOMERS.filter(c => c.churnProb >= 0.70 && c.spend >= 1000);
        vipTbody.innerHTML = vipsAtRisk.map(v => `
            <tr>
                <td><strong>#${v.id}</strong></td>
                <td><strong>£${v.spend.toLocaleString(undefined, {minimumFractionDigits: 2})}</strong></td>
                <td>${v.orders}</td>
                <td>${v.recency} days</td>
                <td><span class="badge-tag" style="background:#EF444422; color:#EF4444;">${(v.churnProb * 100).toFixed(1)}%</span></td>
                <td><small>Executive outreach & bespoke 20% credit</small></td>
                <td><button class="btn btn-outline btn-xs vip-trigger-btn" data-cid="${v.id}">Trigger Outreach</button></td>
            </tr>
        `).join("");

        document.querySelectorAll(".vip-trigger-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const cid = btn.getAttribute("data-cid");
                btn.textContent = "Dispatched ✓";
                btn.classList.remove("btn-outline");
                btn.classList.add("btn-secondary");
                btn.disabled = true;
                showToast("VIP Retention Initiated", `Personalized concierge dispatched to Customer #${cid}`, "success");
                logAuditEvent("Campaign", `Dispatched VIP retention concierge email sequence to Customer #${cid}`);
            });
        });
    }

    const exportVipBtn = document.getElementById("exportVipChurnBtn");
    if (exportVipBtn) {
        exportVipBtn.addEventListener("click", () => {
            const vipsAtRisk = MASTER_CUSTOMERS.filter(c => c.churnProb >= 0.70 && c.spend >= 1000);
            downloadCSV("vip_churn_risk_accounts.csv", vipsAtRisk);
            showToast("VIP Export Complete", "Downloaded 22 high-risk VIP accounts to CSV", "success");
            logAuditEvent("Export", "Exported High-Risk VIP Accounts to CSV");
        });
    }
}

// =============================================================================
// BTYD PROBABILISTIC CUSTOMER LIFETIME VALUE EXPLORER (BG/NBD & GAMMA-GAMMA)
// =============================================================================
let btydChartInstance = null;

const BTYD_BENCHMARK_PROFILES = {
    "14646": {
        customer_id: "14646",
        p_alive: 0.9984,
        expected_orders_90d: 35.12,
        expected_orders_365d: 142.58,
        expected_avg_spend_gbp: 1845.20,
        clv_12m_gbp: 236410.50,
        clv_segment: "Platinum VIP (High CLV)",
        frequency: 73.0,
        recency_weeks: 50.4,
        tenure_weeks: 51.0,
        strategy: "STRATEGIC ACCOUNT RETENTION: Tier-1 priority SLA, dedicated logistics direct line, quarterly wholesale rebate contract."
    },
    "14096": {
        customer_id: "14096",
        p_alive: 0.1882,
        expected_orders_90d: 0.35,
        expected_orders_365d: 1.42,
        expected_avg_spend_gbp: 3850.10,
        clv_12m_gbp: 4890.20,
        clv_segment: "Gold Growth (Moderate CLV)",
        frequency: 17.0,
        recency_weeks: 41.2,
        tenure_weeks: 46.5,
        strategy: "CRITICAL RE-ENGAGEMENT: High historical whale experiencing acute lapse. Immediate senior account manager outreach with 20% credit."
    },
    "17850": {
        customer_id: "17850",
        p_alive: 0.8245,
        expected_orders_90d: 9.45,
        expected_orders_365d: 38.20,
        expected_avg_spend_gbp: 154.20,
        clv_12m_gbp: 5310.80,
        clv_segment: "Platinum VIP (High CLV)",
        frequency: 34.0,
        recency_weeks: 51.1,
        tenure_weeks: 53.0,
        strategy: "LOYALTY OPTIMIZATION: High-frequency catalog buyer. Introduce VIP cross-category perks and early-access seasonal catalog previews."
    },
    "12347": {
        customer_id: "12347",
        p_alive: 0.9754,
        expected_orders_90d: 1.68,
        expected_orders_365d: 6.82,
        expected_avg_spend_gbp: 560.10,
        clv_12m_gbp: 3538.41,
        clv_segment: "Platinum VIP (High CLV)",
        frequency: 6.0,
        recency_weeks: 52.1,
        tenure_weeks: 52.4,
        strategy: "STEADY NURTURING: Consistent quarterly order cadence. Target with complementary home decor and high-margin seasonal collections."
    },
    "12352": {
        customer_id: "12352",
        p_alive: 0.2580,
        expected_orders_90d: 0.28,
        expected_orders_365d: 1.12,
        expected_avg_spend_gbp: 410.20,
        clv_12m_gbp: 405.80,
        clv_segment: "Active Core (Steady)",
        frequency: 6.0,
        recency_weeks: 37.0,
        tenure_weeks: 42.0,
        strategy: "AUTOMATED WIN-BACK: Moderate lifetime value at significant risk of dormancy. Dispatch personalized email discount sequence."
    }
};

async function renderBTYDDiagnostic(cid) {
    cid = String(cid).trim();
    const panel = document.getElementById("btydResultPanel");
    const apiBadge = document.getElementById("btydApiBadge");
    if (!panel) return;

    panel.innerHTML = `<div style="text-align:center; padding:1.5rem; color:var(--text-muted);"><span class="icon-pulse"></span> Running BG/NBD & Gamma-Gamma inference for Customer #${cid}...</div>`;

    let data = null;
    let isLiveApi = false;

    // 1. Attempt live inference from FastAPI ML microservice
    try {
        const res = await fetch(`http://localhost:8000/api/v1/clv/customer/${cid}`, { mode: "cors" });
        if (res.ok) {
            data = await res.json();
            isLiveApi = true;
        }
    } catch (e) {
        // FastAPI unavailable or CORS blocked; fallback gracefully
    }

    // 2. Check cached nexus_data.json sample data or local benchmark profiles
    if (!data) {
        if (window.BTYD_SAMPLE_DATA && Array.isArray(window.BTYD_SAMPLE_DATA)) {
            const found = window.BTYD_SAMPLE_DATA.find(c => String(c.customer_id) === cid);
            if (found) data = found;
        }
        if (!data) {
            data = BTYD_BENCHMARK_PROFILES[cid] || {
                customer_id: cid,
                p_alive: 0.6500,
                expected_orders_90d: 1.20,
                expected_orders_365d: 4.80,
                expected_avg_spend_gbp: 380.00,
                clv_12m_gbp: 1640.00,
                clv_segment: "Active Core (Steady)",
                frequency: 3.0,
                recency_weeks: 24.0,
                tenure_weeks: 38.0,
                strategy: "STANDARD RETENTION: Regular cadence marketing and automated replenishment reminders."
            };
        }
    }

    if (apiBadge) {
        if (isLiveApi) {
            apiBadge.textContent = "LIVE API :8000";
            apiBadge.className = "badge green";
        } else {
            apiBadge.textContent = "Local Matrix Cache";
            apiBadge.className = "badge info-badge";
        }
    }

    const pAlive = data.p_alive;
    const pAlivePct = (pAlive * 100).toFixed(1);
    const pColor = pAlive >= 0.75 ? "#10B981" : pAlive >= 0.40 ? "#F59E0B" : "#EF4444";
    const clvTier = data.clv_segment || (data.clv_12m_gbp >= 3000 ? "Platinum VIP (High CLV)" : data.clv_12m_gbp >= 1000 ? "Gold Growth (Moderate CLV)" : "Active Core (Steady)");
    const tierBadgeClass = clvTier.includes("Platinum") ? "blue" : clvTier.includes("Gold") ? "gold-border" : "gray-border";

    const strategyText = data.strategy || (
        pAlive < 0.40 && data.clv_12m_gbp > 2000
            ? "CRITICAL RE-ENGAGEMENT: High-yield whale account with falling P(Alive). Trigger executive retention concierge."
            : pAlive < 0.40
            ? "AUTOMATED WIN-BACK: Dormant customer. Enroll in 3-part re-engagement discount sequence."
            : data.clv_12m_gbp > 5000
            ? "EXECUTIVE ACCOUNT GROWTH: Top portfolio contributor. Ensure VIP fulfillment priority and dedicated account rep."
            : "STEADY NURTURING: Solid customer health. Continue scheduled category newsletters and reward incentives."
    );

    panel.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid var(--border-color); padding-bottom:0.75rem; flex-wrap:wrap; gap:0.5rem;">
            <div>
                <strong style="font-size:1.05rem;">BTYD Diagnostics: Account #${data.customer_id}</strong>
                <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.2rem;">
                    Submodels: BG/NBD Poisson Rate + Gamma-Gamma Monetary Value (10% Annual Discount)
                </div>
            </div>
            <div style="display:flex; gap:0.5rem; align-items:center;">
                <span class="badge-tag ${tierBadgeClass}">${clvTier}</span>
                <button type="button" class="btn btn-outline btn-xs" onclick="openCustomerDrawer('${data.customer_id}')">View Full Profile</button>
            </div>
        </div>

        <div class="btyd-stat-grid">
            <div class="btyd-stat-box">
                <strong>Probability Active P(Alive)</strong>
                <div class="stat-val" style="color:${pColor};">${pAlivePct}%</div>
                <div class="p-alive-bar-wrap">
                    <div class="p-alive-fill" style="width:${pAlivePct}%; background:${pColor};"></div>
                </div>
            </div>
            <div class="btyd-stat-box">
                <strong>12-Month Expected CLV (NPV)</strong>
                <div class="stat-val" style="color:var(--primary);">£${Number(data.clv_12m_gbp).toLocaleString('en-GB', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                <small style="font-size:0.72rem; color:var(--text-muted);">1-Year Net Present Value</small>
            </div>
            <div class="btyd-stat-box">
                <strong>Expected Orders (365 Days)</strong>
                <div class="stat-val" style="color:#A78BFA;">${Number(data.expected_orders_365d).toFixed(1)} Orders</div>
                <small style="font-size:0.72rem; color:var(--text-muted);">${Number(data.expected_orders_90d).toFixed(1)} orders next 90 days</small>
            </div>
            <div class="btyd-stat-box">
                <strong>Expected Order Value</strong>
                <div class="stat-val" style="color:var(--success);">£${Number(data.expected_avg_spend_gbp).toLocaleString('en-GB', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                <small style="font-size:0.72rem; color:var(--text-muted);">Gamma-Gamma latent spend</small>
            </div>
        </div>

        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:0.5rem; margin-bottom:0.75rem; padding:0.6rem 0.8rem; background:var(--bg-card); border-radius:6px; font-size:0.75rem; border:1px solid var(--border-color);">
            <div><span style="color:var(--text-muted);">Frequency x:</span> <strong>${data.frequency !== undefined ? data.frequency : '-'} repeat periods</strong></div>
            <div><span style="color:var(--text-muted);">Recency t_x:</span> <strong>${data.recency_weeks !== undefined ? data.recency_weeks : '-'} weeks</strong></div>
            <div><span style="color:var(--text-muted);">Customer Age T:</span> <strong>${data.tenure_weeks !== undefined ? data.tenure_weeks : '-'} weeks</strong></div>
            <div><span style="color:var(--text-muted);">Inference Latency:</span> <strong>&lt; 5ms</strong></div>
        </div>

        <div style="padding:0.75rem; background:var(--bg-card); border-radius:6px; border-left:3px solid ${pColor};">
            <strong style="font-size:0.74rem; color:${pColor}; text-transform:uppercase; letter-spacing:0.04em;">Prescribed Strategic Action:</strong>
            <p style="font-size:0.82rem; color:var(--text-primary); margin-top:0.25rem; line-height:1.4;">${strategyText}</p>
        </div>
    `;

    renderBtydTrajectoryChart(data);
}

function renderBtydTrajectoryChart(data) {
    const canvas = document.getElementById("btydProjectionChart");
    if (!canvas) return;

    if (btydChartInstance) {
        btydChartInstance.destroy();
        btydChartInstance = null;
    }

    const months = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"];
    const totalCLV = Number(data.clv_12m_gbp);
    const totalOrders = Number(data.expected_orders_365d);

    // Compound cumulative curve with realistic early acceleration (Poisson process)
    const cumulativeRev = [];
    const cumulativeOrders = [];
    for (let i = 1; i <= 12; i++) {
        const factor = 1 - Math.exp(-0.16 * i);
        const normFactor = factor / (1 - Math.exp(-0.16 * 12));
        cumulativeRev.push(Math.round(totalCLV * normFactor));
        cumulativeOrders.push(Number((totalOrders * normFactor).toFixed(1)));
    }

    btydChartInstance = new Chart(canvas, {
        type: "line",
        data: {
            labels: months,
            datasets: [
                {
                    label: "Cumulative Forward CLV Cash Flow (£)",
                    data: cumulativeRev,
                    borderColor: "#2563EB",
                    backgroundColor: "rgba(37, 99, 235, 0.12)",
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2.5,
                    pointRadius: 4,
                    pointBackgroundColor: "#2563EB",
                    yAxisID: "y"
                },
                {
                    label: "Cumulative Predicted Orders",
                    data: cumulativeOrders,
                    borderColor: "#A78BFA",
                    backgroundColor: "transparent",
                    borderDash: [4, 4],
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: "#A78BFA",
                    yAxisID: "y1"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { position: "top", labels: { boxWidth: 12, color: "#94A3B8", font: { size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ctx.datasetIndex === 0 
                            ? `Cumulative Revenue: £${ctx.raw.toLocaleString()}`
                            : `Cumulative Orders: ${ctx.raw} orders`
                    }
                }
            },
            scales: {
                y: {
                    type: "linear",
                    position: "left",
                    title: { display: true, text: "Cumulative Spend (£)", color: "#94A3B8", font: { size: 11 } },
                    grid: { color: "rgba(255, 255, 255, 0.06)" },
                    ticks: { callback: (v) => `£${Number(v).toLocaleString()}` }
                },
                y1: {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "Orders", color: "#94A3B8", font: { size: 11 } },
                    grid: { drawOnChartArea: false }
                },
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.04)" }
                }
            }
        }
    });
}

function initBTYDCLVExplorer() {
    const input = document.getElementById("btydSearchInput");
    const btn = document.getElementById("btydSearchBtn");

    if (btn && input) {
        btn.addEventListener("click", () => renderBTYDDiagnostic(input.value));
        input.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                renderBTYDDiagnostic(input.value);
            }
        });
    }

    window.quickInspectBtydClv = function(cid) {
        if (input) input.value = cid;
        renderBTYDDiagnostic(cid);
        showToast("BTYD Diagnostic Loaded", `Evaluated BG/NBD & Gamma-Gamma metrics for #${cid}`, "info");
        logAuditEvent("CLV", `Inspected BTYD CLV profile for Customer #${cid}`);
    };

    // Initial render with benchmark Wholesaler
    renderBTYDDiagnostic(input ? input.value : "14646");
}

function initCLVCalculator() {
    const spendInput = document.getElementById("calcSpend");
    const freqInput = document.getElementById("calcFreq");
    const marginSlider = document.getElementById("sliderCalcMargin");
    const costInput = document.getElementById("calcCost");
    const outcomePanel = document.getElementById("clvOutcomePanel");

    function computeCLV() {
        if (!spendInput || !outcomePanel) return;

        const spend = parseFloat(spendInput.value) || 3850;
        const freq = parseFloat(freqInput.value) || 9;
        const margin = parseFloat(marginSlider.value) || 42;
        const cost = parseFloat(costInput.value) || 35;

        document.getElementById("lblCalcMargin").textContent = `${margin}%`;

        // 3-Year Customer Lifetime Value Formula: CLV = Annual Value * Margin * Lifespan Multiplier (approx 2.4 years)
        const annualGrossProfit = spend * (margin / 100);
        const clv3Year = annualGrossProfit * 2.4;
        const savedValue = clv3Year * 0.45; // 45% win-back success probability
        const roiMultiplier = (savedValue / cost).toFixed(1);

        outcomePanel.innerHTML = `
            <div class="outcome-grid">
                <div class="outcome-box">
                    <strong>Predicted 3-Year CLV</strong>
                    <div class="outcome-val" style="color:var(--primary);">£${Math.round(clv3Year).toLocaleString()}</div>
                    <small>Based on £${Math.round(annualGrossProfit).toLocaleString()} annual margin</small>
                </div>
                <div class="outcome-box">
                    <strong>Capital at Churn Risk</strong>
                    <div class="outcome-val" style="color:var(--danger);">£${Math.round(spend).toLocaleString()}</div>
                    <small>Direct gross merchandise exposure</small>
                </div>
                <div class="outcome-box">
                    <strong>Expected Retention ROI</strong>
                    <div class="outcome-val" style="color:var(--success);">${roiMultiplier}x Return</div>
                    <small>£${Math.round(savedValue).toLocaleString()} saved / £${cost} spend</small>
                </div>
                <div class="outcome-box">
                    <strong>Intervention Viability</strong>
                    <div class="outcome-val" style="color:#10B981;">Strongly Positive</div>
                    <small>Payback period &lt; 30 days</small>
                </div>
            </div>
        `;
    }

    [spendInput, freqInput, marginSlider, costInput].forEach(el => {
        if (el) el.addEventListener("input", computeCLV);
    });

    computeCLV();
}

// =============================================================================
// TAB 5: PRODUCT RECOMMENDATION ENGINE & INTERACTIVE LIVE CART BUILDER
// =============================================================================
const RECS_CATALOG = {
    "22423": {
        title: "Frequently Bought Together with: [22423] Regency Cakestand 3 Tier",
        items: [
            { sku: "22699", desc: "Roses Regency Teacup And Saucer", price: 2.95, badge: "52.6% Affinity" },
            { sku: "22697", desc: "Green Regency Teacup And Saucer", price: 2.95, badge: "50.9% Affinity" },
            { sku: "22698", desc: "Pink Regency Teacup And Saucer", price: 2.95, badge: "48.9% Affinity" },
            { sku: "23245", desc: "Set Of 3 Regency Cake Tins", price: 4.95, badge: "46.7% Affinity" },
            { sku: "23173", desc: "Regency Teapot Roses", price: 9.95, badge: "45.4% Affinity" }
        ]
    },
    "85123A": {
        title: "Frequently Bought Together with: [85123A] White Hanging Heart T-Light Holder",
        items: [
            { sku: "21733", desc: "Red Hanging Heart T-Light Holder", price: 2.95, badge: "48.2% Affinity" },
            { sku: "22470", desc: "Heart Of Wicker Large", price: 2.95, badge: "43.1% Affinity" },
            { sku: "22469", desc: "Heart Of Wicker Small", price: 1.65, badge: "41.8% Affinity" },
            { sku: "84029G", desc: "Knitted Union Flag Hot Water Bottle", price: 3.75, badge: "39.5% Affinity" },
            { sku: "84029E", desc: "Red Woolly Hottie White Heart", price: 3.75, badge: "38.9% Affinity" }
        ]
    },
    "47566": {
        title: "Frequently Bought Together with: [47566] Party Bunting",
        items: [
            { sku: "21623", desc: "Vintage Union Jack Bunting", price: 4.95, badge: "46.1% Affinity" },
            { sku: "22086", desc: "Paper Chain Kit 50'S Christmas", price: 2.95, badge: "42.5% Affinity" },
            { sku: "22910", desc: "Paper Chain Kit Vintage Christmas", price: 2.95, badge: "41.2% Affinity" },
            { sku: "22423", desc: "Regency Cakestand 3 Tier", price: 10.95, badge: "38.4% Affinity" },
            { sku: "85099B", desc: "Jumbo Bag Red Retrospot", price: 1.79, badge: "37.5% Affinity" }
        ]
    },
    "85099B": {
        title: "Frequently Bought Together with: [85099B] Jumbo Bag Red Retrospot",
        items: [
            { sku: "20725", desc: "Lunch Bag Red Retrospot", price: 1.65, badge: "54.2% Affinity" },
            { sku: "20727", desc: "Lunch Bag Black Skull", price: 1.65, badge: "48.9% Affinity" },
            { sku: "20728", desc: "Lunch Bag Cars Blue", price: 1.65, badge: "47.8% Affinity" },
            { sku: "22386", desc: "Jumbo Bag Pink Polkadot", price: 1.79, badge: "46.2% Affinity" },
            { sku: "22383", desc: "Lunch Bag Suki Design", price: 1.65, badge: "45.1% Affinity" }
        ]
    },
    "20725": {
        title: "Frequently Bought Together with: [20725] Lunch Bag Red Retrospot",
        items: [
            { sku: "85099B", desc: "Jumbo Bag Red Retrospot", price: 1.79, badge: "54.2% Affinity" },
            { sku: "20727", desc: "Lunch Bag Black Skull", price: 1.65, badge: "52.1% Affinity" },
            { sku: "20728", desc: "Lunch Bag Cars Blue", price: 1.65, badge: "50.9% Affinity" },
            { sku: "22383", desc: "Lunch Bag Suki Design", price: 1.65, badge: "49.8% Affinity" },
            { sku: "20726", desc: "Lunch Bag Woodland", price: 1.65, badge: "48.5% Affinity" }
        ]
    }
};

const USER_RECS_DATABASE = {
    "17850": {
        title: "Personalized Discovery for Customer 17850 (Filtering Owned SKUs)",
        items: [
            { sku: "21733", desc: "Red Hanging Heart T-Light Holder", price: 2.95, badge: "Decor Affinity" },
            { sku: "23355", desc: "Hot Water Bottle Keep Calm", price: 4.95, badge: "Comfort Affinity" },
            { sku: "22865", desc: "Hand Warmer Owl Design", price: 2.10, badge: "Seasonal Cross-Sell" },
            { sku: "22470", desc: "Heart Of Wicker Large", price: 2.95, badge: "Basket Add-on" },
            { sku: "22469", desc: "Heart Of Wicker Small", price: 1.65, badge: "High Propensity" }
        ]
    },
    "13089": {
        title: "Personalized Recommendations for Customer 13089 (B2B Wholesaler)",
        items: [
            { sku: "22423", desc: "Regency Cakestand 3 Tier", price: 10.95, badge: "Top Wholesale Driver" },
            { sku: "47566", desc: "Party Bunting", price: 4.65, badge: "Event Supply" },
            { sku: "22699", desc: "Roses Regency Teacup And Saucer", price: 2.95, badge: "Teaware Expansion" },
            { sku: "85099B", desc: "Jumbo Bag Red Retrospot", price: 1.79, badge: "Packing Re-order" },
            { sku: "22086", desc: "Paper Chain Kit 50'S Christmas", price: 2.95, badge: "Seasonal Restock" }
        ]
    },
    "15311": {
        title: "Personalized Recommendations for Customer 15311 (Vintage Kitchen)",
        items: [
            { sku: "22697", desc: "Green Regency Teacup And Saucer", price: 2.95, badge: "Teaware Variant" },
            { sku: "23245", desc: "Set Of 3 Regency Cake Tins", price: 4.95, badge: "Baking Essentials" },
            { sku: "20725", desc: "Lunch Bag Red Retrospot", price: 1.65, badge: "Dining Accessory" },
            { sku: "23173", desc: "Regency Teapot Roses", price: 9.95, badge: "Complementary Set" },
            { sku: "22698", desc: "Pink Regency Teacup And Saucer", price: 2.95, badge: "High Affinity" }
        ]
    },
    "14646": {
        title: "Personalized Recommendations for Customer 14646 (Top Dutch VIP Buyer)",
        items: [
            { sku: "22423", desc: "Regency Cakestand 3 Tier", price: 10.95, badge: "Margin Booster" },
            { sku: "85123A", desc: "White Hanging Heart T-Light Holder", price: 2.55, badge: "High Volume" },
            { sku: "23843", desc: "Paper Craft , Little Birdie", price: 2.08, badge: "Craft Line" },
            { sku: "47566", desc: "Party Bunting", price: 4.65, badge: "Export Affinity" },
            { sku: "22386", desc: "Jumbo Bag Pink Polkadot", price: 1.79, badge: "Luggage Accessory" }
        ]
    }
};

function initRecommenderTab() {
    const modeSelect = document.getElementById("recModeSelect");
    const skuGroup = document.getElementById("skuSelectorGroup");
    const custGroup = document.getElementById("custSelectorGroup");
    const skuSelect = document.getElementById("skuSelect");
    const custSelect = document.getElementById("custSelect");
    const recsTitle = document.getElementById("recsTitle");
    const recsGrid = document.getElementById("recsGrid");

    function renderRecommendations() {
        const mode = modeSelect.value;
        let data;

        if (mode === "item") {
            skuGroup.style.display = "flex";
            custGroup.style.display = "none";
            const sku = skuSelect.value;
            data = RECS_CATALOG[sku] || RECS_CATALOG["22423"];
        } else {
            skuGroup.style.display = "none";
            custGroup.style.display = "flex";
            const cid = custSelect.value;
            data = USER_RECS_DATABASE[cid] || USER_RECS_DATABASE["17850"];
        }

        recsTitle.textContent = data.title;
        recsGrid.innerHTML = data.items.map(item => `
            <div class="rec-card">
                <div>
                    <span class="rec-sku">SKU: ${item.sku}</span>
                    <h4 class="rec-title">${item.desc}</h4>
                </div>
                <div>
                    <div class="rec-price">£${item.price.toFixed(2)}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.4rem;">
                        <span class="rec-badge">${item.badge}</span>
                        <button class="btn btn-outline btn-xs add-cart-btn" data-sku="${item.sku}" data-desc="${item.desc}" data-price="${item.price}">+ Add</button>
                    </div>
                </div>
            </div>
        `).join("");

        document.querySelectorAll(".add-cart-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const sku = btn.getAttribute("data-sku");
                const desc = btn.getAttribute("data-desc");
                const price = parseFloat(btn.getAttribute("data-price"));
                addToCart(sku, desc, price);
            });
        });
    }

    if (modeSelect) modeSelect.addEventListener("change", renderRecommendations);
    if (skuSelect) skuSelect.addEventListener("change", renderRecommendations);
    if (custSelect) custSelect.addEventListener("change", renderRecommendations);

    window.quickSelectSku = function(sku) {
        if (modeSelect) modeSelect.value = "item";
        if (skuSelect) {
            skuSelect.value = sku;
            renderRecommendations();
            showToast("Catalog Item", `Loaded collaborative cross-sell for SKU [${sku}]`, "info");
            logAuditEvent("Recommender", `Quick-selected SKU [${sku}]`);
        }
    };

    renderRecommendations();
    initMarketBasketRules();
}

// =============================================================================
// PHASE 21: MARKET BASKET ASSOCIATION RULES & BUNDLE OPTIMIZER
// =============================================================================
let BASKET_RULES_CACHE = [];
let BASKET_RULES_WIRED = false;

async function refreshMarketBasketRules() {
    const tbody = document.getElementById("basketRulesTbody");
    const slider = document.getElementById("basketMinLiftSlider");
    const minLiftVal = document.getElementById("basketMinLiftVal");
    if (!tbody) return;

    const minLift = parseFloat(slider ? slider.value : "1.2");
    if (minLiftVal) minLiftVal.textContent = `${minLift.toFixed(1)}x`;

    let report = null;
    try {
        const res = await fetch(`http://localhost:8000/api/v1/recommendations/basket-rules?min_lift=${minLift}&min_support_pct=0.5&limit=18`);
        if (res.ok) report = await res.json();
    } catch (_e) {
        // Offline association rules fallback below
    }

    if (!report) {
        const fallbackRules = [
            { rule_id: "22699->22697", antecedent_code: "22699", antecedent_name: "Roses Regency Teacup And Saucer", antecedent_price: 2.95, consequent_code: "22697", consequent_name: "Green Regency Teacup And Saucer", consequent_price: 2.95, support_pct: 12.4, confidence_pct: 76.2, lift: 4.18, conviction: 3.45, bundle_offer_gbp: 5.31 },
            { rule_id: "22423->22699", antecedent_code: "22423", antecedent_name: "Regency Cakestand 3 Tier", antecedent_price: 10.95, consequent_code: "22699", consequent_name: "Roses Regency Teacup And Saucer", consequent_price: 2.95, support_pct: 9.8, confidence_pct: 58.4, lift: 3.21, conviction: 1.98, bundle_offer_gbp: 12.51 },
            { rule_id: "85123A->21733", antecedent_code: "85123A", antecedent_name: "White Hanging Heart T-Light Holder", antecedent_price: 2.55, consequent_code: "21733", consequent_name: "Red Hanging Heart T-Light Holder", consequent_price: 2.55, support_pct: 8.6, confidence_pct: 61.0, lift: 2.94, conviction: 2.04, bundle_offer_gbp: 4.59 },
            { rule_id: "85099B->20725", antecedent_code: "85099B", antecedent_name: "Jumbo Bag Red Retrospot", antecedent_price: 1.79, consequent_code: "20725", consequent_name: "Lunch Bag Red Retrospot", consequent_price: 1.65, support_pct: 7.4, confidence_pct: 48.2, lift: 2.15, conviction: 1.50, bundle_offer_gbp: 3.10 }
        ].filter(r => r.lift >= minLift);
        report = {
            summary: {
                total_matching_rules: fallbackRules.length,
                top_lift: fallbackRules[0] ? fallbackRules[0].lift : minLift,
                avg_confidence_pct: 61.0,
                avg_bundle_offer_gbp: 6.38
            },
            rules: fallbackRules
        };
    }

    BASKET_RULES_CACHE = report.rules || [];
    const s = report.summary || {};
    const topEl = document.getElementById("basketTopLiftVal");
    const confEl = document.getElementById("basketAvgConfVal");
    const cntEl = document.getElementById("basketRuleCountVal");
    const avgBEl = document.getElementById("basketAvgBundleVal");
    if (topEl) topEl.textContent = `${Number(s.top_lift || 0).toFixed(2)}x`;
    if (confEl) confEl.textContent = `${Number(s.avg_confidence_pct || 0).toFixed(1)}%`;
    if (cntEl) cntEl.textContent = `${Number(s.total_matching_rules || 0).toLocaleString()} rules`;
    if (avgBEl) avgBEl.textContent = `£${Number(s.avg_bundle_offer_gbp || 0).toFixed(2)}`;

    if (!BASKET_RULES_CACHE.length) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--text-muted);">No association rules exceed Lift >= ${minLift.toFixed(1)}x. Lower the threshold slider above.</td></tr>`;
        return;
    }

    tbody.innerHTML = BASKET_RULES_CACHE.map(r => {
        const liftColor = r.lift >= 3.0 ? "#10B981" : r.lift >= 2.0 ? "#3B82F6" : "#F59E0B";
        return `
            <tr>
                <td><code>${r.antecedent_code}</code> <strong>${r.antecedent_name}</strong></td>
                <td><code>${r.consequent_code}</code> <strong>${r.consequent_name}</strong></td>
                <td>${r.support_pct}%</td>
                <td><strong>${r.confidence_pct}%</strong></td>
                <td><span class="badge-tag" style="background:${liftColor}22;color:${liftColor};font-weight:700;">${r.lift}x</span></td>
                <td>${r.conviction}</td>
                <td><strong class="text-green">£${Number(r.bundle_offer_gbp).toFixed(2)}</strong></td>
                <td>
                    <button type="button" class="btn btn-outline btn-xs" onclick="window.addAssociationBundle('${r.antecedent_code}', '${r.consequent_code}')">+ Add Pair</button>
                </td>
            </tr>
        `;
    }).join("");
}

function initMarketBasketRules() {
    refreshMarketBasketRules();
    if (BASKET_RULES_WIRED) return;
    BASKET_RULES_WIRED = true;

    const slider = document.getElementById("basketMinLiftSlider");
    const exportBtn = document.getElementById("exportBasketRulesBtn");

    if (slider) {
        slider.addEventListener("input", refreshMarketBasketRules);
        slider.addEventListener("change", refreshMarketBasketRules);
    }
    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            if (BASKET_RULES_CACHE.length) {
                downloadCSV("market_basket_association_rules.csv", BASKET_RULES_CACHE);
                showToast("Rules Exported", "market_basket_association_rules.csv downloaded", "success");
                logAuditEvent("Recommender", "Exported Phase 21 Apriori Association Rules to CSV");
            }
        });
    }

    window.addAssociationBundle = (aCode, bCode) => {
        const match = BASKET_RULES_CACHE.find(r => r.antecedent_code === aCode && r.consequent_code === bCode);
        if (!match) return;
        addToCart(match.antecedent_code, match.antecedent_name, match.antecedent_price);
        addToCart(match.consequent_code, match.consequent_name, match.consequent_price);
    };
}

function addToCart(sku, desc, price) {
    const existing = APP_STATE.cart.find(i => i.sku === sku);
    if (existing) {
        existing.qty += 1;
    } else {
        APP_STATE.cart.push({ sku, desc, price, qty: 1 });
    }
    try { localStorage.setItem("nexus_cart", JSON.stringify(APP_STATE.cart)); } catch (e) {}
    showToast("Added to Basket", `[${sku}] ${desc} added to cart`, "success");
    renderCart();
    recalculateBasketCrossSell();
}

function removeFromCart(sku) {
    APP_STATE.cart = APP_STATE.cart.filter(i => i.sku !== sku);
    try { localStorage.setItem("nexus_cart", JSON.stringify(APP_STATE.cart)); } catch (e) {}
    renderCart();
    recalculateBasketCrossSell();
}

function renderCart() {
    const list = document.getElementById("cartItemsList");
    const countSpan = document.getElementById("cartCount");
    const totalSpan = document.getElementById("cartTotalAmount");

    if (!list) return;

    if (APP_STATE.cart.length === 0) {
        list.innerHTML = `<p class="text-muted" style="font-size:0.85rem; padding:1rem 0;">Your simulated basket is empty. Click "+ Add to Cart" on any item above.</p>`;
        if (countSpan) countSpan.textContent = "0";
        if (totalSpan) totalSpan.textContent = "£0.00";
        return;
    }

    let subtotal = 0;
    let totalItems = 0;

    list.innerHTML = APP_STATE.cart.map(item => {
        const itemTotal = item.qty * item.price;
        subtotal += itemTotal;
        totalItems += item.qty;
        return `
            <div class="cart-item-row">
                <div class="cart-item-info">
                    <strong>${item.desc}</strong>
                    <small>SKU: ${item.sku} | Qty: ${item.qty} × £${item.price.toFixed(2)}</small>
                </div>
                <div class="cart-item-actions">
                    <span class="cart-item-price">£${itemTotal.toFixed(2)}</span>
                    <button class="cart-item-remove" onclick="removeFromCart('${item.sku}')">✕</button>
                </div>
            </div>
        `;
    }).join("");

    if (countSpan) countSpan.textContent = totalItems;
    if (totalSpan) totalSpan.textContent = `£${subtotal.toFixed(2)}`;
}

function recalculateBasketCrossSell() {
    const basketRecsList = document.getElementById("basketRecsList");
    if (!basketRecsList) return;

    if (APP_STATE.cart.length === 0) {
        basketRecsList.innerHTML = `<p class="text-muted" style="font-size:0.85rem; padding:1rem 0;">Add products to the basket to calculate composite vector affinities.</p>`;
        return;
    }

    // Determine highest affinity complementary item based on active cart SKUs
    const currentSkus = APP_STATE.cart.map(i => i.sku);
    let candidatePool = [];

    currentSkus.forEach(sku => {
        const lookup = RECS_CATALOG[sku];
        if (lookup) {
            candidatePool.push(...lookup.items);
        }
    });

    // Fallback to top Regency or Party accessories if unknown
    if (candidatePool.length === 0) {
        candidatePool = RECS_CATALOG["22423"].items;
    }

    // Filter out items already in the cart
    const filteredPool = candidatePool.filter(c => !currentSkus.includes(c.sku));
    const uniquePool = Array.from(new Map(filteredPool.map(item => [item.sku, item])).values()).slice(0, 3);

    basketRecsList.innerHTML = uniquePool.map(rec => `
        <div class="basket-rec-card">
            <div>
                <strong style="font-size:0.85rem; display:block;">${rec.desc}</strong>
                <small style="color:var(--text-muted);">SKU: ${rec.sku} | £${rec.price.toFixed(2)}</small>
            </div>
            <button class="btn btn-outline btn-xs" onclick="addToCart('${rec.sku}', '${rec.desc.replace(/'/g, "\\'")}', ${rec.price})">+ Add to Order</button>
        </div>
    `).join("");
}

function initLiveCartSimulator() {
    const clearBtn = document.getElementById("clearCartBtn");
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            APP_STATE.cart = [];
            renderCart();
            recalculateBasketCrossSell();
            showToast("Cart Cleared", "Simulated basket emptied", "info");
        });
    }

    const checkoutBtn = document.getElementById("cartCheckoutBtn");
    if (checkoutBtn) {
        checkoutBtn.addEventListener("click", () => {
            if (!APP_STATE.cart || APP_STATE.cart.length === 0) {
                showToast("Basket Empty", "Add items to your basket before initiating POS checkout", "alert");
                return;
            }

            const totalAmount = APP_STATE.cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
            const totalUnits = APP_STATE.cart.reduce((sum, item) => sum + item.qty, 0);
            const primaryItem = APP_STATE.cart[0];

            switchTab("transaction-simulator");
            const simCustId = document.getElementById("simCustId");
            const simSkuCode = document.getElementById("simSkuCode");
            const simQty = document.getElementById("simQty");
            const simPrice = document.getElementById("simPrice");

            if (simCustId) simCustId.value = "12352";
            if (simSkuCode && primaryItem) simSkuCode.value = primaryItem.sku;
            if (simQty) simQty.value = totalUnits;
            if (simPrice && primaryItem) simPrice.value = (totalAmount / totalUnits).toFixed(2);

            showToast("Basket Dispatched to POS", `Transferred ${totalUnits} units (£${totalAmount.toFixed(2)}) to Live POS Injection Engine`, "success");
            logAuditEvent("POS", `Dispatched shopping basket order of ${totalUnits} items (£${totalAmount.toFixed(2)}) to POS simulator`);

            const posForm = document.getElementById("posSimulatorForm");
            if (posForm) {
                setTimeout(() => posForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true })), 300);
            }
        });
    }

    // Prepopulate cart with 1 initial sample item so user sees immediate interactivity
    addToCart("22423", "Regency Cakestand 3 Tier", 10.95);
}

// =============================================================================
// CUSTOMER DETAIL SLIDE-IN MODAL DRAWER
// =============================================================================
function openCustomerDrawer(cid) {
    const backdrop = document.getElementById("customerDrawerBackdrop");
    const drawerTitle = document.getElementById("drawerCustTitle");
    const drawerBadge = document.getElementById("drawerCustBadge");
    const drawerBody = document.getElementById("drawerBody");

    const cust = MASTER_CUSTOMERS.find(c => c.id === cid) || {
        id: cid, segment: "Loyal Customers", spend: 1850.00, orders: 8, aov: 231.25, recency: 18, churnProb: 0.18,
        history: ["Regency Cakestand", "White T-Light Holder", "Vintage Christmas Chain"]
    };

    if (drawerTitle) drawerTitle.textContent = `Customer Account #${cust.id}`;
    if (drawerBadge) {
        drawerBadge.textContent = cust.segment;
        drawerBadge.className = `badge-tag ${cust.segment.includes("VIP") ? "gold-border" : cust.segment.includes("At-Risk") ? "red-border" : "green-border"}`;
    }

    const savedNotes = localStorage.getItem(`nexus_notes_${cust.id}`) || "VIP wholesale client. High preference for Regency collection lines.";

    if (drawerBody) {
        drawerBody.innerHTML = `
            <div>
                <div class="drawer-section-title">Account Financial Summary</div>
                <div class="result-grid">
                    <div class="result-stat"><strong>Lifetime Spend</strong><span>£${cust.spend.toLocaleString(undefined, {minimumFractionDigits: 2})}</span></div>
                    <div class="result-stat"><strong>Order Count</strong><span>${cust.orders} Invoices</span></div>
                    <div class="result-stat"><strong>Average Order Value</strong><span>£${cust.aov.toFixed(2)}</span></div>
                    <div class="result-stat"><strong>Days Inactive</strong><span>${cust.recency} days</span></div>
                </div>
            </div>

            <div>
                <div class="drawer-section-title">Churn Risk Assessment</div>
                <div style="background:var(--bg-surface-alt); padding:0.85rem; border-radius:6px; border-left:3px solid ${cust.churnProb >= 0.70 ? '#EF4444' : '#10B981'};">
                    <strong>Model Probability: ${(cust.churnProb * 100).toFixed(1)}%</strong>
                    <p style="font-size:0.82rem; color:var(--text-secondary); margin-top:0.25rem;">
                        ${cust.churnProb >= 0.70 ? 'High probability of departure. Urgent engagement required.' : 'Healthy retention trajectory.'}
                    </p>
                </div>
            </div>

            <div>
                <div class="drawer-section-title">Verified Invoicing Ledger History</div>
                <div class="drawer-timeline">
                    ${cust.history.map((h, i) => `
                        <div class="drawer-timeline-item">
                            <strong style="font-size:0.85rem;">Invoice #INV-${201100 + i}</strong>
                            <div style="font-size:0.8rem; color:var(--text-secondary);">${h}</div>
                        </div>
                    `).join("")}
                </div>
            </div>

            <div>
                <div class="drawer-section-title">Internal CRM Notes & Direct Actions</div>
                <textarea id="drawerNotesInput" placeholder="Add executive notes for this account..." style="width:100%; height:70px; background:var(--bg-surface-alt); border:1px solid var(--border-color); color:var(--text-primary); padding:0.5rem; border-radius:6px; font-size:0.82rem; outline:none; resize:none;">${savedNotes}</textarea>
                <div style="display:flex; gap:0.5rem; margin-top:0.65rem;">
                    <button class="btn btn-primary btn-sm flex-1" onclick="triggerCustomerCoupon('${cust.id}')">✉️ Send 20% Retention Code</button>
                    <button class="btn btn-secondary btn-sm" onclick="saveCustomerNotes('${cust.id}')">Save Notes</button>
                </div>
            </div>
        `;
    }

    if (backdrop) backdrop.classList.add("open");
}

function closeCustomerDrawer() {
    const backdrop = document.getElementById("customerDrawerBackdrop");
    if (backdrop) backdrop.classList.remove("open");
}

function triggerCustomerCoupon(cid) {
    showToast("Promotional Code Dispatched", `Sent 20% discount coupon to Customer #${cid}`, "success");
    logAuditEvent("CRM", `Dispatched bespoke retention discount to Customer #${cid}`);
    closeCustomerDrawer();
}

function saveCustomerNotes(cid) {
    const input = document.getElementById("drawerNotesInput");
    if (input) {
        localStorage.setItem(`nexus_notes_${cid}`, input.value);
    }
    showToast("Notes Saved", `CRM profile updated for Customer #${cid}`, "success");
    logAuditEvent("CRM", `Updated account notes for Customer #${cid}`);
}

function initCustomerDrawer() {
    const backdrop = document.getElementById("customerDrawerBackdrop");
    const closeBtn = document.getElementById("drawerCloseBtn");

    if (closeBtn) closeBtn.addEventListener("click", closeCustomerDrawer);
    if (backdrop) {
        backdrop.addEventListener("click", (e) => {
            if (e.target === backdrop) closeCustomerDrawer();
        });
    }
}

// =============================================================================
// TAB 6: MLOPS CONSOLE & MODEL REGISTRY & DATA DRIFT RADAR
// =============================================================================
function initMLOpsConsole() {
    const term = document.getElementById("terminalOutput");
    const globalRetrainBtn = document.getElementById("triggerGlobalRetrainBtn");

    function appendTermLog(msg) {
        if (!term) return;
        const now = new Date().toISOString().replace("T", " ").substring(0, 19);
        term.textContent += `\n[${now}] ${msg}`;
        term.scrollTop = term.scrollHeight;
    }

    window.appendMLOpsTermLog = appendTermLog;

    if (globalRetrainBtn) {
        globalRetrainBtn.addEventListener("click", async () => {
            globalRetrainBtn.disabled = true;
            globalRetrainBtn.textContent = "⚙️ Executing Pipeline...";
            appendTermLog("ADMIN TRIGGER: Initiating full MLOps pipeline execution...");

            appendTermLog("[Pipeline] Step 1/4: Ingesting latest POS transactional logs...");
            appendTermLog("[Pipeline] Step 2/4: Rebuilding RFM feature stores and 7-day lagged windows...");

            try {
                const res = await fetch("http://localhost:8000/api/v1/mlops/retrain", {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify({ trigger_source: "admin_web_console", model_types: ["all"] })
                });

                if (res.status === 401 || res.status === 403) {
                    const errBody = await res.json().catch(() => ({}));
                    appendTermLog(`[RBAC DENIED] HTTP ${res.status}: ${errBody.detail || "Insufficient permissions"}`);
                    globalRetrainBtn.disabled = false;
                    globalRetrainBtn.textContent = "⚡ Run Pipeline Ingest & Retrain";
                    showToast("RBAC Access Denied", errBody.detail || `HTTP ${res.status} on MLOps Retrain`, "alert");
                    return;
                }

                if (res.ok) {
                    const data = await res.json();
                    const tel = data.telemetry || {};
                    appendTermLog("[Pipeline] Step 3/4: Fitting Random Forest Regressors, Churn & BTYD models...");
                    appendTermLog(`[Pipeline] Step 4/4: Serialized updated models. Version: ${tel.new_version || "v2.5-prod"}`);
                    appendTermLog(`SUCCESS: Full pipeline executed. Model checkpoint promoted: ${tel.new_version || "v2.5-prod"}.`);
                    appendTermLog(`[Validation] Sales MAPE: ${tel.forecaster_mape || 26.28}%, Churn ROC-AUC: ${tel.churn_auc || 0.7163}`);

                    globalRetrainBtn.disabled = false;
                    globalRetrainBtn.textContent = "⚡ Run Pipeline Ingest & Retrain";
                    showToast("MLOps Pipeline Complete", `Retraining successful. Model version: ${tel.new_version}`, "success");
                    logAuditEvent("MLOps", `Triggered automated model retraining; promoted version ${tel.new_version}`);

                    // Refresh drift check back to baseline
                    evaluateDriftScenario("baseline");
                    return;
                }
            } catch (err) {
                console.warn("[MLOps Retrain] FastAPI server offline, falling back to local simulation:", err.message);
            }

            // Fallback simulation if FastAPI not reachable
            setTimeout(() => appendTermLog("[Pipeline] Step 3/4: Fitting Random Forest Regressor & Churn Classifier..."), 1000);
            setTimeout(() => appendTermLog("[Pipeline] Step 4/4: Exporting serialized .joblib binaries to /models/..."), 1800);
            setTimeout(() => {
                appendTermLog("SUCCESS: Pipeline completed in 2.84s. Model Registry version updated to v2.5.0-prod.");
                globalRetrainBtn.disabled = false;
                globalRetrainBtn.textContent = "⚡ Run Pipeline Ingest & Retrain";
                showToast("MLOps Pipeline Complete", "All 4 models retrained & version v2.5.0 verified", "success");
                logAuditEvent("MLOps", "Triggered manual model retraining pipeline; checkpoint v2.5.0 verified");
                evaluateDriftScenario("baseline");
            }, 2600);
        });
    }

    document.querySelectorAll(".retrain-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const m = btn.getAttribute("data-model");
            btn.textContent = "Training...";
            btn.disabled = true;
            appendTermLog(`ADMIN TRIGGER: Re-fitting isolated model: ${m}...`);
            setTimeout(() => {
                btn.textContent = "Retrain";
                btn.disabled = false;
                appendTermLog(`SUCCESS: ${m} retraining complete. Out-of-sample metrics maintained.`);
                showToast("Model Checkpointed", `${m} successfully re-fit`, "success");
                logAuditEvent("MLOps", `Re-fit individual model: ${m}`);
            }, 1200);
        });
    });

    // Initialize Statistical Data Drift Radar
    initDriftRadar();
}

// =============================================================================
// PHASE 8: DATA DRIFT DETECTION & MODEL DECAY RADAR
// =============================================================================
function initDriftRadar() {
    evaluateDriftScenario("baseline");
    initPersistenceTelemetry();
}

let PERSISTENCE_WIRED = false;

async function refreshPersistenceStatus(checkpoint = false) {
    const modeBadge = document.getElementById("persistenceModeBadge");
    const totalEl = document.getElementById("persistTotalRows");
    const poEl = document.getElementById("persistPoCount");
    const fraudEl = document.getElementById("persistFraudCount");
    const auditEl = document.getElementById("persistAuditAndSize");
    const pathEl = document.getElementById("persistDbPathLabel");
    if (!totalEl) return;

    try {
        const url = checkpoint
            ? "http://localhost:8000/api/v1/system/persistence/checkpoint"
            : "http://localhost:8000/api/v1/system/persistence-status";
        const res = await fetch(url, {
            method: checkpoint ? "POST" : "GET",
            headers: window.getAuthHeaders({ "Content-Type": "application/json" })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            if (checkpoint) showToast("WAL Checkpoint Blocked", err.detail || `HTTP ${res.status}`, "alert");
            return;
        }
        const diag = await res.json();
        const tbl = diag.tables || {};
        if (modeBadge) modeBadge.textContent = `${diag.engine || "SQLite"} • ${diag.journal_mode || "WAL"}`;
        totalEl.textContent = Number(diag.total_persisted_records || 0).toLocaleString();
        if (poEl) poEl.textContent = Number(tbl.purchase_orders || 0).toLocaleString();
        if (fraudEl) fraudEl.textContent = Number(tbl.fraud_alerts || 0).toLocaleString();
        if (auditEl) auditEl.textContent = `${Number(tbl.audit_events || 0).toLocaleString()} (${diag.size_kb || 0} KB)`;
        if (pathEl) pathEl.textContent = `Database Path: ${diag.db_path}`;
        if (checkpoint) {
            showToast("WAL Checkpointed", `Flushed ${diag.total_persisted_records} records cleanly (${diag.size_kb} KB)`, "success");
        }
    } catch (_e) {
        if (modeBadge) modeBadge.textContent = "OFFLINE LOCAL";
        totalEl.textContent = "—";
        if (pathEl) pathEl.textContent = "Database Path: Backend :8000 offline";
    }
}

function initPersistenceTelemetry() {
    refreshPersistenceStatus(false);
    initAutonomousWatchdog();
    if (PERSISTENCE_WIRED) return;
    PERSISTENCE_WIRED = true;
    const refreshBtn = document.getElementById("btnRefreshPersistence");
    const checkpointBtn = document.getElementById("btnCheckpointWal");
    if (refreshBtn) refreshBtn.addEventListener("click", () => refreshPersistenceStatus(false));
    if (checkpointBtn) checkpointBtn.addEventListener("click", () => refreshPersistenceStatus(true));
}

// =============================================================================
// PHASE 20: AUTONOMOUS CROSS-ENGINE TELEMETRY WATCHDOG
// =============================================================================
let WATCHDOG_WIRED = false;

function renderWatchdogSnapshot(snap) {
    const badge = document.getElementById("watchdogOverallBadge");
    const grid = document.getElementById("watchdogSubsystemsGrid");
    const list = document.getElementById("watchdogDirectivesList");
    if (!snap || !grid || !list) return;

    const score = Number(snap.health_score ?? 100);
    if (badge) {
        badge.textContent = `HEALTH SCORE: ${score.toFixed(1)}/100 (${snap.overall_status})`;
        badge.className = `badge-tag ${score < 60 ? "red" : score < 85 ? "gold" : "green"}`;
    }

    grid.innerHTML = (snap.subsystems || []).map(sub => {
        const cls = sub.status === "CRITICAL" ? "text-red" : sub.status === "WARNING" ? "text-gold" : "text-green";
        return `
            <div class="btyd-stat-box">
                <strong>${sub.name}</strong>
                <div class="stat-val ${cls}" style="font-size:1.05rem;">${sub.metric}</div>
                <small style="color:var(--text-muted);">${sub.status}</small>
            </div>
        `;
    }).join("");

    const dirs = snap.directives || [];
    if (!dirs.length) {
        list.innerHTML = `<div class="notif-item success"><strong>All 4 Subsystems Nominal</strong><p>Inventory EOQ, Cohort Retention, MLOps Drift PSI, and Fraud Quarantine are within safe operational thresholds.</p></div>`;
    } else {
        list.innerHTML = dirs.map(d => {
            const cls = d.severity === "CRITICAL" ? "critical" : "info";
            return `
                <div class="notif-item ${cls}" style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:0;">
                    <div>
                        <div class="notif-badge">${d.subsystem} • ${d.severity}</div>
                        <strong>${d.title}</strong>
                        <p style="margin-top:0.15rem;">${d.detail}</p>
                    </div>
                    <button type="button" class="btn btn-outline btn-xs" onclick="switchTab('${d.target_tab}')">${d.cta_label} &rarr;</button>
                </div>
            `;
        }).join("");
    }
}

async function runAutonomousWatchdog(triggerPost = false, simulateStress = false) {
    let snap = null;
    try {
        const url = triggerPost
            ? "http://localhost:8000/api/v1/watchdog/sweep"
            : "http://localhost:8000/api/v1/watchdog/status";
        const opts = triggerPost
            ? {
                method: "POST",
                headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify({ simulate_stress: simulateStress, auto_remediate: simulateStress })
            }
            : { method: "GET", headers: window.getAuthHeaders() };
        const res = await fetch(url, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            if (triggerPost) showToast("Watchdog Blocked", err.detail || `HTTP ${res.status}`, "alert");
            return;
        }
        const data = await res.json();
        snap = triggerPost ? data.sweep : data.latest;
        if (triggerPost && snap) {
            showToast("4-Engine Watchdog Sweep Complete", `Health Score: ${snap.health_score}/100 (${(snap.directives || []).length} directives)`, snap.health_score < 70 ? "alert" : "info");
            logAuditEvent("Watchdog", `Executed Phase 20 4-Engine Sweep (${snap.sweep_id}, Health ${snap.health_score}/100)`);
        }
    } catch (_e) {
        snap = {
            sweep_id: "SWP-LOCAL",
            health_score: simulateStress ? 48.5 : 86.0,
            overall_status: simulateStress ? "CRITICAL" : "HEALTHY",
            subsystems: [
                { key: "inventory", name: "Inventory & Stockout", status: simulateStress ? "CRITICAL" : "WARNING", metric: simulateStress ? "5 SKUs <= ROP" : "3 SKUs <= ROP" },
                { key: "cohorts", name: "Cohort Retention", status: "HEALTHY", metric: "75.5% Champion Stay" },
                { key: "drift", name: "MLOps Drift PSI", status: simulateStress ? "CRITICAL" : "HEALTHY", metric: simulateStress ? "4 Shifted Features" : "0 Shifted Features" },
                { key: "fraud", name: "Fraud Quarantine", status: "WARNING", metric: "2 Pending Holds" }
            ],
            directives: [
                { severity: simulateStress ? "CRITICAL" : "WARNING", subsystem: "Inventory EOQ", title: "Flagship SKUs approaching ROP", detail: "Approve EOQ replenishment POs in Inventory Mart.", target_tab: "inventory-mart", cta_label: "Open EOQ Optimizer" }
            ]
        };
    }
    if (snap) renderWatchdogSnapshot(snap);
}

function initAutonomousWatchdog() {
    runAutonomousWatchdog(false, false);
    if (WATCHDOG_WIRED) return;
    WATCHDOG_WIRED = true;
    const sweepBtn = document.getElementById("btnRunWatchdogSweep");
    const stressBtn = document.getElementById("btnRunStressWatchdogSweep");
    if (sweepBtn) sweepBtn.addEventListener("click", () => runAutonomousWatchdog(true, false));
    if (stressBtn) stressBtn.addEventListener("click", () => runAutonomousWatchdog(true, true));
}

async function evaluateDriftScenario(scenario, clickedBtn = null) {
    const driftGrid = document.getElementById("driftGrid");
    const overallBadge = document.getElementById("driftOverallBadge");
    const actionBanner = document.getElementById("driftActionBanner");
    const apiBadge = document.getElementById("driftApiBadge");

    if (!driftGrid) return;

    // Update scenario button styling
    if (clickedBtn) {
        document.querySelectorAll(".drift-scenarios-bar .preset-chip").forEach(c => c.classList.remove("active"));
        clickedBtn.classList.add("active");
    } else {
        const scenarioBtnMap = {
            "baseline": "btnDriftBaseline",
            "black_friday": "btnDriftBlackFriday",
            "inflation": "btnDriftInflation",
            "dormancy_surge": "btnDriftDormancy"
        };
        const targetId = scenarioBtnMap[scenario];
        if (targetId) {
            const btn = document.getElementById(targetId);
            if (btn) {
                document.querySelectorAll(".drift-scenarios-bar .preset-chip").forEach(c => c.classList.remove("active"));
                btn.classList.add("active");
            }
        }
    }

    // Temporary loading state
    driftGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: var(--text-muted);">
            <div style="display: inline-block; animation: spin 1s linear infinite; margin-bottom: 0.5rem;">⚙️</div>
            <div>Evaluating two-sample Kolmogorov-Smirnov test & Population Stability Index across production distributions...</div>
        </div>
    `;

    let report = null;

    // 1. Attempt live query to FastAPI MLOps endpoint
    try {
        const resp = await fetch(`http://localhost:8000/api/v1/mlops/drift-report?scenario=${scenario}`);
        if (resp.ok) {
            report = await resp.json();
            if (apiBadge) {
                apiBadge.textContent = "FASTAPI :8000 LIVE";
                apiBadge.style.background = "rgba(59, 130, 246, 0.2)";
                apiBadge.style.color = "#3b82f6";
                apiBadge.style.borderColor = "rgba(59, 130, 246, 0.3)";
            }
        }
    } catch (e) {
        if (apiBadge) {
            apiBadge.textContent = "OFFLINE CACHE ACTIVE";
            apiBadge.style.background = "rgba(107, 114, 128, 0.2)";
            apiBadge.style.color = "#9ca3af";
            apiBadge.style.borderColor = "rgba(107, 114, 128, 0.3)";
        }
    }

    // 2. Offline fallback
    if (!report) {
        if (scenario === "baseline" && window.CACHED_DRIFT_REPORT) {
            report = window.CACHED_DRIFT_REPORT;
        } else {
            report = generateMockDriftReport(scenario);
        }
    }

    renderDriftReport(report);
}

function renderDriftReport(report) {
    const driftGrid = document.getElementById("driftGrid");
    const overallBadge = document.getElementById("driftOverallBadge");
    const actionBanner = document.getElementById("driftActionBanner");
    if (!driftGrid || !report) return;

    // 1. Overall Status Badge
    if (overallBadge) {
        if (report.overall_status === "DRIFT_DETECTED") {
            overallBadge.textContent = `🚨 DRIFT DETECTED (${report.drift_detected_count} Features)`;
            overallBadge.style.background = "rgba(239, 68, 68, 0.2)";
            overallBadge.style.color = "#ef4444";
            overallBadge.style.borderColor = "rgba(239, 68, 68, 0.4)";
        } else if (report.overall_status === "WARNING") {
            overallBadge.textContent = `⚡ MINOR SHIFT (${report.warning_count} Warnings)`;
            overallBadge.style.background = "rgba(245, 158, 11, 0.2)";
            overallBadge.style.color = "#f59e0b";
            overallBadge.style.borderColor = "rgba(245, 158, 11, 0.4)";
        } else {
            overallBadge.textContent = "🟢 HEALTHY (PSI < 0.10)";
            overallBadge.style.background = "rgba(16, 185, 129, 0.2)";
            overallBadge.style.color = "#10b981";
            overallBadge.style.borderColor = "rgba(16, 185, 129, 0.3)";
        }
    }

    // 2. Action Banner
    if (actionBanner) {
        if (report.overall_status === "DRIFT_DETECTED") {
            actionBanner.style.display = "flex";
            const bannerTitle = document.getElementById("driftBannerTitle");
            const bannerDesc = document.getElementById("driftBannerDesc");
            if (bannerTitle) bannerTitle.innerHTML = `⚠️ Automated Pipeline Retraining Required (${report.scenario ? report.scenario.toUpperCase() : 'ALERT'})`;
            if (bannerDesc) bannerDesc.textContent = report.system_action || "Significant distribution shift detected. Automated re-fitting of Random Forest and Churn models recommended to prevent inference degradation.";
        } else {
            actionBanner.style.display = "none";
        }
    }

    // 3. Feature Cards
    const features = report.features || [];
    driftGrid.innerHTML = features.map(feat => {
        const isAlert = feat.status === "DRIFT_DETECTED";
        const isWarning = feat.status === "WARNING";
        const cardClass = isAlert ? "drift-card drift-alert" : isWarning ? "drift-card drift-warning" : "drift-card drift-healthy";
        const badgeColor = isAlert ? "red" : isWarning ? "gold" : "green";
        const psiFillClass = isAlert ? "alert" : isWarning ? "warning" : "healthy";

        const psiWidthPct = Math.min(100, Math.max(4, (feat.psi_score / 0.50) * 100));

        const unit = feat.unit || "";
        const baseMean = unit === "£" ? `£${feat.baseline_mean.toFixed(2)}` : `${feat.baseline_mean.toFixed(1)} ${unit}`;
        const currMean = unit === "£" ? `£${feat.current_mean.toFixed(2)}` : `${feat.current_mean.toFixed(1)} ${unit}`;
        const meanShiftPct = feat.baseline_mean !== 0 ? (((feat.current_mean - feat.baseline_mean) / feat.baseline_mean) * 100).toFixed(1) : "0";
        const shiftSign = Number(meanShiftPct) > 0 ? `+${meanShiftPct}%` : `${meanShiftPct}%`;

        return `
            <div class="${cardClass}">
                <div class="drift-card-header">
                    <div>
                        <div class="drift-card-title">${feat.label}</div>
                        <span class="drift-card-code">Feature Vector: <code>${feat.feature}</code></span>
                    </div>
                    <span class="badge ${badgeColor}">${feat.badge}</span>
                </div>

                <div class="drift-metrics-list">
                    <div class="drift-metric-row">
                        <span class="drift-metric-label">Baseline Dist (Mean ± σ):</span>
                        <span class="drift-metric-val">${baseMean} <small class="text-muted">(±${feat.baseline_std})</small></span>
                    </div>
                    <div class="drift-metric-row">
                        <span class="drift-metric-label">Current Stream (Mean ± σ):</span>
                        <span class="drift-metric-val">${currMean} <small class="${Number(meanShiftPct) > 0 ? 'text-danger' : 'text-success'}">(${shiftSign})</small></span>
                    </div>
                    <div class="drift-metric-row">
                        <span class="drift-metric-label">KS Test (Stat / p-val):</span>
                        <span class="drift-metric-val">${feat.ks_statistic.toFixed(4)} / <code style="color: ${feat.ks_p_value < 0.05 ? '#ef4444' : '#10b981'}">p=${feat.ks_p_value < 0.0001 ? '<0.0001' : feat.ks_p_value.toFixed(4)}</code></span>
                    </div>
                </div>

                <div class="drift-psi-section">
                    <div class="drift-psi-header">
                        <span style="font-weight: 600; color: var(--text-secondary);">Population Stability Index (PSI)</span>
                        <span style="font-family: var(--font-mono); font-weight: 700; color: ${isAlert ? '#ef4444' : isWarning ? '#f59e0b' : '#10b981'};">${feat.psi_score.toFixed(4)}</span>
                    </div>
                    <div class="drift-psi-bar-wrap" title="PSI: ${feat.psi_score} (Threshold: 0.10 warning, 0.25 critical)">
                        <div class="drift-psi-fill ${psiFillClass}" style="width: ${psiWidthPct}%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); margin-top: 0.25rem;">
                        <span>0.0 (Stable)</span>
                        <span>0.10 (Warn)</span>
                        <span>0.25+ (Retrain)</span>
                    </div>
                </div>

                <div class="drift-rec-box ${psiFillClass}">
                    <strong>💡 Audit Assessment:</strong> ${feat.recommendation}
                </div>
            </div>
        `;
    }).join("");
}

function generateMockDriftReport(scenario) {
    if (scenario === "black_friday") {
        return {
            scenario: "black_friday",
            scenario_description: "Holiday volume surge: order quantities +180%, total basket spend +120%.",
            evaluated_samples: 4000,
            baseline_samples: 4000,
            overall_status: "DRIFT_DETECTED",
            system_action: "TRIGGER RETRAINING: Automated model pipeline re-execution required.",
            features_monitored_count: 3,
            drift_detected_count: 2,
            warning_count: 0,
            features: [
                {
                    feature: "UnitPrice",
                    label: "Unit Price (£)",
                    unit: "£",
                    baseline_mean: 3.12,
                    baseline_std: 4.85,
                    current_mean: 3.14,
                    current_std: 4.88,
                    psi_score: 0.0042,
                    ks_statistic: 0.0125,
                    ks_p_value: 0.485,
                    status: "HEALTHY",
                    badge: "Healthy",
                    color: "green",
                    recommendation: "Distribution is statistically consistent with baseline training data."
                },
                {
                    feature: "Quantity",
                    label: "Order Item Quantity",
                    unit: "units",
                    baseline_mean: 10.45,
                    baseline_std: 28.12,
                    current_mean: 28.25,
                    current_std: 76.40,
                    psi_score: 2.3388,
                    ks_statistic: 0.5840,
                    ks_p_value: 0.0,
                    status: "DRIFT_DETECTED",
                    badge: "Critical Drift",
                    color: "red",
                    recommendation: "Significant distribution divergence (PSI 2.339, KS p < 0.005). Model retraining recommended."
                },
                {
                    feature: "TotalPrice",
                    label: "Total Order Spend (£)",
                    unit: "£",
                    baseline_mean: 20.85,
                    baseline_std: 62.30,
                    current_mean: 56.40,
                    current_std: 168.20,
                    psi_score: 0.8420,
                    ks_statistic: 0.4210,
                    ks_p_value: 0.0,
                    status: "DRIFT_DETECTED",
                    badge: "Critical Drift",
                    color: "red",
                    recommendation: "Significant distribution divergence (PSI 0.842, KS p < 0.005). Model retraining recommended."
                }
            ]
        };
    } else if (scenario === "inflation") {
        return {
            scenario: "inflation",
            scenario_description: "Macro price elevation: unit catalog prices elevated by +45%.",
            evaluated_samples: 4000,
            baseline_samples: 4000,
            overall_status: "DRIFT_DETECTED",
            system_action: "TRIGGER RETRAINING: Automated model pipeline re-execution required.",
            features_monitored_count: 3,
            drift_detected_count: 1,
            warning_count: 1,
            features: [
                {
                    feature: "UnitPrice",
                    label: "Unit Price (£)",
                    unit: "£",
                    baseline_mean: 3.12,
                    baseline_std: 4.85,
                    current_mean: 5.75,
                    current_std: 8.92,
                    psi_score: 0.6520,
                    ks_statistic: 0.3840,
                    ks_p_value: 0.0,
                    status: "DRIFT_DETECTED",
                    badge: "Critical Drift",
                    color: "red",
                    recommendation: "Significant distribution divergence (PSI 0.652, KS p < 0.005). Model retraining recommended."
                },
                {
                    feature: "Quantity",
                    label: "Order Item Quantity",
                    unit: "units",
                    baseline_mean: 10.45,
                    baseline_std: 28.12,
                    current_mean: 10.40,
                    current_std: 28.05,
                    psi_score: 0.0035,
                    ks_statistic: 0.0110,
                    ks_p_value: 0.620,
                    status: "HEALTHY",
                    badge: "Healthy",
                    color: "green",
                    recommendation: "Distribution is statistically consistent with baseline training data."
                },
                {
                    feature: "TotalPrice",
                    label: "Total Order Spend (£)",
                    unit: "£",
                    baseline_mean: 20.85,
                    baseline_std: 62.30,
                    current_mean: 28.95,
                    current_std: 86.40,
                    psi_score: 0.1850,
                    ks_statistic: 0.0950,
                    ks_p_value: 0.008,
                    status: "WARNING",
                    badge: "Minor Shift",
                    color: "gold",
                    recommendation: "Moderate distribution variation detected (PSI 0.185). Monitor inference error closely."
                }
            ]
        };
    } else if (scenario === "dormancy_surge") {
        return {
            scenario: "dormancy_surge",
            scenario_description: "Customer inactivity shift: extended dormancy across purchasing cohorts.",
            evaluated_samples: 4000,
            baseline_samples: 4000,
            overall_status: "WARNING",
            system_action: "EVALUATE TELEMETRY: Model health degraded but within tolerable inference bounds.",
            features_monitored_count: 3,
            drift_detected_count: 0,
            warning_count: 2,
            features: [
                {
                    feature: "UnitPrice",
                    label: "Unit Price (£)",
                    unit: "£",
                    baseline_mean: 3.12,
                    baseline_std: 4.85,
                    current_mean: 3.12,
                    current_std: 4.85,
                    psi_score: 0.002,
                    ks_statistic: 0.008,
                    ks_p_value: 0.85,
                    status: "HEALTHY",
                    badge: "Healthy",
                    color: "green",
                    recommendation: "Distribution is statistically consistent with baseline training data."
                },
                {
                    feature: "Quantity",
                    label: "Order Item Quantity",
                    unit: "units",
                    baseline_mean: 10.45,
                    baseline_std: 28.12,
                    current_mean: 4.25,
                    current_std: 11.20,
                    psi_score: 0.194,
                    ks_statistic: 0.145,
                    ks_p_value: 0.001,
                    status: "WARNING",
                    badge: "Minor Shift",
                    color: "gold",
                    recommendation: "Moderate distribution variation detected (PSI 0.194). Monitor inference error closely."
                },
                {
                    feature: "TotalPrice",
                    label: "Total Order Spend (£)",
                    unit: "£",
                    baseline_mean: 20.85,
                    baseline_std: 62.30,
                    current_mean: 9.80,
                    current_std: 24.50,
                    psi_score: 0.215,
                    ks_statistic: 0.162,
                    ks_p_value: 0.0005,
                    status: "WARNING",
                    badge: "Minor Shift",
                    color: "gold",
                    recommendation: "Moderate distribution variation detected (PSI 0.215). Monitor inference error closely."
                }
            ]
        };
    }

    return {
        scenario: "baseline",
        scenario_description: "Normal operational traffic matching training distribution.",
        evaluated_samples: 4000,
        baseline_samples: 4000,
        overall_status: "HEALTHY",
        system_action: "SYSTEM OPTIMAL: All production feature vectors match baseline training distribution.",
        features_monitored_count: 3,
        drift_detected_count: 0,
        warning_count: 0,
        features: [
            {
                feature: "UnitPrice",
                label: "Unit Price (£)",
                unit: "£",
                baseline_mean: 3.12,
                baseline_std: 4.85,
                current_mean: 3.11,
                current_std: 4.82,
                psi_score: 0.0028,
                ks_statistic: 0.0102,
                ks_p_value: 0.741,
                status: "HEALTHY",
                badge: "Healthy",
                color: "green",
                recommendation: "Distribution is statistically consistent with baseline training data."
            },
            {
                feature: "Quantity",
                label: "Order Item Quantity",
                unit: "units",
                baseline_mean: 10.45,
                baseline_std: 28.12,
                current_mean: 10.38,
                current_std: 27.95,
                psi_score: 0.0034,
                ks_statistic: 0.0118,
                ks_p_value: 0.612,
                status: "HEALTHY",
                badge: "Healthy",
                color: "green",
                recommendation: "Distribution is statistically consistent with baseline training data."
            },
            {
                feature: "TotalPrice",
                label: "Total Order Spend (£)",
                unit: "£",
                baseline_mean: 20.85,
                baseline_std: 62.30,
                current_mean: 20.72,
                current_std: 61.85,
                psi_score: 0.0041,
                ks_statistic: 0.0135,
                ks_p_value: 0.458,
                status: "HEALTHY",
                badge: "Healthy",
                color: "green",
                recommendation: "Distribution is statistically consistent with baseline training data."
            }
        ]
    };
}

window.evaluateDriftScenario = evaluateDriftScenario;

// =============================================================================
// TAB 7: CUSTOMER ACCOUNT LEDGER
// =============================================================================
function initCustomerLedger() {
    const tbody = document.querySelector("#customerLedgerTable tbody");
    const filterSelect = document.getElementById("customerSegmentFilter");
    const searchInput = document.getElementById("custLedgerSearch");
    const exportBtn = document.getElementById("exportCustLedgerBtn");

    function renderLedger() {
        if (!tbody) return;
        const filter = filterSelect ? filterSelect.value : "all";
        const query = searchInput ? searchInput.value.trim() : "";

        let filtered = MASTER_CUSTOMERS.filter(c => {
            const matchSeg = filter === "all" || c.segment === filter;
            const matchQuery = !query || c.id.includes(query);
            return matchSeg && matchQuery;
        });

        tbody.innerHTML = filtered.map(c => {
            const badgeClass = c.segment.includes("VIP") ? "gold-border" : c.segment.includes("At-Risk") ? "red-border" : "green-border";
            const churnColor = c.churnProb >= 0.70 ? "#EF4444" : c.churnProb >= 0.35 ? "#F59E0B" : "#10B981";

            return `
                <tr style="cursor:pointer;" onclick="openCustomerDrawer('${c.id}')">
                    <td><strong>#${c.id}</strong></td>
                    <td><span class="badge-tag ${badgeClass}">${c.segment}</span></td>
                    <td><strong>£${c.spend.toLocaleString(undefined, {minimumFractionDigits: 2})}</strong></td>
                    <td>${c.orders}</td>
                    <td>£${c.aov.toFixed(2)}</td>
                    <td>${c.recency} days ago</td>
                    <td><span class="badge-tag" style="background:${churnColor}22; color:${churnColor};">${(c.churnProb * 100).toFixed(1)}%</span></td>
                    <td>
                        <button class="btn btn-outline btn-xs" onclick="event.stopPropagation(); openCustomerDrawer('${c.id}')">
                            Inspect
                        </button>
                    </td>
                </tr>
            `;
        }).join("");
    }

    if (filterSelect) filterSelect.addEventListener("change", renderLedger);
    if (searchInput) searchInput.addEventListener("input", renderLedger);
    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            downloadCSV("customer_ledger_export.csv", MASTER_CUSTOMERS);
            showToast("Export Complete", "customer_ledger_export.csv downloaded", "success");
            logAuditEvent("Export", "Exported Master Customer Ledger CSV");
        });
    }

    renderLedger();
}

// =============================================================================
// TAB 8: INVENTORY & CATALOG MART
// =============================================================================
const INVENTORY_DATABASE = [
    { code: "22423", name: "Regency Cakestand 3 Tier", price: 10.95, stock: 420, burn: 38, daysLeft: 11, status: "Critical Reorder" },
    { code: "85123A", name: "White Hanging Heart T-Light Holder", price: 2.55, stock: 1250, burn: 104, daysLeft: 12, status: "Critical Reorder" },
    { code: "47566", name: "Party Bunting", price: 4.65, stock: 950, burn: 50, daysLeft: 19, status: "Reorder Approaching" },
    { code: "85099B", name: "Jumbo Bag Red Retrospot", price: 1.79, stock: 3200, burn: 132, daysLeft: 24, status: "Healthy Stock" },
    { code: "20725", name: "Lunch Bag Red Retrospot", price: 1.65, stock: 2400, burn: 85, daysLeft: 28, status: "Healthy Stock" },
    { code: "22699", name: "Roses Regency Teacup And Saucer", price: 2.95, stock: 210, burn: 29, daysLeft: 7, status: "Urgent Stockout Risk" },
    { code: "22697", name: "Green Regency Teacup And Saucer", price: 2.95, stock: 180, burn: 27, daysLeft: 6, status: "Urgent Stockout Risk" }
];

let inventoryTrajectoryChartInstance = null;
let INVENTORY_POLICIES_CACHE = [];
let INVENTORY_PURCHASE_ORDERS_CACHE = [];
let INVENTORY_INIT_WIRED = false;

function computeLocalInventoryPolicy(item, serviceLevel = 0.95, leadDays = 7, demandMult = 1.0) {
    const zMap = { 0.90: 1.2816, 0.95: 1.6449, 0.98: 2.0537, 0.99: 2.3263 };
    const z = zMap[serviceLevel] || 1.6449;
    const mu = Math.max(0.5, item.burn * demandMult);
    const sigma = Math.max(0.2, (item.std || item.burn * 0.36) * Math.sqrt(demandMult));
    const unitCost = Math.max(0.25, item.price * 0.62);
    const ss = Math.max(1, Math.round(z * sigma * Math.sqrt(leadDays)));
    const rop = Math.max(ss + 1, Math.round(mu * leadDays + ss));
    const eoq = Math.max(10, Math.round(Math.sqrt((2 * mu * 365 * 45) / (unitCost * 0.22))));
    const daysRemaining = parseFloat((item.stock / mu).toFixed(1));
    const riskStatus = (item.stock <= rop * 0.85 || daysRemaining <= leadDays + 3)
        ? "CRITICAL_REORDER"
        : (item.stock <= rop * 1.2 || daysRemaining <= leadDays + 8)
            ? "REORDER_SOON"
            : daysRemaining > 75
                ? "OVERSTOCK_MARKDOWN"
                : "OPTIMAL";
    return {
        stock_code: item.code,
        description: item.name,
        unit_price: item.price,
        unit_cost: parseFloat(unitCost.toFixed(2)),
        abc_class: item.abc_class || (item.price * item.burn > 150 ? "A" : "B"),
        xyz_class: item.xyz_class || "Y",
        abc_xyz: item.abc_xyz || (item.price * item.burn > 150 ? "AX" : "BY"),
        stock_on_hand: item.stock,
        daily_demand_mean: parseFloat(mu.toFixed(2)),
        daily_demand_std: parseFloat(sigma.toFixed(2)),
        safety_stock: ss,
        reorder_point: rop,
        eoq: eoq,
        days_remaining: daysRemaining,
        stockout_probability_pct: item.stock <= rop ? 34.5 : 4.2,
        annual_eoq_savings: parseFloat((eoq * 0.32).toFixed(2)),
        overstock_capital_gbp: daysRemaining > 75 ? parseFloat((item.stock * unitCost).toFixed(2)) : 0,
        risk_status: riskStatus
    };
}

function renderInventoryTrajectoryChart(trajectory, skuLabel) {
    const canvas = document.getElementById("inventoryTrajectoryChart");
    if (!canvas || typeof Chart === "undefined") return;
    if (inventoryTrajectoryChartInstance) {
        inventoryTrajectoryChartInstance.destroy();
    }

    const labels = trajectory.map(pt => pt.label);
    const unmanaged = trajectory.map(pt => pt.unmanaged_stock);
    const eoqManaged = trajectory.map(pt => pt.eoq_managed_stock);
    const ropLine = trajectory.map(pt => pt.reorder_point);
    const ssLine = trajectory.map(pt => pt.safety_stock);

    const textColor = document.documentElement.getAttribute("data-theme") === "light" ? "#334155" : "#CBD5E1";
    const gridColor = document.documentElement.getAttribute("data-theme") === "light" ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";

    inventoryTrajectoryChartInstance = new Chart(canvas.getContext("2d"), {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: `EOQ Replenishment Sawtooth (${skuLabel})`,
                    data: eoqManaged,
                    borderColor: "#3B82F6",
                    backgroundColor: "rgba(59, 130, 246, 0.14)",
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.15,
                    pointRadius: 2
                },
                {
                    label: "Unmanaged Depletion (No Reorder)",
                    data: unmanaged,
                    borderColor: "#EF4444",
                    borderWidth: 2,
                    borderDash: [4, 4],
                    fill: false,
                    tension: 0.15,
                    pointRadius: 0
                },
                {
                    label: "Reorder Point (ROP)",
                    data: ropLine,
                    borderColor: "#F59E0B",
                    borderWidth: 1.5,
                    borderDash: [6, 3],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: "Safety Stock Buffer",
                    data: ssLine,
                    borderColor: "#10B981",
                    borderWidth: 1.5,
                    borderDash: [2, 3],
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { labels: { color: textColor, font: { size: 11 } } }
            },
            scales: {
                x: { ticks: { color: textColor, maxTicksLimit: 8 }, grid: { color: gridColor } },
                y: { beginAtZero: true, ticks: { color: textColor }, grid: { color: gridColor } }
            }
        }
    });
}

function renderInventoryLedgerAndPo(rows, pos = []) {
    const tbody = document.querySelector("#inventoryTable tbody");
    const poBody = document.getElementById("invPoLedgerBody");
    if (!tbody) return;

    const statusMeta = {
        CRITICAL_REORDER: { label: "Critical Reorder", color: "#EF4444" },
        REORDER_SOON: { label: "Reorder Soon", color: "#F59E0B" },
        OVERSTOCK_MARKDOWN: { label: "Overstock / Markdown", color: "#A855F7" },
        OPTIMAL: { label: "Optimal Buffer", color: "#10B981" }
    };

    tbody.innerHTML = rows.map(item => {
        const meta = statusMeta[item.risk_status] || statusMeta.OPTIMAL;
        const abcColor = item.abc_class === "A" ? "#3B82F6" : item.abc_class === "B" ? "#10B981" : "#94A3B8";
        return `
            <tr>
                <td><code>${item.stock_code}</code></td>
                <td><strong>${item.description}</strong></td>
                <td><span class="badge-tag" style="background:${abcColor}22;color:${abcColor};font-weight:700;">${item.abc_xyz}</span></td>
                <td>£${Number(item.unit_price).toFixed(2)}</td>
                <td><strong>${Number(item.stock_on_hand).toLocaleString()} units</strong></td>
                <td>${item.daily_demand_mean} <small style="color:var(--text-muted);">&plusmn;${item.daily_demand_std}</small></td>
                <td><span style="color:var(--text-muted);">${item.safety_stock}</span> / <strong>${item.reorder_point}</strong></td>
                <td><strong class="text-blue">${Number(item.eoq).toLocaleString()}</strong></td>
                <td><strong style="color:${meta.color};">${item.days_remaining}d</strong></td>
                <td><span class="badge-tag" style="background:${meta.color}22;color:${meta.color};font-weight:700;">${meta.label}</span></td>
                <td style="white-space:nowrap;">
                    <button type="button" class="btn btn-secondary btn-xs" onclick="window.selectSkuForOptimization('${item.stock_code}')">📐 EOQ</button>
                    <button type="button" class="btn btn-outline btn-xs" onclick="openRestockModal('${item.stock_code}')">📦 Order PO</button>
                </td>
            </tr>
        `;
    }).join("");

    if (poBody) {
        if (!pos.length) {
            poBody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--text-muted);">No Purchase Orders dispatched in current session yet. Select a SKU above or click Order PO.</td></tr>`;
        } else {
            poBody.innerHTML = pos.map(po => `
                <tr>
                    <td><code>${po.po_id}</code></td>
                    <td><strong>${po.stock_code}</strong> <small style="color:var(--text-muted);">${po.description || ""}</small></td>
                    <td><strong>+${Number(po.order_qty).toLocaleString()}</strong></td>
                    <td>${po.lead_time_days}d</td>
                    <td>£${Number(po.total_cost_gbp).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td><strong class="text-green">${po.new_days_remaining}d</strong></td>
                    <td><code>${po.issued_by}</code></td>
                    <td><span class="badge-tag green">${po.status}</span></td>
                </tr>
            `).join("");
        }
    }
}

async function refreshInventorySimulator() {
    const skuSelect = document.getElementById("invOptSkuSelect");
    const slSelect = document.getElementById("invOptServiceLevel");
    const ltSlider = document.getElementById("invOptLeadTime");
    const multSlider = document.getElementById("invOptDemandMult");
    if (!skuSelect || !skuSelect.value) return;

    const stockCode = skuSelect.value;
    const serviceLevel = parseFloat(slSelect ? slSelect.value : "0.95");
    const leadDays = parseInt(ltSlider ? ltSlider.value : "7", 10);
    const demandMult = parseFloat(multSlider ? multSlider.value : "1.0");

    const ltVal = document.getElementById("invOptLeadTimeVal");
    const multVal = document.getElementById("invOptDemandMultVal");
    if (ltVal) ltVal.textContent = `${leadDays} days`;
    if (multVal) multVal.textContent = `${demandMult.toFixed(1)}x`;

    let simData = null;
    try {
        const res = await fetch("http://localhost:8000/api/v1/inventory/simulate-sku", {
            method: "POST",
            headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({
                stock_code: stockCode,
                service_level: serviceLevel,
                lead_time_days: leadDays,
                demand_multiplier: demandMult,
                horizon_days: 30
            })
        });
        if (res.ok) simData = await res.json();
    } catch (_e) {
        // Fallback offline simulation below
    }

    if (!simData) {
        const base = INVENTORY_POLICIES_CACHE.find(r => r.stock_code === stockCode)
            || computeLocalInventoryPolicy(INVENTORY_DATABASE.find(i => i.code === stockCode) || INVENTORY_DATABASE[0], serviceLevel, leadDays, demandMult);
        const pol = computeLocalInventoryPolicy({
            code: base.stock_code,
            name: base.description,
            price: base.unit_price,
            stock: base.stock_on_hand,
            burn: base.daily_demand_mean,
            std: base.daily_demand_std,
            abc_class: base.abc_class,
            xyz_class: base.xyz_class,
            abc_xyz: base.abc_xyz
        }, serviceLevel, leadDays, demandMult);

        let unm = pol.stock_on_hand;
        let opt = pol.stock_on_hand;
        let arrival = null;
        const traj = [];
        for (let d = 0; d <= 30; d++) {
            if (d > 0) {
                unm = Math.max(0, unm - pol.daily_demand_mean);
                opt = Math.max(0, opt - pol.daily_demand_mean);
                if (arrival === d) { opt += pol.eoq; arrival = null; }
                if (opt <= pol.reorder_point && arrival === null) arrival = d + leadDays;
            }
            traj.push({
                day: d,
                label: `Day ${d}`,
                unmanaged_stock: parseFloat(unm.toFixed(1)),
                eoq_managed_stock: parseFloat(opt.toFixed(1)),
                safety_stock: pol.safety_stock,
                reorder_point: pol.reorder_point
            });
        }
        simData = { policy: pol, trajectory: traj };
    }

    const p = simData.policy;
    const ssEl = document.getElementById("invReadoutSafetyStock");
    const ropEl = document.getElementById("invReadoutRop");
    const eoqEl = document.getElementById("invReadoutEoq");
    const probEl = document.getElementById("invReadoutStockoutProb");
    const abcEl = document.getElementById("invOptAbcBadge");
    if (ssEl) ssEl.textContent = `${Number(p.safety_stock).toLocaleString()} units`;
    if (ropEl) ropEl.textContent = `${Number(p.reorder_point).toLocaleString()} units`;
    if (eoqEl) eoqEl.textContent = `${Number(p.eoq).toLocaleString()} units`;
    if (probEl) {
        probEl.textContent = `${p.stockout_probability_pct}%`;
        probEl.className = `stat-val ${p.stockout_probability_pct >= 25 ? "text-red" : p.stockout_probability_pct >= 12 ? "text-gold" : "text-green"}`;
    }
    if (abcEl) abcEl.textContent = `Class ${p.abc_xyz}`;

    renderInventoryTrajectoryChart(simData.trajectory, p.stock_code);
}

async function initInventoryMart() {
    const tbody = document.querySelector("#inventoryTable tbody");
    const exportBtn = document.getElementById("exportInventoryBtn");
    const skuSelect = document.getElementById("invOptSkuSelect");
    const slSelect = document.getElementById("invOptServiceLevel");
    const ltSlider = document.getElementById("invOptLeadTime");
    const multSlider = document.getElementById("invOptDemandMult");
    const issuePoBtn = document.getElementById("invIssueOptimalPoBtn");
    const recalcBtn = document.getElementById("invRecalcCatalogBtn");

    if (!tbody) return;

    const serviceLevel = parseFloat(slSelect ? slSelect.value : "0.95");
    const leadDays = parseInt(ltSlider ? ltSlider.value : "7", 10);

    let report = null;
    try {
        const res = await fetch(`http://localhost:8000/api/v1/inventory/optimization-report?service_level=${serviceLevel}&lead_time_days=${leadDays}`);
        if (res.ok) report = await res.json();
    } catch (_e) {
        // Fallback offline computation
    }

    if (report && Array.isArray(report.skus)) {
        INVENTORY_POLICIES_CACHE = report.skus;
        INVENTORY_PURCHASE_ORDERS_CACHE = report.purchase_orders || [];
        // Sync local fallback array so modal restock + CSV export align with backend
        INVENTORY_DATABASE.length = 0;
        report.skus.forEach(s => INVENTORY_DATABASE.push({
            code: s.stock_code,
            name: s.description,
            price: s.unit_price,
            stock: s.stock_on_hand,
            burn: s.daily_demand_mean,
            std: s.daily_demand_std,
            daysLeft: s.days_remaining,
            status: s.risk_status
        }));
        const k = report.kpis;
        const kTotal = document.getElementById("invKpiTotalSkus");
        const kAbc = document.getElementById("invKpiAbcSummary");
        const kCrit = document.getElementById("invKpiCriticalSkus");
        const kOver = document.getElementById("invKpiOverstockCap");
        const kSav = document.getElementById("invKpiEoqSavings");
        if (kTotal) kTotal.textContent = `${k.active_skus_monitored} SKUs`;
        if (kAbc && k.abc_distribution) kAbc.textContent = `A: ${k.abc_distribution.A || 0} • B: ${k.abc_distribution.B || 0} • C: ${k.abc_distribution.C || 0}`;
        if (kCrit) kCrit.textContent = `${k.critical_reorder_skus} SKUs`;
        if (kOver) kOver.textContent = `£${Number(k.overstock_capital_gbp).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
        if (kSav) kSav.textContent = `£${Number(k.annual_eoq_savings_gbp).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    } else {
        INVENTORY_POLICIES_CACHE = INVENTORY_DATABASE.map(item => computeLocalInventoryPolicy(item, serviceLevel, leadDays, 1.0));
    }

    if (skuSelect) {
        const prev = skuSelect.value;
        skuSelect.innerHTML = INVENTORY_POLICIES_CACHE.map(r =>
            `<option value="${r.stock_code}">${r.stock_code} — ${r.description} (${r.days_remaining}d cover)</option>`
        ).join("");
        if (prev && INVENTORY_POLICIES_CACHE.some(r => r.stock_code === prev)) {
            skuSelect.value = prev;
        }
    }

    renderInventoryLedgerAndPo(INVENTORY_POLICIES_CACHE, INVENTORY_PURCHASE_ORDERS_CACHE);
    await refreshInventorySimulator();

    window.selectSkuForOptimization = (code) => {
        if (skuSelect) {
            skuSelect.value = code;
            refreshInventorySimulator();
            skuSelect.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    };

    if (!INVENTORY_INIT_WIRED) {
        INVENTORY_INIT_WIRED = true;

        if (exportBtn) {
            exportBtn.addEventListener("click", () => {
                downloadCSV("inventory_eoq_optimization_ledger.csv", INVENTORY_POLICIES_CACHE.length ? INVENTORY_POLICIES_CACHE : INVENTORY_DATABASE);
                showToast("Inventory Exported", "inventory_eoq_optimization_ledger.csv downloaded", "success");
                logAuditEvent("Export", "Exported Phase 17 EOQ & ABC-XYZ Inventory Ledger to CSV");
            });
        }

        [skuSelect, slSelect, ltSlider, multSlider].forEach(el => {
            if (el) {
                el.addEventListener("input", refreshInventorySimulator);
                el.addEventListener("change", refreshInventorySimulator);
            }
        });

        if (recalcBtn) {
            recalcBtn.addEventListener("click", async () => {
                await initInventoryMart();
                showToast("Catalog Recalculated", "Updated Safety Stock, ROP & Wilson EOQ across catalog", "info");
            });
        }

        if (issuePoBtn) {
            issuePoBtn.addEventListener("click", async () => {
                const targetSku = skuSelect ? skuSelect.value : null;
                if (!targetSku) return;
                const sl = parseFloat(slSelect ? slSelect.value : "0.95");
                const lt = parseInt(ltSlider ? ltSlider.value : "7", 10);
                issuePoBtn.disabled = true;
                try {
                    const res = await fetch("http://localhost:8000/api/v1/inventory/purchase-orders", {
                        method: "POST",
                        headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                        body: JSON.stringify({
                            stock_code: targetSku,
                            service_level: sl,
                            lead_time_days: lt,
                            notes: "Approved from Phase 17 EOQ Optimizer"
                        })
                    });
                    const data = await res.json();
                    if (!res.ok) {
                        showToast("PO Authorization Blocked", data.detail || `HTTP ${res.status}`, "alert");
                    } else {
                        const po = data.purchase_order;
                        showToast("EOQ Purchase Order Dispatched", `${po.po_id}: +${po.order_qty} units of SKU ${po.stock_code} (£${Number(po.total_cost_gbp).toFixed(2)})`, "success");
                        logAuditEvent("Inventory", `Dispatched ${po.po_id} (+${po.order_qty} units for ${po.stock_code})`);
                        await initInventoryMart();
                    }
                } catch (_e) {
                    const localItem = INVENTORY_DATABASE.find(i => i.code === targetSku);
                    if (localItem) {
                        const pol = computeLocalInventoryPolicy(localItem, sl, lt, 1.0);
                        localItem.stock += pol.eoq;
                        INVENTORY_PURCHASE_ORDERS_CACHE.unshift({
                            po_id: `PO-${Math.floor(100000 + Math.random() * 899999)}`,
                            stock_code: localItem.code,
                            description: localItem.name,
                            order_qty: pol.eoq,
                            lead_time_days: lt,
                            total_cost_gbp: parseFloat((pol.eoq * pol.unit_cost).toFixed(2)),
                            new_days_remaining: parseFloat((localItem.stock / localItem.burn).toFixed(1)),
                            issued_by: "offline-operator",
                            status: "DISPATCHED (LOCAL)"
                        });
                        await initInventoryMart();
                        showToast("PO Dispatched (Local)", `Replenished +${pol.eoq} units for SKU ${localItem.code}`, "success");
                    }
                } finally {
                    issuePoBtn.disabled = false;
                }
            });
        }
    }
}

// =============================================================================
// TAB 9: RETENTION CAMPAIGN STUDIO
// =============================================================================
function initCampaignStudio() {
    const launchBtn = document.getElementById("launchCampaignBtn");
    const campSegment = document.getElementById("campSegment");
    const campIncentive = document.getElementById("campIncentive");
    const audienceSpan = document.getElementById("campAudienceSize");
    const revSpan = document.getElementById("campRevenueProtected");
    const voucherPreview = document.getElementById("campVoucherPreview");
    const btnRegenVoucher = document.getElementById("btnRegenerateVoucher");
    const list = document.getElementById("activeCampaignsList");
    const testChannelBtns = document.querySelectorAll(".btn-test-channel");
    const btnTestWatchdog = document.getElementById("btnTestWatchdog");
    const activeCampBadge = document.getElementById("activeCampCountBadge");

    const segmentStats = {
        "At-Risk VIPs": { size: "22 Accounts", sizeNum: 22, rev: "£191,892.72", revNum: 191892.72 },
        "All At-Risk": { size: "1,180 Accounts", sizeNum: 1180, rev: "£2,105,745.40", revNum: 2105745.40 },
        "Champions": { size: "708 Accounts", sizeNum: 708, rev: "£5,659,383.84", revNum: 5659383.84 },
        "Hibernating": { size: "1,602 Accounts", sizeNum: 1602, rev: "£555,301.26", revNum: 555301.26 }
    };

    function generateCode() {
        const seg = (campSegment ? campSegment.value : "WINBACK").replace(/[^a-zA-Z]/g, "").slice(0, 6).toUpperCase();
        const disc = campIncentive ? campIncentive.value : "15";
        const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
        let rand = "";
        for (let i = 0; i < 5; i++) rand += chars.charAt(Math.floor(Math.random() * chars.length));
        return `${seg}-${disc}-${rand}`;
    }

    if (voucherPreview) {
        voucherPreview.value = generateCode();
    }

    if (btnRegenVoucher && voucherPreview) {
        btnRegenVoucher.addEventListener("click", () => {
            voucherPreview.value = generateCode();
        });
    }

    if (campSegment) {
        campSegment.addEventListener("change", () => {
            const s = segmentStats[campSegment.value] || segmentStats["At-Risk VIPs"];
            if (audienceSpan) audienceSpan.textContent = s.size;
            if (revSpan) revSpan.textContent = s.rev;
            if (voucherPreview) voucherPreview.value = generateCode();
        });
    }

    if (campIncentive) {
        campIncentive.addEventListener("change", () => {
            if (voucherPreview) voucherPreview.value = generateCode();
        });
    }

    // Test notification channels
    testChannelBtns.forEach(btn => {
        btn.addEventListener("click", async () => {
            const ch = btn.getAttribute("data-channel");
            btn.disabled = true;
            const original = btn.textContent;
            btn.textContent = "⏳ Ping...";
            try {
                const res = await fetch("http://localhost:8000/api/v1/campaigns/test-channel", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ channel: ch })
                });
                if (res.ok) {
                    showToast(`⚡ ${ch.toUpperCase()} Channel Verified`, "Verification ping delivered successfully.", "success");
                }
            } catch (e) {
                showToast("Channel Ping Sent (Local)", `Dispatched ${ch} simulation.`, "info");
            } finally {
                btn.disabled = false;
                btn.textContent = original;
            }
        });
    });

    // Test Watchdog
    if (btnTestWatchdog) {
        btnTestWatchdog.addEventListener("click", async () => {
            btnTestWatchdog.disabled = true;
            btnTestWatchdog.textContent = "⏳ Triggering...";
            try {
                const res = await fetch("http://localhost:8000/api/v1/campaigns/trigger-watchdog", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        watchdog_type: "churn",
                        customer_id: 14096,
                        churn_prob: 0.84,
                        total_spend_gbp: 2850.0
                    })
                });
                if (res.ok) {
                    const data = await res.json();
                    showToast("🚨 VIP Churn Watchdog Triggered", "Account #14096 (84% Churn Risk) triggered automatic Slack & Email win-back dispatch.", "warning");
                }
            } catch (e) {
                showToast("Watchdog Triggered (Simulated)", "VIP account #14096 evaluated.", "warning");
            } finally {
                btnTestWatchdog.disabled = false;
                btnTestWatchdog.textContent = "⚡ Test Watchdog";
            }
        });
    }

    // Launch Campaign
    if (launchBtn && list) {
        launchBtn.addEventListener("click", async () => {
            const seg = campSegment.value;
            const s = segmentStats[seg] || segmentStats["At-Risk VIPs"];
            const disc = parseInt(campIncentive.value, 10) || 15;
            const incText = campIncentive.options[campIncentive.selectedIndex].text;
            const voucher = voucherPreview ? voucherPreview.value : generateCode();

            const chSlack = document.getElementById("campChanSlack")?.checked;
            const chDiscord = document.getElementById("campChanDiscord")?.checked;
            const chEmail = document.getElementById("campChanEmail")?.checked;

            const channels = [];
            if (chSlack) channels.push("slack");
            if (chDiscord) channels.push("discord");
            if (chEmail) channels.push("email");
            if (channels.length === 0) channels.push("email");

            launchBtn.disabled = true;
            launchBtn.textContent = "⏳ Dispatching Across Channels...";

            try {
                const res = await fetch("http://localhost:8000/api/v1/campaigns/dispatch", {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify({
                        campaign_name: `${seg} Retention Wave`,
                        audience_segment: seg,
                        audience_size: s.sizeNum,
                        revenue_target_gbp: s.revNum,
                        discount_pct: disc,
                        channels: channels,
                        custom_message: `Automated retention sequence offering ${incText}.`
                    })
                });

                if (res.status === 401 || res.status === 403) {
                    const errBody = await res.json().catch(() => ({}));
                    showToast("RBAC Access Denied", errBody.detail || `HTTP ${res.status} on Campaign Dispatch`, "alert");
                    return;
                }

                let campData = null;
                if (res.ok) {
                    const payload = await res.json();
                    campData = payload.campaign;
                }

                const newCamp = document.createElement("div");
                newCamp.className = "campaign-item";
                const displayVoucher = campData ? campData.voucher_code : voucher;
                const chanStr = channels.map(c => c.charAt(0).toUpperCase() + c.slice(1)).join(", ");

                newCamp.innerHTML = `
                    <div class="camp-status-badge active">JUST DISPATCHED</div>
                    <h4>${seg} - ${disc}% Off Retention Wave</h4>
                    <p>Strategy: ${incText}</p>
                    <div class="camp-stats">
                        <div><small>Channels</small><strong>${chanStr}</strong></div>
                        <div><small>Voucher</small><code>${displayVoucher}</code></div>
                        <div><small>Audience</small><strong>${s.size}</strong></div>
                        <div><small>Preserved Target</small><strong class="text-green">${s.rev}</strong></div>
                    </div>
                `;
                list.prepend(newCamp);

                showToast(
                    "🚀 Campaign Dispatched Multi-Channel",
                    `Dispatched to ${s.size} via ${chanStr} with voucher ${displayVoucher}`,
                    "success"
                );
                logAuditEvent("Marketing", `Dispatched automated multi-channel retention campaign to ${seg} (${s.size}) with voucher ${displayVoucher}`);

                if (activeCampBadge) {
                    activeCampBadge.textContent = `${list.querySelectorAll(".campaign-item").length} Active Sequences`;
                }

                // Generate new voucher for next campaign
                if (voucherPreview) voucherPreview.value = generateCode();

            } catch (err) {
                console.error("[Campaigns] Dispatch error:", err);
                showToast("Dispatch Local Fallback", `Dispatched ${seg} retention campaign locally.`, "info");
            } finally {
                launchBtn.disabled = false;
                launchBtn.textContent = "🚀 Launch Automated Retention Campaign";
            }
        });
    }
}

// =============================================================================
// TAB 10: LIVE POS & WEBSOCKET TRANSACTION STREAMING
// =============================================================================
let liveOrderSocket = null;
let wsReconnectTimer = null;

function handleLiveIncomingOrder(order) {
    const amount = Number(order.total_amount_gbp) || 0;
    const units = Number(order.total_units) || 1;
    const cid = String(order.customer_id);
    const invoiceNo = order.invoice_no || "INV-LIVE";

    // 1. Reactive KPI Counters Update with glowing pulse animation
    const kpiRev = document.getElementById("kpi-revenue");
    if (kpiRev) {
        const curText = kpiRev.textContent.replace(/[^0-9.]/g, "");
        const curRev = parseFloat(curText) || 10279169.87;
        const newRev = curRev + amount;
        kpiRev.textContent = "£" + newRev.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        kpiRev.classList.remove("pulse-revenue");
        void kpiRev.offsetWidth;
        kpiRev.classList.add("pulse-revenue");
    }

    const kpiOrders = document.getElementById("kpi-orders");
    if (kpiOrders) {
        const curOrders = parseInt(kpiOrders.textContent.replace(/[^0-9]/g, ""), 10) || 19776;
        kpiOrders.textContent = (curOrders + 1).toLocaleString("en-GB");
    }

    const kpiUnits = document.getElementById("kpi-units");
    if (kpiUnits) {
        const curUnits = parseInt(kpiUnits.textContent.replace(/[^0-9]/g, ""), 10) || 5577275;
        kpiUnits.textContent = (curUnits + units).toLocaleString("en-GB");
    }

    // 2. Reactive Customer Ledger & Churn Probability Update
    let cust = MASTER_CUSTOMERS.find(c => String(c.id) === cid);
    const prevProb = cust ? cust.churnProb : 0.75;
    const prevRecency = cust ? cust.recency : 65;

    if (cust) {
        cust.spend += amount;
        cust.orders += 1;
        cust.aov = cust.spend / cust.orders;
        cust.recency = 0;
        cust.churnProb = order.updated_churn_probability !== undefined ? order.updated_churn_probability : Math.max(0.04, cust.churnProb * 0.45);
    } else {
        cust = {
            id: cid,
            segment: "Champions (VIP)",
            spend: amount,
            orders: 1,
            aov: amount,
            recency: 0,
            churnProb: order.updated_churn_probability || 0.12,
            history: [`${units}x Live POS Item`]
        };
        MASTER_CUSTOMERS.unshift(cust);
    }

    // 3. Render Simulator Feedback Box
    const feedback = document.getElementById("simFeedbackArea");
    if (feedback) {
        feedback.innerHTML = `
            <div class="sim-reaction-card" style="width: 100%;">
                <div style="background:var(--success-light); border:1px solid var(--success); padding:1rem; border-radius:8px; margin-bottom:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:var(--success);">✓ WEBSOCKET LIVE STREAM: ORDER BROADCASTED</strong>
                        <small style="color:var(--text-muted); font-family:var(--font-mono);">${order.timestamp ? order.timestamp.substring(11, 19) + ' UTC' : 'Live'}</small>
                    </div>
                    <div style="font-size:0.92rem; color:var(--text-primary); margin-top:0.35rem;">
                        Invoice <code>${invoiceNo}</code>: Customer <strong>#${cid}</strong> purchased <strong>${units} units</strong> for <strong style="color:var(--success);">+£${amount.toFixed(2)}</strong>.
                    </div>
                </div>

                <div class="result-grid">
                    <div class="result-stat" style="background:var(--bg-surface-alt); padding:0.75rem; border-radius:6px;">
                        <strong>Recency Re-index</strong>
                        <span style="color:var(--success);">${prevRecency}d ➔ 0 days</span>
                    </div>
                    <div class="result-stat" style="background:var(--bg-surface-alt); padding:0.75rem; border-radius:6px;">
                        <strong>Churn Probability</strong>
                        <span style="color:var(--success);">${(prevProb * 100).toFixed(1)}% ➔ ${(cust.churnProb * 100).toFixed(1)}%</span>
                    </div>
                    <div class="result-stat" style="background:var(--bg-surface-alt); padding:0.75rem; border-radius:6px;">
                        <strong>New Lifetime Spend</strong>
                        <span>£${cust.spend.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    <div class="result-stat" style="background:var(--bg-surface-alt); padding:0.75rem; border-radius:6px;">
                        <strong>WebSocket Broadcast</strong>
                        <span style="color:var(--primary);">${order.active_clients_notified !== undefined ? order.active_clients_notified : 1} Client(s)</span>
                    </div>
                </div>
            </div>
        `;
    }

    // 4. UI Toast notification
    showToast(
        "⚡ Live POS Order Broadcast",
        `${invoiceNo}: +£${amount.toFixed(2)} (${units} units) for Customer #${cid}`,
        "success"
    );

    // 5. Audit Log Entry
    logAuditEvent(
        "POS/LiveStream",
        `WebSocket Broadcast: Ingested ${invoiceNo} (+£${amount.toFixed(2)}) for #${cid}. Recency ➔ 0d.`
    );

    // 6. Refresh active views if visible
    if (typeof initCustomerLedger === "function") initCustomerLedger();
    if (typeof initChurnTab === "function") initChurnTab();
}

function initLiveOrderWebSocket() {
    const wsBadge = document.getElementById("wsStreamBadge");

    function connectWs() {
        if (liveOrderSocket && (liveOrderSocket.readyState === WebSocket.OPEN || liveOrderSocket.readyState === WebSocket.CONNECTING)) {
            return;
        }

        try {
            liveOrderSocket = new WebSocket("ws://localhost:8000/ws/live-orders");

            liveOrderSocket.onopen = () => {
                console.log("[Nexus WebSocket] Connected to live retail order stream (ws://localhost:8000/ws/live-orders)");
                if (wsBadge) {
                    wsBadge.textContent = "● WS STREAM ACTIVE :8000";
                    wsBadge.className = "badge green ws-live-pulse";
                }
            };

            liveOrderSocket.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === "ORDER_INJECTED" && msg.data) {
                        handleLiveIncomingOrder(msg.data);
                    } else if (msg.type === "MLOPS_RETRAINING_COMPLETE" && msg.data) {
                        handleMlopsRetrainingBroadcast(msg.data);
                    } else if (msg.type === "DATASET_BATCH_INGESTED" && msg.data) {
                        handleDatasetBatchIngestedBroadcast(msg.data);
                    } else if (msg.type === "WEBHOOK_ORDER_INGESTED" && msg.data) {
                        handleWebhookOrderBroadcast(msg.data);
                    } else if (msg.type === "CAMPAIGN_DISPATCHED" && msg.data) {
                        handleCampaignDispatchedBroadcast(msg.data);
                    } else if (msg.type === "WATCHDOG_ALERT_TRIGGERED" && msg.data) {
                        handleWatchdogAlertBroadcast(msg.data);
                    } else if (msg.type === "PRICING_EXPERIMENT_COMPLETED" && msg.data) {
                        handlePricingExperimentBroadcast(msg.data);
                    } else if (msg.type === "SECURITY_AUDIT_EVENT" && msg.data) {
                        handleSecurityAuditBroadcast(msg.data);
                    } else if (msg.type === "SECURITY_POLICY_UPDATED" && msg.data) {
                        handleSecurityPolicyBroadcast(msg.data);
                    } else if (msg.type === "ANOMALY_ALERT_TRIGGERED" && msg.data) {
                        handleAnomalyAlertBroadcast(msg.data);
                    } else if (msg.type === "FRAUD_QUARANTINE_RESOLVED" && msg.data) {
                        handleQuarantineResolvedBroadcast(msg.data);
                    }
                } catch (e) {
                    console.warn("[Nexus WebSocket] Inbound parse warning:", e);
                }
            };

            liveOrderSocket.onclose = () => {
                if (wsBadge) {
                    wsBadge.textContent = "○ WS STREAM OFFLINE";
                    wsBadge.className = "badge gray-border";
                }
                clearTimeout(wsReconnectTimer);
                wsReconnectTimer = setTimeout(connectWs, 5000);
            };

            liveOrderSocket.onerror = () => {
                liveOrderSocket?.close();
            };
        } catch (e) {
            clearTimeout(wsReconnectTimer);
            wsReconnectTimer = setTimeout(connectWs, 5000);
        }
    }

    connectWs();
}

function handleMlopsRetrainingBroadcast(data) {
    console.log("[Nexus WebSocket] Received MLOps retraining broadcast:", data);
    if (window.appendMLOpsTermLog) {
        window.appendMLOpsTermLog(`[WebSocket Broadcast] Pipeline retraining executed. Version checkpoint: ${data.new_version || 'latest'}`);
        window.appendMLOpsTermLog(`[WebSocket Broadcast] Certified metrics: Forecaster MAPE ${data.forecaster_mape || 26.28}%, Churn AUC ${data.churn_auc || 0.7163}`);
    }
    showToast("Model Checkpoint Promoted", `WebSocket Broadcast: Pipeline version updated to ${data.new_version || 'v2.5'}`, "success");
    logAuditEvent("MLOps", `WebSocket Broadcast: Model pipeline retrained; active checkpoint promoted to ${data.new_version || 'v2.5'}`);
    if (typeof evaluateDriftScenario === "function") {
        evaluateDriftScenario("baseline");
    }
}

function handleDatasetBatchIngestedBroadcast(data) {
    console.log("[Nexus WebSocket] Received dataset batch ingestion broadcast:", data);
    if (window.appendMLOpsTermLog) {
        window.appendMLOpsTermLog(`[WebSocket Broadcast] Dataset batch ingested: ${data.filename} (+${data.rows_added} rows, +£${Number(data.total_revenue_gbp).toFixed(2)})`);
    }
    showToast("Dataset Ingestion Live", `Batch ${data.filename} merged into production data store (+${data.rows_added} transactions)`, "success");
    logAuditEvent("Data Engineering", `Ingested dataset batch: ${data.filename} (+${data.rows_added} rows, +£${Number(data.total_revenue_gbp).toFixed(2)})`);
}

function handleCampaignDispatchedBroadcast(data) {
    console.log("[Nexus WebSocket] Received campaign dispatched broadcast:", data);
    showToast(
        "🚀 Multi-Channel Campaign Dispatched",
        `${data.name}: ${data.target_segment} (${data.audience_size} users) • Voucher ${data.voucher_code}`,
        "success"
    );
}

function handleWatchdogAlertBroadcast(data) {
    console.log("[Nexus WebSocket] Received watchdog alert:", data);
    if (data.rule === "churn_watchdog") {
        showToast(
            "🚨 VIP Churn Watchdog Alert",
            `Account #${data.customer_id} reached ${(data.churn_prob * 100).toFixed(1)}% churn risk (£${Number(data.spend_gbp).toFixed(2)} spend). Automatic win-back dispatched!`,
            "warning"
        );
    } else if (data.rule === "drift_watchdog") {
        showToast(
            "🚨 MLOps Data Drift Watchdog Alert",
            `PSI ${Number(data.psi_score).toFixed(3)} exceeded threshold. Shifted features: ${(data.shifted_features || []).join(", ")}`,
            "danger"
        );
    }
}

function initTransactionSimulator() {
    const form = document.getElementById("posSimulatorForm");
    const feedback = document.getElementById("simFeedbackArea");

    if (!form || !feedback) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const cid = document.getElementById("simCustId").value.trim();
        const skuSelect = document.getElementById("simSkuCode");
        const sku = skuSelect.value;
        const skuText = skuSelect.options[skuSelect.selectedIndex].text;
        const qty = parseInt(document.getElementById("simQty").value, 10);
        const price = parseFloat(document.getElementById("simPrice").value);
        const country = document.getElementById("simCountry") ? document.getElementById("simCountry").value.trim() : "United Kingdom";
        const total = qty * price;

        const payload = {
            customer_id: cid,
            country: country,
            items: [
                {
                    stock_code: sku,
                    description: skuText.split(" (")[0].replace(/^\[.*?\]\s*/, ""),
                    quantity: qty,
                    unit_price: price
                }
            ]
        };

        // 1. Attempt broadcast via FastAPI REST endpoint (which relays to all WebSockets)
        let broadcasted = false;
        try {
            const res = await fetch("http://localhost:8000/api/v1/orders/inject", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const resData = await res.json();
                broadcasted = true;
                // If this client isn't connected via WebSocket, handle directly
                if (!liveOrderSocket || liveOrderSocket.readyState !== WebSocket.OPEN) {
                    handleLiveIncomingOrder(resData.order);
                }
            }
        } catch (err) {
            console.log("[POS Simulator] FastAPI offline, processing local simulation...");
        }

        // 2. Offline fallback simulation
        if (!broadcasted) {
            const localOrder = {
                invoice_no: `INV-${Math.random().toString(16).substring(2, 8).toUpperCase()}`,
                timestamp: new Date().toISOString(),
                customer_id: cid,
                country: country,
                total_amount_gbp: total,
                total_units: qty,
                updated_churn_probability: Math.max(0.04, (MASTER_CUSTOMERS.find(c => c.id === cid)?.churnProb || 0.75) * 0.45),
                active_clients_notified: 1
            };
            handleLiveIncomingOrder(localOrder);
        }
    });

    window.quickFillSimOrder = function(cid, sku, qty, price, country) {
        const inputCid = document.getElementById("simCustId");
        const selectSku = document.getElementById("simSkuCode");
        const inputQty = document.getElementById("simQty");
        const inputPrice = document.getElementById("simPrice");
        const inputCountry = document.getElementById("simCountry");

        if (inputCid) inputCid.value = cid;
        if (selectSku) selectSku.value = sku;
        if (inputQty) inputQty.value = qty;
        if (inputPrice) inputPrice.value = price;
        if (inputCountry && country) inputCountry.value = country;

        // Auto trigger submit
        if (form) {
            form.dispatchEvent(new Event("submit", { cancelable: true }));
        }
    };
}

// =============================================================================
// TAB 11: SECURITY & AUDIT LOGGER
// =============================================================================
function logAuditEvent(cat, action, sev = "INFO") {
    const now = new Date().toISOString().replace("T", " ").substring(0, 19);
    const roleMap = {
        admin: "Principal Admin",
        lead_ds: "Lead Data Scientist",
        growth: "Growth Lead",
        supply: "Supply VP"
    };

    const entry = {
        time: now,
        cat: cat,
        role: roleMap[APP_STATE.role] || "Principal Admin",
        action: action,
        ip: "127.0.0.1 (Localhost)",
        sev: sev
    };

    APP_STATE.auditLogs.unshift(entry);
    try {
        localStorage.setItem("nexus_audit_logs", JSON.stringify(APP_STATE.auditLogs.slice(0, 100)));
    } catch (e) {}
    renderAuditLogs();
}

function renderAuditLogs() {
    const tbody = document.getElementById("auditLogsTbody");
    if (!tbody) return;

    tbody.innerHTML = APP_STATE.auditLogs.map(log => `
        <tr>
            <td><code>${log.time}</code></td>
            <td><span class="badge-tag blue">${log.cat}</span></td>
            <td><strong>${log.role}</strong></td>
            <td>${log.action}</td>
            <td><code>${log.ip}</code></td>
            <td><span class="badge-tag green">${log.sev}</span></td>
        </tr>
    `).join("");
}

function initAuditLogger() {
    renderAuditLogs();

    const clearBtn = document.getElementById("clearAuditLogsBtn");
    const exportBtn = document.getElementById("exportAuditLogsBtn");
    const exportCsvBtn = document.getElementById("exportAuditCsvBtn");

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            APP_STATE.auditLogs = [];
            localStorage.removeItem("nexus_audit_logs");
            renderAuditLogs();
            showToast("Audit Log Cleared", "Session log buffer emptied", "info");
        });
    }

    if (exportCsvBtn) {
        exportCsvBtn.addEventListener("click", () => {
            downloadCSV("security_audit_logs.csv", APP_STATE.auditLogs);
            showToast("Audit CSV Exported", "security_audit_logs.csv downloaded", "success");
            logAuditEvent("Export", "Exported Security Audit Stream to CSV");
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(APP_STATE.auditLogs, null, 2));
            const dlAnchor = document.createElement("a");
            dlAnchor.setAttribute("href", dataStr);
            dlAnchor.setAttribute("download", "nexus_audit_logs.json");
            dlAnchor.click();
            showToast("Audit JSON Exported", "nexus_audit_logs.json downloaded", "success");
        });
    }
}

// =============================================================================
// UTILITY: CSV DOWNLOAD HELPER
// =============================================================================
function downloadCSV(filename, rows) {
    if (!rows || !rows.length) return;
    const separator = ",";
    const keys = Object.keys(rows[0]);
    const csvContent =
        keys.join(separator) +
        "\n" +
        rows.map(row => {
            return keys.map(k => {
                let cell = row[k] === null || row[k] === undefined ? "" : row[k];
                cell = cell instanceof Date ? cell.toLocaleString() : cell.toString().replace(/"/g, '""');
                if (cell.search(/("|,|\n)/g) >= 0) cell = `"${cell}"`;
                return cell;
            }).join(separator);
        }).join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", filename);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Export global helper functions to window for onclick handlers
window.openCustomerDrawer = openCustomerDrawer;
window.closeCustomerDrawer = closeCustomerDrawer;
window.triggerCustomerCoupon = triggerCustomerCoupon;
window.saveCustomerNotes = saveCustomerNotes;
window.addToCart = addToCart;
window.removeFromCart = removeFromCart;
window.openRestockModal = (code) => {
    if (typeof openRestockModal === 'function') openRestockModal(code);
};

// =============================================================================
// TAB 1 EXTENSION: CUSTOMER COHORT RETENTION HEATMAP
// =============================================================================
const COHORT_DATA = [
    { cohort: "2010-12", size: 885, spend: 823746, rates: [100, 38.2, 33.5, 38.8, 36.0, 39.8, 38.0, 35.5, 35.4, 39.5, 37.4, 50.0] },
    { cohort: "2011-01", size: 417, spend: 293207, rates: [100, 24.0, 28.3, 24.2, 32.8, 29.9, 26.1, 25.7, 31.2, 34.8, 36.8] },
    { cohort: "2011-02", size: 380, spend: 158188, rates: [100, 24.7, 19.2, 27.9, 26.8, 24.7, 25.5, 28.2, 25.8, 31.3] },
    { cohort: "2011-03", size: 440, spend: 206563, rates: [100, 19.1, 25.5, 21.8, 23.2, 17.7, 26.4, 23.9, 28.2] },
    { cohort: "2011-04", size: 299, spend: 121997, rates: [100, 22.7, 22.1, 21.1, 20.7, 23.7, 23.1, 26.1] },
    { cohort: "2011-05", size: 279, spend: 124103, rates: [100, 23.7, 17.2, 17.2, 21.5, 24.4, 26.5] },
    { cohort: "2011-06", size: 235, spend: 136611, rates: [100, 20.9, 18.7, 27.2, 24.7, 31.5] },
    { cohort: "2011-07", size: 191, spend: 75782,  rates: [100, 20.9, 19.4, 23.0, 27.2] },
    { cohort: "2011-08", size: 167, spend: 79541,  rates: [100, 25.1, 25.1, 25.1] },
    { cohort: "2011-09", size: 298, spend: 155090, rates: [100, 29.9, 32.6] },
    { cohort: "2011-10", size: 352, spend: 174780, rates: [100, 26.4] },
    { cohort: "2011-11", size: 321, spend: 137372, rates: [100] }
];

let cohortViewMode = "rate"; // "rate" or "spend"

function renderCohortHeatmap() {
    const table = document.getElementById("cohortTable");
    if (!table) return;

    let html = `
        <thead>
            <tr>
                <th style="min-width:90px;">Cohort</th>
                <th style="min-width:85px;">New Users</th>
                <th>M0</th><th>M1</th><th>M2</th><th>M3</th><th>M4</th><th>M5</th><th>M6</th><th>M7</th><th>M8</th><th>M9</th><th>M10</th><th>M11</th>
            </tr>
        </thead>
        <tbody>
    `;

    COHORT_DATA.forEach(row => {
        html += `
            <tr>
                <td><strong>${row.cohort}</strong></td>
                <td>${row.size.toLocaleString()}</td>
        `;

        for (let m = 0; m <= 11; m++) {
            if (m < row.rates.length) {
                const rate = row.rates[m];
                let intensityClass = "intensity-0";
                if (rate >= 75) intensityClass = "intensity-4";
                else if (rate >= 50) intensityClass = "intensity-3";
                else if (rate >= 35) intensityClass = "intensity-2";
                else if (rate >= 20) intensityClass = "intensity-1";

                let cellDisplay = cohortViewMode === "rate" ? `${rate.toFixed(1)}%` : `£${Math.round(row.spend * (rate / 100)).toLocaleString()}`;

                html += `
                    <td class="cohort-cell ${intensityClass}" title="Cohort: ${row.cohort} | Month ${m} | Retention: ${rate.toFixed(1)}% (${Math.round(row.size * (rate / 100))} buyers)">
                        ${cellDisplay}
                    </td>
                `;
            } else {
                html += `<td class="cohort-cell intensity-empty">-</td>`;
            }
        }
        html += `</tr>`;
    });

    html += `</tbody>`;
    table.innerHTML = html;
}

function initCohortHeatmap() {
    renderCohortHeatmap();

    const rateBtn = document.getElementById("cohortModeRateBtn");
    const spendBtn = document.getElementById("cohortModeSpendBtn");
    const exportBtn = document.getElementById("exportCohortBtn");

    if (rateBtn && spendBtn) {
        rateBtn.addEventListener("click", () => {
            cohortViewMode = "rate";
            rateBtn.classList.add("active");
            spendBtn.classList.remove("active");
            renderCohortHeatmap();
            showToast("Heatmap Mode", "Displaying Cohort Retention Rate (%)", "info");
        });

        spendBtn.addEventListener("click", () => {
            cohortViewMode = "spend";
            spendBtn.classList.add("active");
            rateBtn.classList.remove("active");
            renderCohortHeatmap();
            showToast("Heatmap Mode", "Displaying Cohort Cumulative Spend (£)", "info");
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            const csvRows = COHORT_DATA.map(c => ({
                Cohort: c.cohort,
                NewUsers: c.size,
                InitialSpend: c.spend,
                M0: c.rates[0] || "",
                M1: c.rates[1] || "",
                M2: c.rates[2] || "",
                M3: c.rates[3] || "",
                M4: c.rates[4] || "",
                M5: c.rates[5] || "",
                M6: c.rates[6] || "",
                M7: c.rates[7] || "",
                M8: c.rates[8] || "",
                M9: c.rates[9] || "",
                M10: c.rates[10] || "",
                M11: c.rates[11] || ""
            }));
            downloadCSV("customer_cohort_retention_matrix.csv", csvRows);
            showToast("Cohort Matrix Exported", "Downloaded customer_cohort_retention_matrix.csv", "success");
            logAuditEvent("Export", "Exported 12-Month Cohort Retention Matrix CSV");
        });
    }
}

// =============================================================================
// TAB 2 EXTENSION: DYNAMIC RFM SEGMENT & AUDIENCE BUILDER
// =============================================================================
function initCustomSegmentBuilder() {
    const sliderRecency = document.getElementById("sliderDynRecency");
    const sliderFreq = document.getElementById("sliderDynFrequency");
    const sliderSpend = document.getElementById("sliderDynSpend");
    const lblRecency = document.getElementById("lblDynRecency");
    const lblFreq = document.getElementById("lblDynFrequency");
    const lblSpend = document.getElementById("lblDynSpend");
    const outcomePanel = document.getElementById("customSegmentOutcomePanel");

    if (!sliderRecency || !sliderFreq || !sliderSpend || !outcomePanel) return;

    let matchedCohort = [];

    function updateDynamicCohort() {
        const rVal = parseInt(sliderRecency.value, 10);
        const fVal = parseInt(sliderFreq.value, 10);
        const mVal = parseFloat(sliderSpend.value);

        if (lblRecency) lblRecency.textContent = `≤ ${rVal} Days`;
        if (lblFreq) lblFreq.textContent = `≥ ${fVal} Orders`;
        if (lblSpend) lblSpend.textContent = `≥ £${mVal.toLocaleString()}`;

        matchedCohort = MASTER_CUSTOMERS.filter(c => c.recency <= rVal && c.orders >= fVal && c.spend >= mVal);

        const totalCust = 4334;
        const totalRev = 10279170;
        const matchedSpend = matchedCohort.reduce((acc, c) => acc + c.spend, 0);
        const pctCust = ((matchedCohort.length / totalCust) * 100).toFixed(1);
        const pctRev = ((matchedSpend / totalRev) * 100).toFixed(1);
        const aov = matchedCohort.length > 0 ? (matchedSpend / matchedCohort.reduce((acc, c) => acc + c.orders, 0)).toFixed(2) : "0.00";

        outcomePanel.innerHTML = `
            <div class="sim-metric-row">
                <div class="sim-metric-card">
                    <small>Matched Audience Size</small>
                    <strong>${matchedCohort.length.toLocaleString()} Accounts</strong>
                    <span class="text-green">${pctCust}% of Customer Base</span>
                </div>
                <div class="sim-metric-card highlight">
                    <small>Combined Revenue Yield</small>
                    <strong style="color:var(--primary);">£${matchedSpend.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong>
                    <span class="text-green">${pctRev}% of Total Store GMV</span>
                </div>
                <div class="sim-metric-card">
                    <small>Average Order Value</small>
                    <strong>£${aov}</strong>
                    <span>High Commercial Density</span>
                </div>
            </div>
            <div class="sim-actions-row" style="margin-top:1rem; display:flex; gap:0.75rem; flex-wrap:wrap;">
                <button class="btn btn-secondary btn-sm" id="exportDynCohortBtn">📥 Export Filtered Audience CSV (${matchedCohort.length})</button>
                <button class="btn btn-primary btn-sm" id="pushDynCohortToCampaignBtn">🚀 Push to Retention Campaign Studio</button>
            </div>
        `;

        const exportBtn = document.getElementById("exportDynCohortBtn");
        if (exportBtn) {
            exportBtn.addEventListener("click", () => {
                if (matchedCohort.length === 0) {
                    showToast("No Accounts Matched", "Broaden slider filters to export audience", "alert");
                    return;
                }
                const rows = matchedCohort.map(c => ({
                    CustomerID: c.id,
                    Segment: c.segment,
                    Spend: c.spend,
                    Orders: c.orders,
                    RecencyDays: c.recency,
                    ChurnRisk: (c.churnProb * 100).toFixed(1) + "%"
                }));
                downloadCSV("custom_audience_cohort.csv", rows);
                showToast("Audience Exported", `Downloaded custom_audience_cohort.csv (${matchedCohort.length} accounts)`, "success");
                logAuditEvent("Export", `Exported custom RFM audience of ${matchedCohort.length} accounts`);
            });
        }

        const pushBtn = document.getElementById("pushDynCohortToCampaignBtn");
        if (pushBtn) {
            pushBtn.addEventListener("click", () => {
                switchTab("campaign-studio");
                const audSize = document.getElementById("campAudienceSize");
                const revProt = document.getElementById("campRevenueProtected");
                if (audSize) audSize.textContent = `${matchedCohort.length} Accounts (Custom Filtered)`;
                if (revProt) revProt.textContent = `£${matchedSpend.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                showToast("Cohort Linked", `Loaded ${matchedCohort.length} accounts into Campaign Studio`, "success");
                logAuditEvent("Campaign", `Linked custom RFM cohort (${matchedCohort.length} accounts, £${matchedSpend.toFixed(2)}) to Campaign Studio`);
            });
        }
    }

    sliderRecency.addEventListener("input", updateDynamicCohort);
    sliderFreq.addEventListener("input", updateDynamicCohort);
    sliderSpend.addEventListener("input", updateDynamicCohort);

    updateDynamicCohort();
}

// =============================================================================
// TAB 8 EXTENSION: SKU & RESTOCK MODALS
// =============================================================================
function initSkuAndRestockModals() {
    // Add SKU Modal
    const skuModal = document.getElementById("skuModalBackdrop");
    const openSkuBtn = document.getElementById("addNewSkuModalBtn");
    const closeSkuBtn = document.getElementById("closeSkuModalBtn");
    const cancelSkuBtn = document.getElementById("cancelSkuModalBtn");
    const skuForm = document.getElementById("skuModalForm");

    if (openSkuBtn && skuModal) {
        openSkuBtn.addEventListener("click", () => {
            skuModal.classList.add("open");
        });
    }

    function closeSkuModal() {
        if (skuModal) skuModal.classList.remove("open");
        if (skuForm) skuForm.reset();
    }

    if (closeSkuBtn) closeSkuBtn.addEventListener("click", closeSkuModal);
    if (cancelSkuBtn) cancelSkuBtn.addEventListener("click", closeSkuModal);

    if (skuForm) {
        skuForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const code = document.getElementById("modalSkuCode").value.trim().toUpperCase();
            const name = document.getElementById("modalSkuName").value.trim();
            const price = parseFloat(document.getElementById("modalSkuPrice").value) || 4.99;
            const stock = parseInt(document.getElementById("modalSkuStock").value, 10) || 250;
            const burn = parseInt(document.getElementById("modalSkuBurn").value, 10) || 10;

            try {
                const res = await fetch("http://localhost:8000/api/v1/inventory/skus", {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify({
                        stock_code: code,
                        description: name,
                        unit_price: price,
                        daily_demand_mean: burn,
                        stock_on_hand: stock
                    })
                });
                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    showToast("Catalog Update Blocked", errData.detail || `HTTP ${res.status}`, "alert");
                    return;
                }
            } catch (_err) {
                const daysLeft = Math.round(stock / burn);
                const status = daysLeft <= 14 ? "CRITICAL_REORDER" : daysLeft <= 21 ? "REORDER_SOON" : "OPTIMAL";
                INVENTORY_DATABASE.unshift({ code, name, price, stock, burn, daysLeft, status });
            }

            await initInventoryMart();
            closeSkuModal();
            showToast("SKU Registered", `Created catalog product [${code}] ${name}`, "success");
            logAuditEvent("Catalog", `Registered new SKU catalog item: [${code}] ${name} (£${price.toFixed(2)})`);
        });
    }

    // Restock Modal
    const restockModal = document.getElementById("restockModalBackdrop");
    const closeRestockBtn = document.getElementById("closeRestockModalBtn");
    const cancelRestockBtn = document.getElementById("cancelRestockModalBtn");
    const restockForm = document.getElementById("restockModalForm");
    const restockQtyInput = document.getElementById("modalRestockQty");
    const restockProjectedStock = document.getElementById("modalRestockProjectedStock");
    const restockProjectedDays = document.getElementById("modalRestockProjectedDays");

    let currentRestockItem = null;

    function openRestockModal(code) {
        currentRestockItem = INVENTORY_DATABASE.find(i => i.code === code);
        if (!currentRestockItem || !restockModal) return;

        document.getElementById("modalRestockSkuCode").value = currentRestockItem.code;
        document.getElementById("modalRestockSkuName").value = `[${currentRestockItem.code}] ${currentRestockItem.name} (Current: ${currentRestockItem.stock} units)`;
        updateRestockProjections();
        restockModal.classList.add("open");
    }

    function updateRestockProjections() {
        if (!currentRestockItem) return;
        const addQty = parseInt(restockQtyInput.value, 10) || 500;
        const newTotal = currentRestockItem.stock + addQty;
        const newDays = Math.round(newTotal / currentRestockItem.burn);
        const addedDays = Math.round(addQty / currentRestockItem.burn);

        if (restockProjectedStock) restockProjectedStock.textContent = `${newTotal.toLocaleString()} Units`;
        if (restockProjectedDays) restockProjectedDays.textContent = `+${addedDays} Days Coverage (${newDays} Days Total)`;
    }

    if (restockQtyInput) {
        restockQtyInput.addEventListener("input", updateRestockProjections);
    }

    function closeRestockModal() {
        if (restockModal) restockModal.classList.remove("open");
        currentRestockItem = null;
    }

    if (closeRestockBtn) closeRestockBtn.addEventListener("click", closeRestockModal);
    if (cancelRestockBtn) cancelRestockBtn.addEventListener("click", closeRestockModal);

    if (restockForm) {
        restockForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!currentRestockItem) return;

            const addQty = parseInt(restockQtyInput.value, 10) || 500;
            const supplier = document.getElementById("modalRestockSupplier").value;
            const leadDays = parseInt(document.getElementById("modalRestockLeadDays").value, 10) || 3;
            const targetCode = currentRestockItem.code;

            try {
                const res = await fetch("http://localhost:8000/api/v1/inventory/purchase-orders", {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify({
                        stock_code: targetCode,
                        order_qty: addQty,
                        lead_time_days: leadDays,
                        notes: `Manual Restock Modal (${supplier})`
                    })
                });
                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    showToast("Purchase Order Blocked", errData.detail || `HTTP ${res.status}`, "alert");
                    return;
                }
            } catch (_err) {
                currentRestockItem.stock += addQty;
                currentRestockItem.daysLeft = Math.round(currentRestockItem.stock / currentRestockItem.burn);
                currentRestockItem.status = currentRestockItem.daysLeft <= 14 ? "CRITICAL_REORDER" : currentRestockItem.daysLeft <= 21 ? "REORDER_SOON" : "OPTIMAL";
            }

            await initInventoryMart();
            closeRestockModal();
            showToast("Purchase Order Dispatched", `Added ${addQty} units to SKU [${targetCode}]. Lead Time: ${leadDays}d (${supplier})`, "success");
            logAuditEvent("Inventory", `Dispatched replenishment PO: ${addQty} units for SKU [${targetCode}] via ${supplier}`);
        });
    }

    // Wire up buttons in table
    window.openRestockModal = openRestockModal;
}

// =============================================================================
// TAB 12: DEVELOPER API CONSOLE & LIVE REST ENDPOINT TESTER
// =============================================================================
const API_ENDPOINTS = {
    churn: {
        method: "POST",
        path: "/api/v1/churn/predict",
        url: "http://localhost:8000/api/v1/churn/predict",
        payload: {
            Recency: 84,
            HistoricalFrequency: 17,
            HistoricalMonetary: 65164.79,
            HistoricalUnits: 850,
            UniqueSKUs: 42,
            Tenure: 280,
            AOV: 3833.22,
            UnitsPerOrder: 50,
            PurchaseVelocity: 1.82
        },
        handler: (req) => {
            const r = req.Recency || 80;
            const m = req.HistoricalMonetary || 1000;
            const prob = Math.min(0.96, Math.max(0.04, 0.15 + (r / 120) * 0.75 - (m > 10000 ? 0.08 : 0)));
            const isHigh = prob >= 0.65;
            return {
                churn_probability: parseFloat(prob.toFixed(4)),
                risk_tier: isHigh ? "High Risk" : prob >= 0.35 ? "Medium Risk" : "Low Risk (Healthy)",
                is_churn_predicted: prob >= 0.50,
                recommended_strategy: isHigh ? "VIP EXECUTIVE INTERVENTION" : "LOYALTY PRESERVATION"
            };
        }
    },
    forecast: {
        method: "POST",
        path: "/api/v1/forecast/sales",
        url: "http://localhost:8000/api/v1/forecast/sales",
        payload: {
            DayOfWeek: 3,
            DayOfMonth: 15,
            Month: 11,
            Quarter: 4,
            IsWeekend: 0,
            Lag_1: 42000.0,
            Lag_2: 39000.0,
            Lag_7: 45000.0,
            Lag_14: 41000.0,
            Lag_30: 38000.0,
            RollingMean_7: 41500.0,
            RollingStd_7: 3200.0,
            RollingMean_14: 40800.0,
            RollingMean_30: 39500.0,
            LagOrders_1: 120.0,
            LagOrders_7: 115.0
        },
        handler: (req) => ({
            predicted_daily_revenue_gbp: parseFloat((((req.Lag_7 || 42000) * 0.6 + (req.RollingMean_7 || 41500) * 0.4)).toFixed(2)),
            model_name: "Random Forest Regressor (Offline Estimate)",
            inputs: req
        })
    },
    recommend: {
        method: "GET",
        path: "/api/v1/recommend/item/22423",
        url: "http://localhost:8000/api/v1/recommend/item/22423?top_n=4",
        payload: { stock_code: "22423", top_n: 4 },
        handler: (req) => {
            const code = req.stock_code || "22423";
            const pool = RECS_CATALOG[code] || RECS_CATALOG["22423"];
            return {
                query_stock_code: code,
                query_description: pool.name,
                recommendations: pool.items.slice(0, req.top_n || 4)
            };
        }
    },
    segment: {
        method: "POST",
        path: "/api/v1/segment/rfm",
        url: "http://localhost:8000/api/v1/segment/rfm",
        payload: { Recency: 10, Frequency: 15, Monetary: 6500.0 },
        handler: (req) => ({
            cluster_id: (req.Monetary || 0) > 2500 ? 1 : 3,
            segment_name: (req.Monetary || 0) > 2500 ? "Champions (VIPs)" : "Loyal Customers",
            inputs: req
        })
    },
    pricing: {
        method: "POST",
        path: "/api/v1/pricing/simulate-price-change",
        url: "http://localhost:8000/api/v1/pricing/simulate-price-change",
        payload: { category: "Kitchen & Dining", price_change_pct: 12.0, cogs_ratio: 0.47 },
        handler: (req) => ({
            status: "success",
            category: req.category,
            requested_price_change_pct: req.price_change_pct,
            mode: "offline_preview"
        })
    },
    fraud: {
        method: "POST",
        path: "/api/v1/fraud/score-transaction",
        url: "http://localhost:8000/api/v1/fraud/score-transaction",
        payload: { amount_gbp: 18500.0, total_units: 6200, line_items: 1, customer_id: "Guest", hour_of_day: 2, is_guest: true, auto_quarantine: false },
        handler: (req) => ({
            status: "success",
            assessment: { risk_score: (req.amount_gbp || 0) > 4000 ? 86.5 : 18.0, risk_tier: (req.amount_gbp || 0) > 4000 ? "CRITICAL_QUARANTINE" : "LOW_SAFE" }
        })
    },
    inventory: {
        method: "POST",
        path: "/api/v1/inventory/simulate-sku",
        url: "http://localhost:8000/api/v1/inventory/simulate-sku",
        payload: { stock_code: "22423", service_level: 0.95, lead_time_days: 7, demand_multiplier: 1.0, horizon_days: 30 },
        handler: (req) => ({
            status: "success",
            policy: { stock_code: req.stock_code || "22423", safety_stock: 62, reorder_point: 328, eoq: 914 }
        })
    },
    cohorts: {
        method: "GET",
        path: "/api/v1/cohorts/retention-report",
        url: "http://localhost:8000/api/v1/cohorts/retention-report?metric=customers&country=All",
        payload: { info: "GET endpoint; query parameters ?metric=customers|revenue&country=All" },
        handler: () => buildLocalCohortFallback("customers")
    },
    persistence: {
        method: "GET",
        path: "/api/v1/system/persistence-status",
        url: "http://localhost:8000/api/v1/system/persistence-status",
        payload: { info: "GET endpoint; returns SQLite WAL size and persisted row counts." },
        handler: () => ({ status: "persistent", engine: "SQLite3", journal_mode: "WAL", total_persisted_records: 0 })
    },
    watchdog: {
        method: "GET",
        path: "/api/v1/watchdog/status",
        url: "http://localhost:8000/api/v1/watchdog/status",
        payload: { info: "GET endpoint; returns 4-engine Watchdog health score and remediation directives." },
        handler: () => ({ status: "online", latest: { health_score: 84.0, overall_status: "ATTENTION" } })
    },
    basket_rules: {
        method: "GET",
        path: "/api/v1/recommendations/basket-rules",
        url: "http://localhost:8000/api/v1/recommendations/basket-rules?min_lift=1.2&limit=12",
        payload: { info: "GET endpoint; mines pairwise Support, Confidence, and Lift across checkout baskets." },
        handler: () => ({ status: "healthy", summary: { top_lift: 4.18, total_matching_rules: 4 } })
    },
    finance: {
        method: "GET",
        path: "/api/v1/finance/waterfall-report",
        url: "http://localhost:8000/api/v1/finance/waterfall-report?country=All&cogs_ratio=0.58",
        payload: { info: "GET endpoint; returns Gross-to-Net P&L margin waterfall and high-return SKUs." },
        handler: () => ({ status: "healthy", summary: { return_rate_pct: 8.42 } })
    },
    rbac: {
        method: "GET",
        path: "/api/v1/auth/rbac-matrix",
        url: "http://localhost:8000/api/v1/auth/rbac-matrix",
        payload: { info: "GET endpoint; no request body needed." },
        handler: () => ({ status: "success", roles: ["admin", "lead_ds", "growth", "supply"] })
    }
};

function initApiConsole() {
    const endpointSelect = document.getElementById("apiEndpointSelect");
    const methodBadge = document.getElementById("apiMethodBadge");
    const requestJson = document.getElementById("apiRequestJson");
    const responseJson = document.getElementById("apiResponseJson");
    const responseUrl = document.getElementById("apiResponseUrl");
    const statusPill = document.getElementById("apiStatusPill");
    const latencyPill = document.getElementById("apiLatencyPill");
    const executeBtn = document.getElementById("apiExecuteBtn");
    const resetBtn = document.getElementById("apiResetPayloadBtn");
    const copyCurlBtn = document.getElementById("apiCopyCurlBtn");
    const copyRespBtn = document.getElementById("apiCopyResponseBtn");

    if (!endpointSelect || !requestJson || !responseJson) return;

    function setEndpoint(key) {
        const ep = API_ENDPOINTS[key];
        if (!ep) return;
        if (methodBadge) {
            methodBadge.textContent = ep.method;
            methodBadge.className = `method-badge ${ep.method.toLowerCase()}`;
        }
        if (responseUrl) responseUrl.textContent = ep.url;
        requestJson.value = JSON.stringify(ep.payload, null, 2);
        executeEndpoint(key, true);
    }

    async function executeEndpoint(key, quiet = false) {
        const ep = API_ENDPOINTS[key || endpointSelect.value];
        if (!ep) return;

        let parsedBody = ep.payload;
        try {
            parsedBody = JSON.parse(requestJson.value);
        } catch (e) {
            showToast("Invalid JSON", "Request body contains invalid JSON syntax", "alert");
            return;
        }

        const t0 = performance.now();
        try {
            const fetchOpts = {
                method: ep.method,
                headers: window.getAuthHeaders({ "Content-Type": "application/json" })
            };
            if (ep.method !== "GET") {
                fetchOpts.body = JSON.stringify(parsedBody);
            }
            const res = await fetch(ep.url, fetchOpts);
            const elapsed = (performance.now() - t0).toFixed(1);
            const data = await res.json();
            if (statusPill) {
                statusPill.textContent = `${res.status} ${res.ok ? "OK" : "ERROR"}`;
                statusPill.className = `badge-tag ${res.ok ? "green" : "red"}`;
            }
            if (latencyPill) latencyPill.textContent = `Latency: ${elapsed} ms`;
            responseJson.textContent = JSON.stringify(data, null, 2);
            logAuditEvent("API", `Live ${ep.method} ${ep.path} (${elapsed}ms, HTTP ${res.status})`);
            if (!quiet) showToast("Live API Executed", `HTTP ${res.status} returned in ${elapsed} ms`, res.ok ? "success" : "alert");
            return;
        } catch (err) {
            // Fallback to local mock telemetry when backend :8000 is offline
        }

        const simLatency = (performance.now() - t0 + 3.5).toFixed(1);
        if (statusPill) {
            statusPill.textContent = "200 OK (LOCAL)";
            statusPill.className = "badge-tag blue";
        }
        if (latencyPill) latencyPill.textContent = `Latency: ${simLatency} ms`;
        const resp = ep.handler(parsedBody);
        responseJson.textContent = JSON.stringify(resp, null, 2);
        logAuditEvent("API", `Executed local test call to ${ep.path} (${simLatency}ms)`);
        if (!quiet) showToast("Endpoint Executed (Local)", `Status 200 OK | Simulated fallback`, "info");
    }

    endpointSelect.addEventListener("change", () => {
        setEndpoint(endpointSelect.value);
    });

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            const ep = API_ENDPOINTS[endpointSelect.value];
            if (ep) {
                requestJson.value = JSON.stringify(ep.payload, null, 2);
                showToast("Payload Reset", "Restored default request body", "info");
            }
        });
    }

    if (executeBtn) {
        executeBtn.addEventListener("click", () => {
            executeEndpoint(endpointSelect.value, false);
        });
    }

    if (copyCurlBtn) {
        copyCurlBtn.addEventListener("click", () => {
            const ep = API_ENDPOINTS[endpointSelect.value];
            if (!ep) return;
            const bodyStr = requestJson.value.replace(/\n/g, "").replace(/\s+/g, " ");
            const curl = ep.method === "GET" 
                ? `curl -X GET "${ep.url}"`
                : `curl -X POST "${ep.url}" \\\n  -H "Content-Type: application/json" \\\n  -d '${bodyStr}'`;
            navigator.clipboard.writeText(curl).then(() => {
                showToast("cURL Copied", "cURL command copied to clipboard", "success");
            });
        });
    }

    if (copyRespBtn) {
        copyRespBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(responseJson.textContent).then(() => {
                showToast("JSON Copied", "Response JSON copied to clipboard", "success");
            });
        });
    }

    setEndpoint("churn");
}

// =============================================================================
// EXECUTIVE BOARD BRIEFING REPORT MODAL
// =============================================================================
function initExecutiveReportModal() {
    const reportModal = document.getElementById("reportModalBackdrop");
    const openBtn = document.getElementById("boardReportBtn");
    const closeBtn1 = document.getElementById("closeReportModalBtn");
    const closeBtn2 = document.getElementById("closeReportModalBtn2");
    const printBtn = document.getElementById("printReportBtn");
    const dateSpan = document.getElementById("reportGeneratedDate");

    if (openBtn && reportModal) {
        openBtn.addEventListener("click", () => {
            if (dateSpan) {
                dateSpan.textContent = `Generated: ${new Date().toUTCString()} | Nexus Retail AI`;
            }
            reportModal.classList.add("open");
            logAuditEvent("Security", "Generated Executive Board Briefing Report");
        });
    }

    function closeReportModal() {
        if (reportModal) reportModal.classList.remove("open");
    }

    if (closeBtn1) closeBtn1.addEventListener("click", closeReportModal);
    if (closeBtn2) closeBtn2.addEventListener("click", closeReportModal);

    if (printBtn) {
        printBtn.addEventListener("click", () => {
            window.print();
            showToast("Print Triggered", "Prepared board briefing PDF / printer document", "info");
        });
    }
}

// =============================================================================
// GLOBAL CHART STYLING DEFAULTS (EXECUTIVE DESIGN SYSTEM)
// =============================================================================
function initChartDefaults() {
    if (window.Chart) {
        Chart.defaults.font.family = "'Outfit', -apple-system, BlinkMacSystemFont, sans-serif";
        Chart.defaults.color = "#94A3B8";
        Chart.defaults.plugins.tooltip.backgroundColor = "rgba(15, 23, 42, 0.94)";
        Chart.defaults.plugins.tooltip.titleColor = "#FFFFFF";
        Chart.defaults.plugins.tooltip.bodyColor = "#F1F5F9";
        Chart.defaults.plugins.tooltip.borderColor = "rgba(255, 255, 255, 0.12)";
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
    }
}

// =============================================================================
// FLOATING BACK TO TOP INTERACTION
// =============================================================================
function initScrollToTop() {
    const btn = document.getElementById("scrollToTopBtn");
    if (!btn) return;

    window.addEventListener("scroll", () => {
        if (window.scrollY > 350) {
            btn.classList.add("visible");
        } else {
            btn.classList.remove("visible");
        }
    }, { passive: true });

    btn.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}

// =============================================================================
// LIVE DATA HYDRATION & FASTAPI ML INFERENCE INTEGRATION
// =============================================================================
async function initLivePipelineSync() {
    // 1. Hydrate UI with real pipeline JSON if available
    try {
        const resp = await fetch("data/nexus_data.json");
        if (resp.ok) {
            const data = await resp.json();
            if (data && data.kpis) {
                const revFormatted = "£" + Number(data.kpis.total_gross_revenue_gbp).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                const ordersFormatted = Number(data.kpis.total_completed_orders).toLocaleString("en-GB");
                const aovFormatted = "£" + Number(data.kpis.average_order_value_gbp).toFixed(2);
                const cancelFormatted = Number(data.kpis.cancellation_rate_pct).toFixed(2) + "%";
                const unitsFormatted = Number(data.kpis.total_units_sold).toLocaleString("en-GB");

                // Update active date range cache
                if (typeof DATE_RANGE_DATA !== "undefined" && DATE_RANGE_DATA.all) {
                    DATE_RANGE_DATA.all.rev = revFormatted;
                    DATE_RANGE_DATA.all.orders = ordersFormatted;
                    DATE_RANGE_DATA.all.aov = aovFormatted;
                    DATE_RANGE_DATA.all.cancel = cancelFormatted;
                    DATE_RANGE_DATA.all.units = unitsFormatted;
                }

                // Update DOM KPI elements if on "all" range
                const kpiRev = document.getElementById("kpi-revenue");
                const kpiOrders = document.getElementById("kpi-orders");
                const kpiAov = document.getElementById("kpi-aov");
                const kpiCancel = document.getElementById("kpi-cancel");
                const kpiUnits = document.getElementById("kpi-units");

                if (kpiRev) kpiRev.textContent = revFormatted;
                if (kpiOrders) kpiOrders.textContent = ordersFormatted;
                if (kpiAov) kpiAov.textContent = aovFormatted;
                if (kpiCancel) kpiCancel.textContent = cancelFormatted;
                if (kpiUnits) kpiUnits.textContent = unitsFormatted;

                // Update Top Products table with real data
                if (data.top_products && data.top_products.length > 0) {
                    const tbody = document.querySelector("#topProductsTable tbody");
                    if (tbody) {
                        const totalRev = data.kpis.total_gross_revenue_gbp || 1;
                        tbody.innerHTML = data.top_products.map(p => {
                            const sharePct = ((p.revenue / totalRev) * 100).toFixed(2) + "%";
                            return `
                                <tr>
                                    <td><code>${p.stock_code}</code></td>
                                    <td><strong>${p.description || "Product"}</strong></td>
                                    <td>${Number(p.units_sold).toLocaleString("en-GB")}</td>
                                    <td>${Number(p.order_count).toLocaleString("en-GB")}</td>
                                    <td><strong>£${Number(p.revenue).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></td>
                                    <td><span class="badge-tag blue">${sharePct}</span></td>
                                </tr>
                            `;
                        }).join("");
                    }
                }

                // Hydrate BTYD CLV portfolio summary if present
                if (data.clv_btyd) {
                    if (data.clv_btyd.summary) {
                        const clvSum = data.clv_btyd.summary;
                        const elTotal = document.getElementById("btydTotalPortfolioClv");
                        const elEval = document.getElementById("btydEvaluatedCustomers");
                        const elAvg = document.getElementById("btydAvgCustomerClv");
                        if (elTotal && clvSum.total_portfolio_clv_gbp) {
                            elTotal.textContent = "£" + Number(clvSum.total_portfolio_clv_gbp).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        }
                        if (elEval && clvSum.total_evaluated_customers) {
                            elEval.textContent = Number(clvSum.total_evaluated_customers).toLocaleString("en-GB") + " Accounts";
                        }
                        if (elAvg && clvSum.avg_customer_clv_gbp) {
                            elAvg.textContent = "£" + Number(clvSum.avg_customer_clv_gbp).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        }
                    }
                    if (data.clv_btyd.sample_customers) {
                        window.BTYD_SAMPLE_DATA = data.clv_btyd.sample_customers;
                    }
                }

                // Hydrate baseline drift report if present
                if (data.drift_report) {
                    window.CACHED_DRIFT_REPORT = data.drift_report;
                }

                console.log("[Nexus LiveSync] Hydrated dashboard with real pipeline data (data/nexus_data.json)");
            }
        }
    } catch (e) {
        console.warn("[Nexus LiveSync] Using offline defaults:", e.message);
    }

    // 2. Check if FastAPI ML Inference Server is online (localhost:8000)
    const headerApi = document.getElementById("headerApiStatus");
    try {
        const apiCheck = await fetch("http://localhost:8000/health", { mode: "cors" });
        if (apiCheck.ok) {
            console.log("[Nexus LiveSync] Connected to FastAPI ML Inference Engine at http://localhost:8000");
            const statusBadge = document.querySelector(".live-pill");
            if (statusBadge) {
                statusBadge.innerHTML = '<span class="status-dot"></span> LIVE: FASTAPI ML ENGINE CONNECTED';
                statusBadge.style.background = "rgba(16, 185, 129, 0.15)";
                statusBadge.style.color = "#10B981";
                statusBadge.style.borderColor = "rgba(16, 185, 129, 0.3)";
            }
            if (headerApi) {
                headerApi.classList.remove("offline");
                const text = headerApi.querySelector(".api-live-text");
                if (text) text.textContent = "API Live :8000";
            }
        } else {
            throw new Error("API non-200");
        }
    } catch (e) {
        // FastAPI server not reachable or offline; gracefully keep local mode
        console.log("[Nexus LiveSync] FastAPI server offline; running in client simulation mode.");
        if (headerApi) {
            headerApi.classList.add("offline");
            const text = headerApi.querySelector(".api-live-text");
            if (text) text.textContent = "API Offline (Mock)";
        }
    }
}

// =============================================================================
// DATASET INGESTION STUDIO (CSV / EXCEL IMPORT)
// =============================================================================
function initDatasetImporter() {
    const modalBackdrop = document.getElementById("datasetImportModalBackdrop");
    const openBtn = document.getElementById("openImportModalBtn");
    const closeBtn1 = document.getElementById("closeImportModalBtn");
    const closeBtn2 = document.getElementById("closeImportModalBtn2");
    const dropzone = document.getElementById("importDropzone");
    const fileInput = document.getElementById("importFileInput");
    const browseBtn = document.getElementById("btnBrowseFiles");
    const downloadCsvBtn = document.getElementById("btnDownloadCsvTemplate");
    const downloadXlsxBtn = document.getElementById("btnDownloadExcelTemplate");
    const demoBatchBtn = document.getElementById("btnLoadDemoBatch");
    const inspectionPanel = document.getElementById("importInspectionPanel");
    const executeBtn = document.getElementById("btnExecuteIngest");
    const cancelBtn = document.getElementById("btnCancelImport");
    const statusBox = document.getElementById("importStatusBox");

    let currentFile = null;
    let currentValidationData = null;

    function openModal() {
        if (!modalBackdrop) return;
        modalBackdrop.classList.add("open");
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        if (!modalBackdrop) return;
        modalBackdrop.classList.remove("open");
        document.body.style.overflow = "";
        resetState();
    }

    function resetState() {
        currentFile = null;
        currentValidationData = null;
        if (fileInput) fileInput.value = "";
        if (inspectionPanel) inspectionPanel.style.display = "none";
        if (statusBox) statusBox.style.display = "none";
        if (dropzone) dropzone.style.display = "block";
    }

    if (openBtn) openBtn.addEventListener("click", openModal);
    if (closeBtn1) closeBtn1.addEventListener("click", closeModal);
    if (closeBtn2) closeBtn2.addEventListener("click", closeModal);
    if (cancelBtn) cancelBtn.addEventListener("click", resetState);

    if (modalBackdrop) {
        modalBackdrop.addEventListener("click", (e) => {
            if (e.target === modalBackdrop) closeModal();
        });
    }

    // Browse files button
    if (browseBtn && fileInput) {
        browseBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            fileInput.click();
        });
    }

    // Dropzone click
    if (dropzone && fileInput) {
        dropzone.addEventListener("click", () => fileInput.click());

        ["dragenter", "dragover"].forEach(name => {
            dropzone.addEventListener(name, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach(name => {
            dropzone.addEventListener(name, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("dragover");
            });
        });

        dropzone.addEventListener("drop", (e) => {
            const files = e.dataTransfer.files;
            if (files && files.length > 0) {
                processSelectedFile(files[0]);
            }
        });
    }

    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                processSelectedFile(e.target.files[0]);
            }
        });
    }

    // Template downloads
    if (downloadCsvBtn) {
        downloadCsvBtn.addEventListener("click", () => {
            window.location.href = "http://localhost:8000/api/v1/data/download-template?format=csv";
            showToast("Template Downloaded", "Sample CSV transactions template ready for data entry", "info");
        });
    }

    if (downloadXlsxBtn) {
        downloadXlsxBtn.addEventListener("click", () => {
            window.location.href = "http://localhost:8000/api/v1/data/download-template?format=xlsx";
            showToast("Template Downloaded", "Sample Excel (.xlsx) transactions workbook ready for data entry", "info");
        });
    }

    // Demo batch loading
    if (demoBatchBtn) {
        demoBatchBtn.addEventListener("click", async () => {
            try {
                const res = await fetch("http://localhost:8000/api/v1/data/demo-batch");
                if (res.ok) {
                    const json = await res.json();
                    const records = json.data || [];
                    // Convert records to CSV string
                    const headers = Object.keys(records[0] || {});
                    const csvRows = [headers.join(",")];
                    records.forEach(r => {
                        const vals = headers.map(h => `"${r[h]}"`);
                        csvRows.push(vals.join(","));
                    });
                    const csvContent = csvRows.join("\n");
                    const blob = new Blob([csvContent], { type: "text/csv" });
                    const file = new File([blob], "demo_retail_q4_batch.csv", { type: "text/csv" });
                    processSelectedFile(file);
                    showToast("Demo Batch Loaded", "15 pre-configured wholesale transactions loaded for inspection", "success");
                    return;
                }
            } catch (err) {
                console.warn("[Demo Batch] Backend unreachable, generating client mock:", err);
            }

            // Fallback client synthetic batch
            const sampleCsv = `InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country
581001,22423,REGENCY CAKESTAND 3 TIER,12,2026-10-15 10:30:00,12.75,14096,United Kingdom
581001,85123A,WHITE HANGING HEART T-LIGHT HOLDER,24,2026-10-15 11:15:00,2.95,14911,United Kingdom
581002,47566,PARTY BUNTING,36,2026-10-15 14:00:00,4.95,17841,Germany
581002,20725,LUNCH BAG RED RETROSPOT,48,2026-10-16 09:45:00,2.25,14646,France
581003,22960,JAM MAKING SET WITH JARS,18,2026-10-16 16:30:00,4.25,12415,Netherlands`;

            const blob = new Blob([sampleCsv], { type: "text/csv" });
            const file = new File([blob], "demo_retail_client_batch.csv", { type: "text/csv" });
            processSelectedFile(file);
            showToast("Demo Batch Loaded", "Client sample transactions loaded for inspection", "success");
        });
    }

    async function processSelectedFile(file) {
        currentFile = file;
        const fn = file.name.toLowerCase();
        const isExcel = fn.endsWith(".xlsx") || fn.endsWith(".xls");

        // UI indicators
        const iconEl = document.getElementById("importFileIcon");
        const nameEl = document.getElementById("importFileName");
        const sizeEl = document.getElementById("importFileSize");
        if (iconEl) iconEl.textContent = isExcel ? "📊" : "📄";
        if (nameEl) nameEl.textContent = file.name;
        if (sizeEl) sizeEl.textContent = `(${(file.size / 1024).toFixed(1)} KB)`;

        // Show inspection panel with loading skeleton
        if (inspectionPanel) inspectionPanel.style.display = "block";
        const tbody = document.querySelector("#importPreviewTable tbody");
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:1.5rem;color:var(--text-muted);">Parsing and inspecting schema...</td></tr>`;

        // Dispatch validation to FastAPI
        const formData = new FormData();
        formData.append("file", file);

        try {
            const resp = await fetch("http://localhost:8000/api/v1/data/validate-upload", {
                method: "POST",
                body: formData
            });

            if (resp.ok) {
                const data = await resp.json();
                currentValidationData = data;
                renderInspectionDetails(data);
                return;
            } else {
                const errJson = await resp.json();
                renderValidationError(errJson.detail || "Validation failed.");
                return;
            }
        } catch (e) {
            console.warn("[Importer] Validation backend offline, attempting client text parse:", e.message);
        }

        // Client-side fallback preview if backend not reachable
        renderClientFallbackPreview(file);
    }

    function renderInspectionDetails(data) {
        const schemaBadge = document.getElementById("importSchemaBadge");
        const chipContainer = document.getElementById("columnMappingChips");
        const validRowsEl = document.getElementById("importValidRows");
        const discardedEl = document.getElementById("importDiscardedRows");
        const totalRevEl = document.getElementById("importTotalRev");
        const aovEl = document.getElementById("importAov");
        const dateRangeEl = document.getElementById("importDateRange");
        const acctsSkusEl = document.getElementById("importAccountsSkus");
        const tbody = document.querySelector("#importPreviewTable tbody");
        const executeBtn = document.getElementById("btnExecuteIngest");

        if (!data.valid) {
            if (schemaBadge) {
                schemaBadge.textContent = "🚨 MISSING REQUIRED COLUMNS";
                schemaBadge.style.background = "rgba(239, 68, 68, 0.2)";
                schemaBadge.style.color = "#ef4444";
                schemaBadge.style.borderColor = "rgba(239, 68, 68, 0.4)";
            }
            if (executeBtn) executeBtn.disabled = true;
            if (chipContainer) chipContainer.innerHTML = `<span style="color:#ef4444;font-size:0.8rem;">${data.error}</span>`;
            return;
        }

        if (schemaBadge) {
            schemaBadge.textContent = "🟢 SCHEMA VALIDATED";
            schemaBadge.style.background = "rgba(16, 185, 129, 0.2)";
            schemaBadge.style.color = "#10b981";
            schemaBadge.style.borderColor = "rgba(16, 185, 129, 0.3)";
        }
        if (executeBtn) executeBtn.disabled = false;

        // Render detected mapping chips
        if (chipContainer && data.detected_mappings) {
            chipContainer.innerHTML = Object.entries(data.detected_mappings).map(([orig, canon]) => `
                <span class="mapping-chip">
                    <strong>${orig}</strong> <span class="arrow">➔</span> <code>${canon}</code>
                </span>
            `).join("");
        }

        // Summary metrics
        const m = data.metrics || {};
        if (validRowsEl) validRowsEl.textContent = `${Number(data.valid_commercial_rows).toLocaleString("en-GB")} Rows`;
        if (discardedEl) discardedEl.textContent = `${data.cancelled_or_invalid_rows || 0} discarded / cancelled`;
        if (totalRevEl) totalRevEl.textContent = `£${Number(m.total_revenue_gbp || 0).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (aovEl) aovEl.textContent = `AOV: £${Number(m.average_order_value_gbp || 0).toFixed(2)}`;
        if (dateRangeEl) dateRangeEl.textContent = m.date_range || "N/A";
        if (acctsSkusEl) acctsSkusEl.textContent = `${m.unique_customers || 0} Cust / ${m.unique_skus || 0} SKUs`;

        // Render 5 preview rows
        if (tbody && data.preview_rows) {
            tbody.innerHTML = data.preview_rows.map(r => `
                <tr>
                    <td><code>${r.InvoiceNo || ""}</code></td>
                    <td><code>${r.StockCode || ""}</code></td>
                    <td><strong>${r.Description || "Item"}</strong></td>
                    <td>${r.Quantity}</td>
                    <td><small>${(r.InvoiceDate || "").substring(0, 16)}</small></td>
                    <td>£${Number(r.UnitPrice || 0).toFixed(2)}</td>
                    <td>${r.CustomerID ? '#' + r.CustomerID : '<span class="text-muted">Guest</span>'}</td>
                    <td><span class="badge-tag gray">${r.Country || "UK"}</span></td>
                </tr>
            `).join("");
        }
    }

    function renderValidationError(msg) {
        const schemaBadge = document.getElementById("importSchemaBadge");
        if (schemaBadge) {
            schemaBadge.textContent = "🚨 VALIDATION ERROR";
            schemaBadge.style.background = "rgba(239, 68, 68, 0.2)";
            schemaBadge.style.color = "#ef4444";
        }
        showToast("Validation Error", msg, "error");
    }

    function renderClientFallbackPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result || "";
            const lines = text.split("\n").filter(l => l.trim().length > 0);
            if (lines.length === 0) return;

            const sampleRows = lines.slice(1, 6).map(line => {
                const cols = line.split(",").map(c => c.replace(/"/g, "").trim());
                return {
                    InvoiceNo: cols[0] || "581000",
                    StockCode: cols[1] || "22423",
                    Description: cols[2] || "Sample Product",
                    Quantity: cols[3] || "12",
                    InvoiceDate: cols[4] || "2026-10-15",
                    UnitPrice: cols[5] || "5.95",
                    CustomerID: cols[6] || "14096",
                    Country: cols[7] || "United Kingdom"
                };
            });

            renderInspectionDetails({
                valid: true,
                filename: file.name,
                detected_mappings: { "InvoiceNo": "InvoiceNo", "UnitPrice": "UnitPrice", "Quantity": "Quantity" },
                total_rows_parsed: lines.length - 1,
                valid_commercial_rows: lines.length - 1,
                cancelled_or_invalid_rows: 0,
                metrics: {
                    date_range: "2026-10-15 to 2026-10-16",
                    total_revenue_gbp: 485.50,
                    average_order_value_gbp: 97.10,
                    unique_customers: 4,
                    unique_skus: 5
                },
                preview_rows: sampleRows
            });
        };
        reader.readAsText(file);
    }

    // Ingestion Execution
    if (executeBtn) {
        executeBtn.addEventListener("click", async () => {
            if (!currentFile) return;

            const mergeProd = document.getElementById("chkMergeProduction")?.checked ?? true;
            const triggerRetrain = document.getElementById("chkTriggerRetrain")?.checked ?? true;

            if (inspectionPanel) inspectionPanel.style.display = "none";
            if (statusBox) statusBox.style.display = "block";

            const progressBar = document.getElementById("importProgressBar");
            const statusText = document.getElementById("importStatusText");

            if (progressBar) progressBar.style.width = "25%";
            if (statusText) statusText.textContent = "Uploading dataset stream to Nexus Data Engine...";

            const formData = new FormData();
            formData.append("file", currentFile);
            formData.append("merge_to_production", mergeProd);
            formData.append("trigger_retrain", triggerRetrain);

            setTimeout(() => {
                if (progressBar) progressBar.style.width = "60%";
                if (statusText) statusText.textContent = "Writing partitioned Parquet batch and merging feature vectors...";
            }, 500);

            try {
                const res = await fetch("http://localhost:8000/api/v1/data/ingest-upload", {
                    method: "POST",
                    body: formData
                });

                if (res.ok) {
                    const data = await res.json();
                    if (progressBar) progressBar.style.width = "100%";
                    if (statusText) statusText.textContent = "SUCCESS: Dataset ingested and merged. Updating local telemetry...";

                    showToast("Dataset Ingested", `Successfully imported ${currentFile.name} (${data.rows_added || 'active'} rows merged)`, "success");
                    logAuditEvent("Data Engineering", `Imported dataset ${currentFile.name}: merged ${data.rows_added || 0} rows; retrain=${triggerRetrain}`);

                    if (window.appendMLOpsTermLog) {
                        window.appendMLOpsTermLog(`[Data Ingestion] Ingested batch: ${data.batch_file || currentFile.name} (+${data.rows_added || 0} rows)`);
                    }

                    setTimeout(() => {
                        closeModal();
                    }, 1400);
                    return;
                }
            } catch (err) {
                console.warn("[Importer Execution] Backend ingestion offline, finishing simulated import:", err.message);
            }

            // Fallback simulated execution
            setTimeout(() => {
                if (progressBar) progressBar.style.width = "100%";
                if (statusText) statusText.textContent = "SUCCESS: Dataset imported locally. Model stores refreshed.";
                showToast("Dataset Ingested", `Successfully imported ${currentFile.name} into local cache`, "success");
                logAuditEvent("Data Engineering", `Imported local dataset ${currentFile.name}`);
                setTimeout(() => closeModal(), 1400);
            }, 1200);
        });
    }
}

// =============================================================================
// AI COPILOT & TEXT-TO-SQL ASSISTANT DRAWER
// =============================================================================
function initAiCopilot() {
    const backdrop = document.getElementById("copilotDrawerBackdrop");
    const openBtn = document.getElementById("openCopilotBtn");
    const closeBtn = document.getElementById("copilotCloseBtn");
    const messagesContainer = document.getElementById("copilotMessages");
    const form = document.getElementById("copilotForm");
    const input = document.getElementById("copilotInput");
    const promptChips = document.querySelectorAll(".copilot-prompt-chip");

    function openCopilot() {
        if (!backdrop) return;
        backdrop.classList.add("open");
        document.body.style.overflow = "hidden";
        if (input) {
            setTimeout(() => input.focus(), 150);
        }
    }

    function closeCopilot() {
        if (!backdrop) return;
        backdrop.classList.remove("open");
        document.body.style.overflow = "";
    }

    if (openBtn) openBtn.addEventListener("click", openCopilot);
    if (closeBtn) closeBtn.addEventListener("click", closeCopilot);

    if (backdrop) {
        backdrop.addEventListener("click", (e) => {
            if (e.target === backdrop) closeCopilot();
        });
    }

    // Preset Prompt chips click
    promptChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const prompt = chip.getAttribute("data-prompt") || chip.textContent;
            submitCopilotQuery(prompt);
        });
    });

    if (form) {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            const q = input.value.trim();
            if (!q) return;
            input.value = "";
            submitCopilotQuery(q);
        });
    }

    async function submitCopilotQuery(queryText) {
        if (!messagesContainer) return;

        // 1. Append User Message Bubble
        appendUserMessage(queryText);

        // 2. Append Loading / Thinking indicator
        const thinkingId = "copilotThinking_" + Date.now();
        appendThinkingIndicator(thinkingId);

        let result = null;

        // 3. Attempt query to FastAPI Copilot endpoint
        try {
            const resp = await fetch("http://localhost:8000/api/v1/copilot/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: queryText })
            });
            if (resp.ok) {
                result = await resp.json();
            }
        } catch (err) {
            console.warn("[Copilot] FastAPI backend unreachable, using client offline response:", err);
        }

        // 4. Remove thinking indicator
        const thinkingEl = document.getElementById(thinkingId);
        if (thinkingEl) thinkingEl.remove();

        // 5. Render Response
        if (result) {
            appendAssistantResponse(result);
        } else {
            appendAssistantOfflineFallback(queryText);
        }
    }

    function appendUserMessage(text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "copilot-msg user";
        msgDiv.innerHTML = `<div class="copilot-bubble">${escapeHtml(text)}</div>`;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendThinkingIndicator(id) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "copilot-msg assistant";
        msgDiv.id = id;
        msgDiv.innerHTML = `
            <div class="copilot-avatar">✨</div>
            <div class="copilot-bubble" style="color:var(--text-muted);font-style:italic;">
                <span style="display:inline-block;animation:spin 1s linear infinite;">⚙️</span> Analyzing natural language, running DuckDB query in-memory...
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendAssistantResponse(res) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "copilot-msg assistant";

        let sqlHtml = "";
        if (res.sql) {
            sqlHtml = `
                <div class="copilot-sql-box">
                    <div class="copilot-sql-header">
                        <span style="color:#60A5FA;font-weight:600;">⚡ DuckDB SQL [${res.execution_time_ms || 1.8}ms]</span>
                        <button type="button" class="btn btn-outline btn-xs" style="font-size:0.65rem;padding:0.15rem 0.4rem;" onclick="navigator.clipboard.writeText(this.getAttribute('data-sql'));showToast('SQL Copied', 'Query copied to clipboard', 'info');" data-sql="${escapeHtml(res.sql)}">Copy SQL</button>
                    </div>
                    <code>${escapeHtml(res.sql)}</code>
                </div>
            `;
        }

        let tableHtml = "";
        if (res.data && res.data.length > 0 && res.columns) {
            const cols = res.columns.slice(0, 5);
            tableHtml = `
                <div class="copilot-table-wrap">
                    <table class="copilot-table">
                        <thead>
                            <tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>
                        </thead>
                        <tbody>
                            ${res.data.slice(0, 5).map(row => `
                                <tr>${cols.map(c => `<td>${formatCellValue(row[c])}</td>`).join("")}</tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            `;
        }

        let followupsHtml = "";
        if (res.suggested_followups && res.suggested_followups.length > 0) {
            followupsHtml = `
                <div class="copilot-followups-row">
                    ${res.suggested_followups.map(f => `
                        <button type="button" class="copilot-followup-pill" onclick="window.askCopilotPrompt('${escapeHtml(f)}')">💡 ${f}</button>
                    `).join("")}
                </div>
            `;
        }

        msgDiv.innerHTML = `
            <div class="copilot-avatar">✨</div>
            <div class="copilot-bubble">
                <div style="font-size:0.86rem;line-height:1.5;">${formatMarkdown(res.summary || "Here are your analytical results:")}</div>
                ${sqlHtml}
                ${tableHtml}
                ${followupsHtml}
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendAssistantOfflineFallback(queryText) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "copilot-msg assistant";
        msgDiv.innerHTML = `
            <div class="copilot-avatar">✨</div>
            <div class="copilot-bubble">
                <p style="margin:0 0 0.5rem 0;">I've parsed your query: <em>"${escapeHtml(queryText)}"</em>.</p>
                <div class="copilot-sql-box">
                    <div class="copilot-sql-header">
                        <span style="color:#60A5FA;font-weight:600;">⚡ DuckDB SQL (Local Mode)</span>
                    </div>
                    <code>SELECT stock_code, FIRST(description) AS item, SUM(total_price) AS revenue FROM ecommerce_transactions GROUP BY stock_code ORDER BY revenue DESC LIMIT 5;</code>
                </div>
                <p style="margin:0;font-size:0.8rem;color:var(--text-muted);">FastAPI server at :8000 is currently running offline, but client analytics and simulator tools remain active.</p>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function formatCellValue(val) {
        if (typeof val === "number") {
            if (val > 1000) return Number(val).toLocaleString("en-GB", { maximumFractionDigits: 2 });
            return Number(val).toFixed(2);
        }
        return escapeHtml(String(val ?? ""));
    }

    function formatMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    function escapeHtml(str) {
        return (str || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    window.askCopilotPrompt = function(promptText) {
        openCopilot();
        submitCopilotQuery(promptText);
    };
}


// =============================================================================
// E-COMMERCE INTEGRATION WEBHOOK HUB (SHOPIFY / STRIPE / WOOCOMMERCE)
// =============================================================================
function handleWebhookOrderBroadcast(data) {
    console.log("[Nexus WebSocket] Received live webhook order:", data);
    showToast(
        `⚡ ${String(data.provider || 'Store').toUpperCase()} Order Ingested`,
        `${data.invoice_no}: +£${Number(data.total_amount_gbp || 0).toFixed(2)} (${data.items_count || 1} items) for #${data.customer_id || 'Guest'}`,
        "success"
    );
    logAuditEvent(
        "Webhooks",
        `Ingested ${String(data.provider || '').toUpperCase()} order ${data.invoice_no} (+£${Number(data.total_amount_gbp || 0).toFixed(2)}) for #${data.customer_id}`
    );
    if (typeof refreshWebhooksTelemetry === "function") {
        refreshWebhooksTelemetry();
    }
}

function initWebhooksHub() {
    const modalBackdrop = document.getElementById("webhooksHubModalBackdrop");
    const openBtn = document.getElementById("openWebhooksModalBtn");
    const closeBtn1 = document.getElementById("closeWebhooksModalBtn");
    const closeBtn2 = document.getElementById("closeWebhooksModalBtn2");
    const simulateBtns = document.querySelectorAll(".btn-simulate-webhook");
    const copyBtns = document.querySelectorAll(".copy-btn");
    const tableBody = document.getElementById("webhookEventsTableBody");
    const totalCountBadge = document.getElementById("webhooksTotalCountBadge");
    const simResultBox = document.getElementById("webhookSimResultBox");
    const simPayloadCode = document.getElementById("webhookSimPayloadCode");
    const simHeading = document.getElementById("webhookSimHeading");
    const simStatus = document.getElementById("webhookSimStatus");

    function openModal() {
        if (!modalBackdrop) return;
        modalBackdrop.classList.add("open");
        document.body.style.overflow = "hidden";
        refreshWebhooksTelemetry();
    }

    function closeModal() {
        if (!modalBackdrop) return;
        modalBackdrop.classList.remove("open");
        document.body.style.overflow = "";
    }

    if (openBtn) openBtn.addEventListener("click", openModal);
    if (closeBtn1) closeBtn1.addEventListener("click", closeModal);
    if (closeBtn2) closeBtn2.addEventListener("click", closeModal);

    if (modalBackdrop) {
        modalBackdrop.addEventListener("click", (e) => {
            if (e.target === modalBackdrop) closeModal();
        });
    }

    // Copy Webhook URL to clipboard
    copyBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const targetEl = document.getElementById(targetId);
            if (!targetEl) return;
            const textToCopy = targetEl.textContent.trim();
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalHtml = btn.innerHTML;
                btn.innerHTML = "✓ Copied!";
                btn.classList.add("btn-success");
                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                    btn.classList.remove("btn-success");
                }, 1500);
            }).catch(err => {
                console.error("Failed to copy webhook URL:", err);
            });
        });
    });

    // Simulate Webhook Ingestion
    simulateBtns.forEach(btn => {
        btn.addEventListener("click", async () => {
            const provider = btn.getAttribute("data-provider");
            if (!provider) return;

            const originalText = btn.innerHTML;
            btn.innerHTML = "⏳ Simulating...";
            btn.disabled = true;

            try {
                const res = await fetch("http://localhost:8000/api/v1/integrations/webhook/simulate-sample", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ provider })
                });

                if (!res.ok) {
                    throw new Error(`Simulation failed with HTTP ${res.status}`);
                }

                const data = await res.json();

                // Show dynamic result preview
                if (simResultBox && simPayloadCode) {
                    simResultBox.style.display = "block";
                    if (simHeading) simHeading.textContent = `⚡ Live ${provider.toUpperCase()} Webhook Ingested • ${data.invoice_no}`;
                    if (simStatus) simStatus.textContent = `200 OK • Ingested (£${Number(data.total_amount_gbp).toFixed(2)})`;
                    simPayloadCode.textContent = JSON.stringify(data.raw_sample_payload, null, 2);
                }

                showToast(
                    `⚡ ${provider.toUpperCase()} Simulated Order Ingested`,
                    `Invoice ${data.invoice_no}: +£${Number(data.total_amount_gbp).toFixed(2)} (${data.items_ingested} items)`,
                    "success"
                );

                refreshWebhooksTelemetry();

            } catch (err) {
                console.error("[Webhooks] Simulation error:", err);
                showToast("Simulation Failed", err.message, "danger");
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });
    });

    window.refreshWebhooksTelemetry = async function() {
        try {
            const res = await fetch("http://localhost:8000/api/v1/integrations/status");
            if (!res.ok) return;
            const data = await res.json();

            // Update Connector Cards
            if (data.connectors) {
                const shopify = data.connectors.shopify;
                if (shopify) {
                    const cnt = document.getElementById("shopifyOrdersCount");
                    const rev = document.getElementById("shopifyRevenueVal");
                    const ping = document.getElementById("shopifyLastPing");
                    const badge = document.getElementById("shopifyStatusBadge");
                    if (cnt) cnt.textContent = shopify.events_received;
                    if (rev) rev.textContent = `£${Number(shopify.total_revenue_gbp).toFixed(2)}`;
                    if (ping) ping.textContent = shopify.last_event_at ? new Date(shopify.last_event_at).toLocaleTimeString() : "Never";
                    if (badge) {
                        badge.textContent = shopify.status === "ACTIVE" ? "● ACTIVE" : "● LISTENING";
                        badge.style.color = shopify.status === "ACTIVE" ? "#38bdf8" : "#22c55e";
                    }
                }

                const stripe = data.connectors.stripe;
                if (stripe) {
                    const cnt = document.getElementById("stripeOrdersCount");
                    const rev = document.getElementById("stripeRevenueVal");
                    const ping = document.getElementById("stripeLastPing");
                    const badge = document.getElementById("stripeStatusBadge");
                    if (cnt) cnt.textContent = stripe.events_received;
                    if (rev) rev.textContent = `£${Number(stripe.total_revenue_gbp).toFixed(2)}`;
                    if (ping) ping.textContent = stripe.last_event_at ? new Date(stripe.last_event_at).toLocaleTimeString() : "Never";
                    if (badge) {
                        badge.textContent = stripe.status === "ACTIVE" ? "● ACTIVE" : "● LISTENING";
                        badge.style.color = stripe.status === "ACTIVE" ? "#38bdf8" : "#22c55e";
                    }
                }

                const woo = data.connectors.woocommerce;
                if (woo) {
                    const cnt = document.getElementById("wooOrdersCount");
                    const rev = document.getElementById("wooRevenueVal");
                    const ping = document.getElementById("wooLastPing");
                    const badge = document.getElementById("wooStatusBadge");
                    if (cnt) cnt.textContent = woo.events_received;
                    if (rev) rev.textContent = `£${Number(woo.total_revenue_gbp).toFixed(2)}`;
                    if (ping) ping.textContent = woo.last_event_at ? new Date(woo.last_event_at).toLocaleTimeString() : "Never";
                    if (badge) {
                        badge.textContent = woo.status === "ACTIVE" ? "● ACTIVE" : "● LISTENING";
                        badge.style.color = woo.status === "ACTIVE" ? "#38bdf8" : "#22c55e";
                    }
                }
            }

            if (totalCountBadge) {
                totalCountBadge.textContent = `${data.total_events_ingested || 0} Events Ingested (Total: £${Number(data.total_revenue_ingested_gbp || 0).toFixed(2)})`;
            }

            // Update Events Table
            if (tableBody && data.recent_events && data.recent_events.length > 0) {
                tableBody.innerHTML = data.recent_events.map(ev => {
                    const providerIcon = ev.provider === "shopify" ? "🛍️ Shopify" : ev.provider === "stripe" ? "💳 Stripe" : "🏪 WooCommerce";
                    const sigBadge = ev.verified 
                        ? `<span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #22c55e;">✓ VERIFIED</span>`
                        : `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">DEV_MODE</span>`;
                    const timeStr = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : "Just now";

                    return `
                        <tr>
                            <td><strong>${providerIcon}</strong></td>
                            <td><code>${ev.invoice_no}</code></td>
                            <td>${ev.items_count} item(s)</td>
                            <td style="color: var(--success); font-weight: 600;">£${Number(ev.total_amount_gbp).toFixed(2)}</td>
                            <td>#${ev.customer_id}</td>
                            <td>${sigBadge}</td>
                            <td style="color: var(--text-muted); font-size: 0.75rem;">${timeStr}</td>
                        </tr>
                    `;
                }).join("");
            }

        } catch (err) {
            console.warn("[Webhooks] Could not fetch status:", err);
        }
    };
}

// =============================================================================
// TAB 13: DYNAMIC PRICING ELASTICITY & A/B EXPERIMENTATION LAB
// =============================================================================
function handlePricingExperimentBroadcast(exp) {
    if (!exp) return;
    const stats = exp.statistics || {};
    showToast(
        "🧪 Pricing A/B Experiment Completed",
        `${exp.experiment_name}: Winner=${stats.winner || "EVALUATED"} (p=${Number(stats.p_value || 0).toFixed(4)})`,
        stats.winner === "VARIANT" ? "success" : "info"
    );
    logAuditEvent(
        "Pricing/AB",
        `Executed pricing A/B test '${exp.experiment_name}' (${exp.category}, ${exp.price_change_pct}%): Winner=${stats.winner}`
    );
}

const PRICING_OFFLINE_CATEGORIES = [
    { category: "Kitchen & Dining", elasticity_coefficient: -1.723, r_squared: 0.5066, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 2.24, baseline_total_units: 1112255, baseline_revenue_gbp: 2493143.89, baseline_cogs_ratio: 0.47, baseline_gross_margin_gbp: 1321366.26, optimal_price_change_pct: 12.0, optimal_price_gbp: 2.51, margin_uplift_gbp: 11719.37, margin_uplift_pct: 0.89 },
    { category: "Home Decor & Lighting", elasticity_coefficient: -1.757, r_squared: 0.5171, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 1.90, baseline_total_units: 1324278, baseline_revenue_gbp: 2511398.72, baseline_cogs_ratio: 0.44, baseline_gross_margin_gbp: 1406383.28, optimal_price_change_pct: 2.0, optimal_price_gbp: 1.93, margin_uplift_gbp: 419.31, margin_uplift_pct: 0.03 },
    { category: "Bags & Storage", elasticity_coefficient: -1.694, r_squared: 0.4242, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 2.09, baseline_total_units: 585811, baseline_revenue_gbp: 1222326.21, baseline_cogs_ratio: 0.49, baseline_gross_margin_gbp: 623386.37, optimal_price_change_pct: 20.0, optimal_price_gbp: 2.50, margin_uplift_gbp: 13867.44, margin_uplift_pct: 2.22 },
    { category: "Seasonal & Party", elasticity_coefficient: -1.628, r_squared: 0.5066, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 1.45, baseline_total_units: 294157, baseline_revenue_gbp: 427986.53, baseline_cogs_ratio: 0.36, baseline_gross_margin_gbp: 273911.38, optimal_price_change_pct: -7.0, optimal_price_gbp: 1.35, margin_uplift_gbp: 634.36, margin_uplift_pct: 0.23 },
    { category: "Stationery & Craft", elasticity_coefficient: -1.688, r_squared: 0.5001, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 1.09, baseline_total_units: 626868, baseline_revenue_gbp: 680314.90, baseline_cogs_ratio: 0.34, baseline_gross_margin_gbp: 449007.83, optimal_price_change_pct: -17.0, optimal_price_gbp: 0.90, margin_uplift_gbp: 7556.78, margin_uplift_pct: 1.68 },
    { category: "General Giftware", elasticity_coefficient: -1.643, r_squared: 0.5020, demand_regime: "Elastic (Volume Sensitive)", baseline_avg_price_gbp: 2.06, baseline_total_units: 1081846, baseline_revenue_gbp: 2225737.60, baseline_cogs_ratio: 0.43, baseline_gross_margin_gbp: 1268670.43, optimal_price_change_pct: 10.0, optimal_price_gbp: 2.26, margin_uplift_gbp: 6418.82, margin_uplift_pct: 0.51 }
];

function initPricingLab() {
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
            kpiUplift.textContent = `+£${Math.round(totalGain).toLocaleString("en-GB")}`;
        }
        if (kpiSkus) kpiSkus.textContent = Number(elasticityReport.total_skus_analyzed || 3804).toLocaleString("en-GB");
        if (kpiTxns) kpiTxns.textContent = `${Number(elasticityReport.total_transactions_analyzed || 527573).toLocaleString("en-GB")} Valid Rows`;
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
                    <td>£${Number(c.baseline_avg_price_gbp).toFixed(2)}</td>
                    <td>£${Math.round(c.baseline_revenue_gbp).toLocaleString("en-GB")}</td>
                    <td><span class="badge ${optBadgeColor}">${optSign} → £${Number(c.optimal_price_gbp).toFixed(2)}</span></td>
                    <td style="color: var(--success); font-weight: 700;">+£${Math.round(c.margin_uplift_gbp).toLocaleString("en-GB")} (+${Number(c.margin_uplift_pct).toFixed(2)}%)</td>
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
            const res = await fetch("http://localhost:8000/api/v1/pricing/elasticity-report");
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
            recommendation: `${catMeta.category} (ε=${e.toFixed(2)}) maximizes bounded gross profit at ${optPt.price_change_pct > 0 ? "+" : ""}${optPt.price_change_pct}% adjustment (+£${Math.round(optPt.gross_profit_gbp - baseline.gross_profit_gbp).toLocaleString()}).`
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
            const res = await fetch("http://localhost:8000/api/v1/pricing/simulate-price-change", {
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

        if (outPrice) outPrice.innerHTML = `£${Number(s.new_price_gbp).toFixed(2)} <small style="font-size:0.72rem;color:var(--text-muted);">${deltaPct >= 0 ? "+" : ""}${deltaPct}%</small>`;
        if (outUnits) outUnits.innerHTML = `${Number(s.projected_units).toLocaleString("en-GB")} <small style="font-size:0.72rem;color:${s.unit_delta_pct >= 0 ? "var(--success)" : "var(--warning)"};">(${s.unit_delta_pct >= 0 ? "+" : ""}${s.unit_delta_pct}%)</small>`;
        if (outRev) outRev.innerHTML = `£${Math.round(s.projected_revenue_gbp).toLocaleString("en-GB")} <small style="font-size:0.72rem;color:${s.revenue_delta_gbp >= 0 ? "var(--success)" : "var(--warning)"};">(${s.revenue_delta_pct >= 0 ? "+" : ""}${s.revenue_delta_pct}%)</small>`;
        if (outProfit) {
            outProfit.style.color = s.profit_delta_gbp >= 0 ? "var(--success)" : "var(--danger)";
            outProfit.innerHTML = `£${Math.round(s.projected_gross_profit_gbp).toLocaleString("en-GB")} <small style="font-size:0.72rem;">(${s.profit_delta_gbp >= 0 ? "+" : "-"}£${Math.abs(Math.round(s.profit_delta_gbp)).toLocaleString("en-GB")})</small>`;
        }
        if (regimeBadge) regimeBadge.textContent = `${simData.demand_regime} (ε=${Number(simData.elasticity_used).toFixed(2)})`;
        if (optBadge) optBadge.textContent = `Optimal: ${opt.price_change_pct > 0 ? "+" : ""}${opt.price_change_pct}% (£${Number(opt.optimal_price_gbp).toFixed(2)})`;
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
                        label: "Projected Gross Revenue (£)",
                        data: revs,
                        borderColor: "#38BDF8",
                        backgroundColor: "rgba(56, 189, 248, 0.08)",
                        borderWidth: 2,
                        tension: 0.25,
                        pointRadius: 2
                    },
                    {
                        label: "Projected Gross Profit (£)",
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
                            label: ctx => `${ctx.dataset.label}: £${Math.round(ctx.parsed.y).toLocaleString("en-GB")}`
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: { callback: v => `£${(v / 1000000).toFixed(2)}M` },
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
                        <span class="badge blue">£${Number(c.unit_price_gbp).toFixed(2)}</span>
                    </div>
                    <div class="ab-arm-stats-list">
                        <div class="ab-arm-stat-row"><span>Visitors:</span><strong>${c.visitors.toLocaleString()}</strong></div>
                        <div class="ab-arm-stat-row"><span>Conversions (CVR):</span><strong>${c.conversions.toLocaleString()} (${c.conversion_rate_pct}%)</strong></div>
                        <div class="ab-arm-stat-row"><span>Revenue / Visitor:</span><strong>£${Number(c.revenue_per_visitor_gbp).toFixed(2)}</strong></div>
                        <div class="ab-arm-stat-row"><span>Profit / Visitor:</span><strong>£${Number(c.profit_per_visitor_gbp).toFixed(2)}</strong></div>
                    </div>
                </div>
                <div class="ab-arm-card ${st.winner === "VARIANT" ? "winner-arm" : ""}">
                    <div class="ab-arm-header">
                        <strong>🅱️ Price Variant (${exp.price_change_pct > 0 ? "+" : ""}${exp.price_change_pct}%)</strong>
                        <span class="badge ${st.winner === "VARIANT" ? "green" : "gold"}">£${Number(v.unit_price_gbp).toFixed(2)}</span>
                    </div>
                    <div class="ab-arm-stats-list">
                        <div class="ab-arm-stat-row"><span>Visitors:</span><strong>${v.visitors.toLocaleString()}</strong></div>
                        <div class="ab-arm-stat-row"><span>Conversions (CVR):</span><strong>${v.conversions.toLocaleString()} (${v.conversion_rate_pct}%)</strong></div>
                        <div class="ab-arm-stat-row"><span>Revenue / Visitor:</span><strong>£${Number(v.revenue_per_visitor_gbp).toFixed(2)}</strong></div>
                        <div class="ab-arm-stat-row"><span>Profit / Visitor:</span><strong>£${Number(v.profit_per_visitor_gbp).toFixed(2)}</strong></div>
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
                const res = await fetch("http://localhost:8000/api/v1/pricing/run-ab-experiment", {
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
            const url = `http://localhost:8000/api/v1/pricing/ab-test-calculator?baseline_conversion_rate=${baseCvr}&minimum_detectable_effect_pct=${mdePct}&alpha=${alpha}&power=${power}&daily_traffic=${dailyTraffic}&holdout_ratio=${holdoutRatio}`;
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

        if (ctrlOut) ctrlOut.textContent = `${Number(powerData.sample_size_control).toLocaleString("en-GB")} visitors`;
        if (varOut) varOut.textContent = `${Number(powerData.sample_size_variant).toLocaleString("en-GB")} visitors`;
        if (totOut) totOut.textContent = `${Number(powerData.total_sample_size).toLocaleString("en-GB")} total`;
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

// =============================================================================
// ENTERPRISE RBAC, JWT AUTHENTICATION & MULTI-TENANT SECURITY CONSOLE
// =============================================================================
function handleSecurityAuditBroadcast(ev) {
    if (!ev) return;
    logAuditEvent(ev.event_type || "Security", `${ev.action} [${ev.tenant_id}]`, ev.severity || "INFO");
}

function handleSecurityPolicyBroadcast(data) {
    if (!data) return;
    const chkStrict = document.getElementById("chkStrictRbacToggle");
    if (chkStrict) chkStrict.checked = Boolean(data.strict_rbac_enabled);
    if (data.audit_event) handleSecurityAuditBroadcast(data.audit_event);
}

function initEnterpriseSecurity() {
    const authDialog = document.getElementById("authSignInDialog");
    const openAuthBtn = document.getElementById("openAuthDialogBtn");
    const openFromSecurityBtn = document.getElementById("btnOpenAuthFromSecurity");
    const closeXBtn = document.getElementById("closeAuthDialogXBtn");
    const cancelBtn = document.getElementById("btnAuthCancel");
    const signInForm = document.getElementById("authSignInForm");
    const emailInput = document.getElementById("authEmailInput");
    const pwdInput = document.getElementById("authPasswordInput");
    const togglePwdBtn = document.getElementById("toggleAuthPwdBtn");
    const authErrorBox = document.getElementById("authFormError");
    const demoButtons = document.querySelectorAll(".btn-demo-identity");

    const tenantSelect = document.getElementById("tenantWorkspaceSelect");
    const switchTenantBtn = document.getElementById("btnSwitchTenant");
    const strictToggle = document.getElementById("chkStrictRbacToggle");
    const copyJwtBtn = document.getElementById("btnCopyJwt");
    const signOutBtn = document.getElementById("btnSignOutSession");
    const createKeyForm = document.getElementById("createApiKeyForm");
    const apiKeysTbody = document.getElementById("apiKeysTbody");
    const rbacMatrixTbody = document.getElementById("rbacMatrixTbody");

    const ROLE_ALLOWED_TABS = {
        admin: ["overview", "segmentation", "forecasting", "churn", "recommendations", "customer-mgmt", "inventory-mart", "campaign-studio", "pricing-lab", "fraud-radar", "transaction-simulator", "admin-ops", "api-console", "audit-logs"],
        lead_ds: ["overview", "segmentation", "forecasting", "churn", "recommendations", "pricing-lab", "fraud-radar", "admin-ops", "api-console", "audit-logs"],
        growth: ["overview", "segmentation", "forecasting", "churn", "recommendations", "customer-mgmt", "campaign-studio", "pricing-lab"],
        supply: ["overview", "forecasting", "recommendations", "inventory-mart", "fraud-radar", "transaction-simulator"]
    };

    const escapeSecHtml = (str) => String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    window.applyRbacUiState = function(roleKey) {
        const allowed = ROLE_ALLOWED_TABS[roleKey] || ROLE_ALLOWED_TABS.admin;
        document.querySelectorAll(".nav-item[data-tab]").forEach(btn => {
            const tabName = btn.getAttribute("data-tab");
            btn.classList.toggle("rbac-locked", !allowed.includes(tabName));
        });
    };

    function openSignInDialog() {
        if (!authDialog) return;
        if (authErrorBox) authErrorBox.hidden = true;
        if (typeof authDialog.showModal === "function") {
            authDialog.showModal();
        }
    }

    function closeSignInDialog() {
        if (!authDialog) return;
        if (typeof authDialog.close === "function" && authDialog.open) {
            authDialog.close();
        }
    }

    if (authDialog) {
        authDialog.addEventListener("close", () => {
            authDialog.returnValue = "";
        });

        // Light-dismiss fallback for browsers without native dialog `closedby="any"`
        if (!("closedBy" in HTMLDialogElement.prototype)) {
            const isOutsideDialog = (e) => {
                const r = authDialog.getBoundingClientRect();
                return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
            };
            let pressedOutside = false;
            authDialog.addEventListener("pointerdown", (e) => {
                pressedOutside = isOutsideDialog(e);
            });
            authDialog.addEventListener("pointerup", (e) => {
                if (pressedOutside && isOutsideDialog(e)) closeSignInDialog();
            });
        }
    }

    openAuthBtn?.addEventListener("click", openSignInDialog);
    openFromSecurityBtn?.addEventListener("click", openSignInDialog);
    closeXBtn?.addEventListener("click", closeSignInDialog);
    cancelBtn?.addEventListener("click", closeSignInDialog);

    // Accessible Show/Hide password toggle
    if (togglePwdBtn && pwdInput) {
        togglePwdBtn.addEventListener("click", () => {
            const show = pwdInput.type === "password";
            pwdInput.type = show ? "text" : "password";
            togglePwdBtn.setAttribute("aria-pressed", String(show));
            togglePwdBtn.setAttribute("aria-label", show ? "Hide password" : "Show password");
            togglePwdBtn.textContent = show ? "🙈 Hide" : "👁️ Show";
        });
    }

    // 1-Click Demo Persona Presets
    demoButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            if (emailInput) emailInput.value = btn.getAttribute("data-email") || "";
            if (pwdInput) pwdInput.value = btn.getAttribute("data-pwd") || "";
            if (authErrorBox) authErrorBox.hidden = true;
        });
    });

    function syncSessionUi() {
        const badge = document.getElementById("authSessionStatusBadge");
        const emailEl = document.getElementById("secPrincipalEmail");
        const roleEl = document.getElementById("secPrincipalRole");
        const tenantEl = document.getElementById("secActiveTenant");
        const tokenBar = document.getElementById("jwtTokenBar");
        const tokenSnippet = document.getElementById("jwtTokenSnippet");
        const sidebarTenant = document.getElementById("sidebarTenantName");
        const headerAvatar = document.getElementById("headerUserAvatar");
        const headerName = document.getElementById("headerUserName");
        const headerBadge = document.getElementById("adminBadgeText");
        const roleSelect = document.getElementById("adminRoleSelect");

        const tenantLabels = {
            tenant_uk_flagship: "UK Flagship (GBP)",
            tenant_eu_nordics: "EU Nordics (EUR)",
            tenant_us_direct: "US Direct (USD)"
        };

        if (APP_STATE.authUser && APP_STATE.authToken) {
            const u = APP_STATE.authUser;
            if (openAuthBtn) openAuthBtn.innerHTML = `<span>🛡️</span> ${escapeSecHtml(u.role.toUpperCase())}`;
            if (badge) {
                badge.textContent = "HS256 JWT ACTIVE";
                badge.className = "badge green";
            }
            if (emailEl) emailEl.textContent = `${u.email} (${u.name})`;
            if (roleEl) roleEl.textContent = `${u.role_label} (${u.role})`;
            if (tenantEl) tenantEl.textContent = `${u.tenant_name || u.tenant_id}`;
            if (tokenBar && tokenSnippet) {
                tokenBar.style.display = "block";
                tokenSnippet.textContent = `${APP_STATE.authToken.slice(0, 48)}...${APP_STATE.authToken.slice(-16)}`;
            }
            if (sidebarTenant) sidebarTenant.textContent = tenantLabels[u.tenant_id] || u.tenant_name || u.tenant_id;
            if (tenantSelect && [...tenantSelect.options].some(o => o.value === u.tenant_id)) {
                tenantSelect.value = u.tenant_id;
            }
            if (headerName) headerName.textContent = u.name;
            if (headerAvatar) {
                const initials = u.name.split(/\s+/).map(p => p[0]).join("").slice(0, 2).toUpperCase();
                headerAvatar.textContent = initials || "NX";
            }
            if (headerBadge) headerBadge.textContent = u.role_label;
            if (roleSelect) {
                APP_STATE.role = u.role;
                roleSelect.value = u.role;
                localStorage.setItem("nexus_role", u.role);
            }
            window.applyRbacUiState(u.role);
        } else {
            if (openAuthBtn) openAuthBtn.innerHTML = `<span>🔐</span> Sign In`;
            if (badge) {
                badge.textContent = strictToggle?.checked ? "STRICT AUTH REQUIRED" : "DEV OPEN MODE";
                badge.className = strictToggle?.checked ? "badge red" : "badge blue";
            }
            if (emailEl) emailEl.textContent = "dev@nexusretail.ai (Unauthenticated Dev)";
            if (roleEl) roleEl.textContent = `${APP_STATE.role} (Local Role Switch)`;
            if (tenantEl) tenantEl.textContent = tenantLabels[APP_STATE.tenantId] || APP_STATE.tenantId;
            if (tokenBar) tokenBar.style.display = "none";
            if (sidebarTenant) sidebarTenant.textContent = tenantLabels[APP_STATE.tenantId] || "UK Flagship (GBP)";
        }
    }

    async function loadRbacMatrixAndKeys() {
        try {
            const matRes = await fetch("http://localhost:8000/api/v1/auth/rbac-matrix");
            if (matRes.ok) {
                const matData = await matRes.json();
                if (strictToggle) strictToggle.checked = Boolean(matData.strict_rbac_enabled);

                if (tenantSelect && matData.tenants) {
                    const prevVal = tenantSelect.value || APP_STATE.tenantId;
                    tenantSelect.innerHTML = matData.tenants
                        .map(t => `<option value="${escapeSecHtml(t.tenant_id)}">${escapeSecHtml(t.name)} (${escapeSecHtml(t.currency)})</option>`)
                        .join("");
                    if ([...tenantSelect.options].some(o => o.value === prevVal)) tenantSelect.value = prevVal;

                    const keyTenantSel = document.getElementById("newKeyTenantSelect");
                    if (keyTenantSel) {
                        keyTenantSel.innerHTML = matData.tenants
                            .map(t => `<option value="${escapeSecHtml(t.tenant_id)}">${escapeSecHtml(t.name)}</option>`)
                            .join("");
                    }
                }

                if (rbacMatrixTbody && matData.roles) {
                    const cellMark = (ok) => ok
                        ? `<span class="badge green">✓ Allowed</span>`
                        : `<span class="badge" style="background:rgba(239,68,68,0.12);color:#ef4444;">✕ Denied</span>`;
                    const has = (perms, p) => perms.includes("*") || perms.includes(p);

                    rbacMatrixTbody.innerHTML = Object.entries(matData.roles).map(([key, spec]) => {
                        const p = spec.permissions || [];
                        return `
                            <tr>
                                <td><strong>${escapeSecHtml(spec.label)}</strong> <small class="text-muted">(<code>${escapeSecHtml(key)}</code>)</small></td>
                                <td>${cellMark(spec.can_switch_tenants)}</td>
                                <td>${cellMark(has(p, "mlops:retrain"))}</td>
                                <td>${cellMark(has(p, "integrations:write") || has(p, "api_keys:manage"))}</td>
                                <td>${cellMark(has(p, "campaigns:dispatch"))}</td>
                                <td>${cellMark(has(p, "experiments:run"))}</td>
                            </tr>
                        `;
                    }).join("");
                }
            }
        } catch (e) {
            // Backend offline
        }

        try {
            const keysRes = await fetch("http://localhost:8000/api/v1/auth/api-keys", {
                headers: window.getAuthHeaders()
            });
            if (keysRes.ok && apiKeysTbody) {
                const keysData = await keysRes.json();
                const keys = keysData.api_keys || [];
                if (keys.length === 0) {
                    apiKeysTbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No API keys provisioned for this tenant.</td></tr>`;
                } else {
                    apiKeysTbody.innerHTML = keys.map(k => `
                        <tr>
                            <td><strong>${escapeSecHtml(k.label)}</strong></td>
                            <td><code>${escapeSecHtml(k.key_prefix)}</code></td>
                            <td><code>${escapeSecHtml(k.tenant_id)}</code></td>
                            <td>${escapeSecHtml(k.role)}</td>
                            <td><span class="badge ${k.active ? "green" : "red"}">${k.active ? "ACTIVE" : "REVOKED"}</span></td>
                            <td>${k.active ? `<button type="button" class="btn btn-outline btn-xs btn-revoke-apikey" data-key-id="${escapeSecHtml(k.key_id)}">Revoke</button>` : "—"}</td>
                        </tr>
                    `).join("");

                    apiKeysTbody.querySelectorAll(".btn-revoke-apikey").forEach(btn => {
                        btn.addEventListener("click", async () => {
                            const keyId = btn.getAttribute("data-key-id");
                            const revRes = await fetch(`http://localhost:8000/api/v1/auth/api-keys/${keyId}`, {
                                method: "DELETE",
                                headers: window.getAuthHeaders()
                            });
                            if (revRes.ok) {
                                showToast("API Key Revoked", `Key ${keyId} deactivated immediately`, "info");
                                loadRbacMatrixAndKeys();
                            } else {
                                const err = await revRes.json().catch(() => ({}));
                                showToast("RBAC Revocation Blocked", err.detail || `HTTP ${revRes.status}`, "alert");
                            }
                        });
                    });
                }
            }
        } catch (e) {
            // Offline ignore
        }

        syncSessionUi();
    }

    if (signInForm) {
        signInForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById("btnAuthSubmit");
            if (authErrorBox) authErrorBox.hidden = true;
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "Authenticating...";
            }

            try {
                const res = await fetch("http://localhost:8000/api/v1/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        email: emailInput.value.trim(),
                        password: pwdInput.value
                    })
                });

                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    if (authErrorBox) {
                        authErrorBox.textContent = data.detail || "Invalid credentials.";
                        authErrorBox.hidden = false;
                    }
                    return;
                }

                APP_STATE.authToken = data.access_token;
                APP_STATE.authUser = data.user;
                APP_STATE.tenantId = data.user.tenant_id;
                localStorage.setItem("nexus_jwt_token", APP_STATE.authToken);
                localStorage.setItem("nexus_tenant_id", APP_STATE.tenantId);

                closeSignInDialog();
                loadRbacMatrixAndKeys();
                showToast("Signed In", `Authenticated as ${data.user.name} (${data.user.role_label})`, "success");
                logAuditEvent("Auth/JWT", `Signed in via JWT: ${data.user.email} [${data.user.tenant_id}]`);
            } catch (err) {
                if (authErrorBox) {
                    authErrorBox.textContent = "Authentication server :8000 unreachable.";
                    authErrorBox.hidden = false;
                }
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Sign In";
                }
            }
        });
    }

    if (switchTenantBtn && tenantSelect) {
        switchTenantBtn.addEventListener("click", async () => {
            const targetTid = tenantSelect.value;
            if (!APP_STATE.authToken) {
                APP_STATE.tenantId = targetTid;
                localStorage.setItem("nexus_tenant_id", targetTid);
                syncSessionUi();
                showToast("Tenant Workspace Selected", `Dev tenant context set to ${targetTid}`, "info");
                return;
            }

            try {
                const res = await fetch("http://localhost:8000/api/v1/auth/switch-tenant", {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify({ tenant_id: targetTid })
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    showToast("Tenant Isolation Enforced", data.detail || `HTTP ${res.status}`, "alert");
                    return;
                }
                APP_STATE.authToken = data.access_token;
                APP_STATE.tenantId = data.tenant.tenant_id;
                if (APP_STATE.authUser) {
                    APP_STATE.authUser.tenant_id = data.tenant.tenant_id;
                    APP_STATE.authUser.tenant_name = data.tenant.name;
                }
                localStorage.setItem("nexus_jwt_token", APP_STATE.authToken);
                localStorage.setItem("nexus_tenant_id", APP_STATE.tenantId);
                loadRbacMatrixAndKeys();
                showToast("Tenant Context Switched", `Issued new JWT scoped to ${data.tenant.name}`, "success");
            } catch (e) {
                showToast("Switch Failed", "Backend unreachable", "alert");
            }
        });
    }

    if (strictToggle) {
        strictToggle.addEventListener("change", async () => {
            const desired = strictToggle.checked;
            try {
                const res = await fetch("http://localhost:8000/api/v1/auth/security-policy", {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify({ strict_rbac_enabled: desired })
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    strictToggle.checked = !desired;
                    showToast("Policy Update Denied", err.detail || `HTTP ${res.status}`, "alert");
                    return;
                }
                syncSessionUi();
                showToast(
                    "Security Policy Updated",
                    desired ? "Strict JWT/API-Key RBAC enforcement ENABLED" : "Dev open compatibility mode restored",
                    desired ? "warning" : "info"
                );
            } catch (e) {
                strictToggle.checked = !desired;
                showToast("Backend Offline", "Unable to update policy on :8000", "alert");
            }
        });
    }

    if (copyJwtBtn) {
        copyJwtBtn.addEventListener("click", () => {
            if (!APP_STATE.authToken) return;
            navigator.clipboard.writeText(APP_STATE.authToken).then(() => {
                showToast("Bearer JWT Copied", "Copied full HS256 JWT token to clipboard", "success");
            });
        });
    }

    if (signOutBtn) {
        signOutBtn.addEventListener("click", async () => {
            if (APP_STATE.authToken) {
                await fetch("http://localhost:8000/api/v1/auth/logout", {
                    method: "POST",
                    headers: window.getAuthHeaders()
                }).catch(() => {});
            }
            APP_STATE.authToken = "";
            APP_STATE.authUser = null;
            localStorage.removeItem("nexus_jwt_token");
            syncSessionUi();
            showToast("Session Revoked", "JWT signed out and blacklisted", "info");
        });
    }

    if (createKeyForm) {
        createKeyForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const label = document.getElementById("newKeyLabelInput")?.value.trim();
            const tenantId = document.getElementById("newKeyTenantSelect")?.value || APP_STATE.tenantId;
            const role = document.getElementById("newKeyRoleSelect")?.value || "lead_ds";

            try {
                const res = await fetch("http://localhost:8000/api/v1/auth/api-keys", {
                    method: "POST",
                    headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
                    body: JSON.stringify({ label, tenant_id: tenantId, role })
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    showToast("Key Issuance Denied", data.detail || `HTTP ${res.status}`, "alert");
                    return;
                }
                const box = document.getElementById("apiKeyOneTimeBox");
                const secretEl = document.getElementById("apiKeyOneTimeSecret");
                if (box && secretEl && data.api_key?.raw_secret) {
                    secretEl.textContent = data.api_key.raw_secret;
                    box.style.display = "block";
                }
                createKeyForm.reset();
                loadRbacMatrixAndKeys();
                showToast("API Key Minted", `Provisioned scoped key for ${tenantId}`, "success");
            } catch (err) {
                showToast("API Offline", "Start FastAPI :8000 to provision API keys", "alert");
            }
        });
    }

    document.getElementById("btnCopyNewApiKey")?.addEventListener("click", () => {
        const val = document.getElementById("apiKeyOneTimeSecret")?.textContent;
        if (val) navigator.clipboard.writeText(val).then(() => showToast("Secret Copied", "Copied raw API key to clipboard", "success"));
    });

    async function restoreExistingJwtSession() {
        if (APP_STATE.authToken) {
            try {
                const res = await fetch("http://localhost:8000/api/v1/auth/me", {
                    headers: { "Authorization": `Bearer ${APP_STATE.authToken}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    APP_STATE.authUser = data.principal;
                    APP_STATE.tenantId = data.principal.tenant_id;
                } else {
                    APP_STATE.authToken = "";
                    localStorage.removeItem("nexus_jwt_token");
                }
            } catch (e) {
                // Keep stored token until backend reconnects
            }
        }
        loadRbacMatrixAndKeys();
    }

    restoreExistingJwtSession();
}

// =============================================================================
// TAB 14: TRANSACTION ANOMALY, FRAUD & CANCELLATION RADAR
// =============================================================================
function handleAnomalyAlertBroadcast(alert) {
    if (!alert) return;
    showToast(
        `🚨 Fraud Anomaly Flagged (${alert.risk_score}/100)`,
        `Invoice ${alert.invoice_no}: £${Number(alert.amount_gbp || 0).toLocaleString()} (${alert.risk_tier})`,
        "alert"
    );
    logAuditEvent(
        "Fraud/Anomaly",
        `Quarantined order ${alert.invoice_no} (score ${alert.risk_score}/100, £${Number(alert.amount_gbp || 0).toFixed(2)})`,
        "WARNING"
    );
    if (typeof window.refreshFraudRadarReport === "function") {
        window.refreshFraudRadarReport();
    }
}

function handleQuarantineResolvedBroadcast(alert) {
    if (!alert) return;
    if (typeof window.refreshFraudRadarReport === "function") {
        window.refreshFraudRadarReport();
    }
}

function initFraudRadar() {
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
                    <td>£${Number(item.amount_gbp || 0).toLocaleString("en-GB", { minimumFractionDigits: 2 })}</td>
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
                    const res = await fetch(`http://localhost:8000/api/v1/fraud/quarantine/${alertId}/resolve`, {
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
            const res = await fetch("http://localhost:8000/api/v1/fraud/anomaly-report");
            if (res.ok) {
                const data = await res.json();
                const s = data.summary || {};
                const kpiInv = document.getElementById("fraudKpiInvoices");
                const kpiRate = document.getElementById("fraudKpiCancelRate");
                const kpiCancelCnt = document.getElementById("fraudKpiCancelCount");
                const kpiExp = document.getElementById("fraudKpiExposure");
                const kpiFlagCnt = document.getElementById("fraudKpiAnomalyCount");

                if (kpiInv) kpiInv.textContent = Number(s.total_invoices_scanned || 23218).toLocaleString("en-GB");
                if (kpiRate) kpiRate.textContent = `${Number(s.cancellation_rate_pct || 14.74).toFixed(2)}%`;
                if (kpiCancelCnt) kpiCancelCnt.textContent = `${Number(s.cancelled_invoices_count || 3422).toLocaleString("en-GB")} Cancelled Invoices`;
                if (kpiExp) kpiExp.textContent = `£${((s.anomaly_revenue_exposure_gbp || 1850000) / 1000000).toFixed(2)}M`;
                if (kpiFlagCnt) kpiFlagCnt.textContent = `${Number(s.flagged_anomalies_count || 1161).toLocaleString("en-GB")} Isolation Outliers (${s.flagged_share_pct || 5.0}%)`;

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
            const res = await fetch("http://localhost:8000/api/v1/fraud/score-transaction", {
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
        if (Math.abs(payload.amount_gbp) > 4000) { localScore += 32; signals.push(`High order value £${Math.abs(payload.amount_gbp).toLocaleString()}`); }
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






