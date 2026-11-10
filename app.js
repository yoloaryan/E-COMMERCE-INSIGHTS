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
    initAuditLogger();
    initApiConsole();
    initExecutiveReportModal();
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
    cart: initialCart,
    dateRange: localStorage.getItem("nexus_date_range") || "all",
    auditLogs: initialLogs
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
        }
        roleSelect.addEventListener("change", () => {
            APP_STATE.role = roleSelect.value;
            localStorage.setItem("nexus_role", APP_STATE.role);
            badgeText.textContent = roleMap[roleSelect.value];
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
const ADVANCED_TABS = ["customer-mgmt", "inventory-mart", "campaign-studio", "transaction-simulator", "admin-ops", "api-console", "audit-logs"];

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

        if (!silent) showToast("⚙️ All Tools Active", "Expanded all 12 operational, commerce & MLOps tools", "info");
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
    const crumbCurrent = document.getElementById("crumbCurrent");
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
            const autoDrop = document.getElementById("searchAutocomplete");
            if (autoDrop) autoDrop.classList.remove("active");
            const notifDrop = document.getElementById("notifDropdown");
            if (notifDrop) notifDrop.classList.remove("open");
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
// TAB 6: MLOPS CONSOLE & MODEL REGISTRY
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

    if (globalRetrainBtn) {
        globalRetrainBtn.addEventListener("click", () => {
            globalRetrainBtn.disabled = true;
            globalRetrainBtn.textContent = "⚙️ Executing Pipeline...";
            appendTermLog("ADMIN TRIGGER: Initiating full MLOps pipeline execution...");

            setTimeout(() => appendTermLog("[Pipeline] Step 1/4: Ingesting latest POS transactional logs..."), 500);
            setTimeout(() => appendTermLog("[Pipeline] Step 2/4: Rebuilding RFM feature stores and 7-day lagged windows..."), 1200);
            setTimeout(() => appendTermLog("[Pipeline] Step 3/4: Fitting Random Forest Regressor & Churn Classifier..."), 2000);
            setTimeout(() => appendTermLog("[Pipeline] Step 4/4: Exporting serialized .joblib binaries to /models/..."), 2800);
            setTimeout(() => {
                appendTermLog("SUCCESS: Pipeline completed in 3.42s. Model Registry version updated to v2.5.0-prod.");
                globalRetrainBtn.disabled = false;
                globalRetrainBtn.textContent = "⚡ Run Pipeline Ingest & Retrain";
                showToast("MLOps Pipeline Complete", "All 4 models retrained & version v2.5.0 verified", "success");
                logAuditEvent("MLOps", "Triggered manual full model retraining pipeline; checkpoint v2.5.0 verified");
            }, 3400);
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
            }, 1500);
        });
    });
}

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

function initInventoryMart() {
    const tbody = document.querySelector("#inventoryTable tbody");
    const exportBtn = document.getElementById("exportInventoryBtn");

    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            downloadCSV("inventory_sku_catalog.csv", INVENTORY_DATABASE);
            showToast("Inventory Exported", "inventory_sku_catalog.csv downloaded", "success");
            logAuditEvent("Export", "Exported SKU Inventory & Reorder Intelligence Catalog to CSV");
        });
    }

    if (!tbody) return;

    tbody.innerHTML = INVENTORY_DATABASE.map(item => {
        const isUrgent = item.daysLeft <= 14;
        const badgeColor = isUrgent ? "#EF4444" : item.daysLeft <= 21 ? "#F59E0B" : "#10B981";

        return `
            <tr>
                <td><code>${item.code}</code></td>
                <td><strong>${item.name}</strong></td>
                <td>£${item.price.toFixed(2)}</td>
                <td><strong>${item.stock.toLocaleString()} units</strong></td>
                <td>${item.burn} / day</td>
                <td><strong style="color:${badgeColor};">${item.daysLeft} days</strong></td>
                <td><span class="badge-tag" style="background:${badgeColor}22; color:${badgeColor}; font-weight:700;">${item.status}</span></td>
                <td><button class="btn btn-outline btn-xs" onclick="openRestockModal('${item.code}')">📦 Order Restock</button></td>
            </tr>
        `;
    }).join("");
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
    const list = document.getElementById("activeCampaignsList");

    const segmentStats = {
        "At-Risk VIPs": { size: "22 Accounts", rev: "£191,892.72" },
        "All At-Risk": { size: "1,180 Accounts", rev: "£2,105,745.40" },
        "Champions": { size: "708 Accounts", rev: "£5,659,383.84" },
        "Hibernating": { size: "1,602 Accounts", rev: "£555,301.26" }
    };

    if (campSegment && audienceSpan && revSpan) {
        campSegment.addEventListener("change", () => {
            const s = segmentStats[campSegment.value] || segmentStats["At-Risk VIPs"];
            audienceSpan.textContent = s.size;
            revSpan.textContent = s.rev;
        });
    }

    if (launchBtn && list) {
        launchBtn.addEventListener("click", () => {
            const seg = campSegment.value;
            const inc = campIncentive.options[campIncentive.selectedIndex].text;
            const newCamp = document.createElement("div");
            newCamp.className = "campaign-item";
            newCamp.innerHTML = `
                <div class="camp-status-badge active">JUST LAUNCHED</div>
                <h4>${seg} - ${inc.split(" ")[0]} Campaign</h4>
                <p>Strategy: ${inc}</p>
                <div class="camp-stats">
                    <div><small>Status</small><strong class="text-green">Active</strong></div>
                    <div><small>Audience</small><strong>${segmentStats[seg].size}</strong></div>
                    <div><small>Channel</small><strong>Omni-Channel</strong></div>
                    <div><small>Revenue Target</small><strong class="text-green">${segmentStats[seg].rev}</strong></div>
                </div>
            `;
            list.prepend(newCamp);
            showToast("Campaign Dispatched", `Targeting ${segmentStats[seg].size} with ${inc.split(" ")[0]}`, "success");
            logAuditEvent("Marketing", `Launched automated retention campaign targeting ${seg} (${segmentStats[seg].size})`);
        });
    }
}

// =============================================================================
// TAB 10: LIVE POS & TRANSACTION INJECTION SIMULATOR
// =============================================================================
function initTransactionSimulator() {
    const form = document.getElementById("posSimulatorForm");
    const feedback = document.getElementById("simFeedbackArea");

    if (!form || !feedback) return;

    form.addEventListener("submit", (e) => {
        e.preventDefault();

        const cid = document.getElementById("simCustId").value.trim();
        const skuSelect = document.getElementById("simSkuCode");
        const sku = skuSelect.value;
        const skuText = skuSelect.options[skuSelect.selectedIndex].text;
        const qty = parseInt(document.getElementById("simQty").value, 10);
        const price = parseFloat(document.getElementById("simPrice").value);
        const total = qty * price;
        const now = new Date().toISOString().replace("T", " ").substring(0, 19);

        let cust = MASTER_CUSTOMERS.find(c => c.id === cid);
        const prevProb = cust ? cust.churnProb : 0.75;
        const prevRecency = cust ? cust.recency : 65;

        if (cust) {
            cust.spend += total;
            cust.orders += 1;
            cust.aov = cust.spend / cust.orders;
            cust.recency = 0;
            cust.churnProb = Math.max(0.04, cust.churnProb * 0.45);
        } else {
            cust = { id: cid, segment: "Loyal Customers", spend: total, orders: 1, aov: total, recency: 0, churnProb: 0.15, history: [`${qty}x ${skuText}`] };
            MASTER_CUSTOMERS.unshift(cust);
        }

        feedback.innerHTML = `
            <div class="sim-reaction-card" style="width: 100%;">
                <div style="background:var(--success-light); border:1px solid var(--success); padding:1rem; border-radius:8px; margin-bottom:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:var(--success);">✓ TRANSACTION COMMITTED TO ANALYTICAL MART</strong>
                        <small style="color:var(--text-muted); font-family:var(--font-mono);">${now}</small>
                    </div>
                    <div style="font-size:0.92rem; color:var(--text-primary); margin-top:0.35rem;">
                        Customer <strong>#${cid}</strong> purchased <strong>${qty}x ${skuText}</strong> for <strong>£${total.toFixed(2)}</strong>.
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
                        <strong>Updated Persona</strong>
                        <span style="color:var(--primary);">${cust.segment}</span>
                    </div>
                </div>
            </div>
        `;

        showToast("POS Transaction Injected", `£${total.toFixed(2)} recorded for Customer #${cid}. Recency reset to 0d.`, "success");
        logAuditEvent("POS/Injection", `Simulated £${total.toFixed(2)} order for Customer #${cid} (SKU: ${sku}). Recency reset to 0d.`);
        
        initCustomerLedger();
        initChurnTab();
    });
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
        skuForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const code = document.getElementById("modalSkuCode").value.trim().toUpperCase();
            const name = document.getElementById("modalSkuName").value.trim();
            const price = parseFloat(document.getElementById("modalSkuPrice").value) || 4.99;
            const stock = parseInt(document.getElementById("modalSkuStock").value, 10) || 250;
            const burn = parseInt(document.getElementById("modalSkuBurn").value, 10) || 10;

            const daysLeft = Math.round(stock / burn);
            const status = daysLeft <= 14 ? "Critical Reorder" : daysLeft <= 21 ? "Reorder Approaching" : "Healthy Stock";

            INVENTORY_DATABASE.unshift({
                code: code,
                name: name,
                price: price,
                stock: stock,
                burn: burn,
                daysLeft: daysLeft,
                status: status
            });

            initInventoryMart();
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
        restockForm.addEventListener("submit", (e) => {
            e.preventDefault();
            if (!currentRestockItem) return;

            const addQty = parseInt(restockQtyInput.value, 10) || 500;
            const supplier = document.getElementById("modalRestockSupplier").value;
            const leadDays = parseInt(document.getElementById("modalRestockLeadDays").value, 10) || 3;

            currentRestockItem.stock += addQty;
            currentRestockItem.daysLeft = Math.round(currentRestockItem.stock / currentRestockItem.burn);
            currentRestockItem.status = currentRestockItem.daysLeft <= 14 ? "Critical Reorder" : currentRestockItem.daysLeft <= 21 ? "Reorder Approaching" : "Healthy Stock";

            initInventoryMart();
            closeRestockModal();
            showToast("Purchase Order Dispatched", `Added ${addQty} units to SKU [${currentRestockItem.code}]. Lead Time: ${leadDays}d (${supplier})`, "success");
            logAuditEvent("Inventory", `Dispatched replenishment PO: ${addQty} units for SKU [${currentRestockItem.code}] via ${supplier}`);
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
        path: "/api/v1/predict/churn",
        url: "http://localhost:8080/api/v1/predict/churn",
        payload: {
            customer_id: "14096",
            recency_days: 84,
            frequency_orders: 17,
            monetary_spend: 65164.79,
            avg_order_value: 3833.22,
            cancellation_rate: 0.04
        },
        handler: (req) => {
            const r = req.recency_days || 80;
            const m = req.monetary_spend || 1000;
            const prob = Math.min(0.96, Math.max(0.04, 0.15 + (r / 120) * 0.75 - (m > 10000 ? 0.08 : 0)));
            const isHigh = prob >= 0.70;
            return {
                status: "success",
                model_checkpoint: "RandomForestClassifier_balanced_v2.4",
                inference_timestamp: new Date().toISOString(),
                data: {
                    customer_id: req.customer_id,
                    churn_probability: parseFloat(prob.toFixed(4)),
                    churn_risk_tier: isHigh ? "HIGH_RISK" : prob >= 0.35 ? "MEDIUM_RISK" : "LOW_RISK",
                    action_required: isHigh ? "TRIGGER_ACCOUNT_CONCIERGE_OUTREACH" : "STANDARD_LOYALTY_CADENCE",
                    features_evaluated: {
                        recency_days: r,
                        frequency_orders: req.frequency_orders || 1,
                        monetary_spend_gbp: m
                    }
                }
            };
        }
    },
    forecast: {
        method: "POST",
        path: "/api/v1/forecast/sales",
        url: "http://localhost:8080/api/v1/forecast/sales",
        payload: {
            horizon_days: 14,
            day_of_week: 4,
            promo_discount_pct: 15,
            ad_spend_multiplier: 1.20,
            seasonal_surge_pct: 25
        },
        handler: (req) => {
            const base = 28450.00;
            const dayMult = req.day_of_week === 4 ? 1.34 : req.day_of_week === 0 ? 0.65 : 1.05;
            const promoLift = 1 + (req.promo_discount_pct * 0.0145);
            const adLift = Math.pow(req.ad_spend_multiplier || 1, 0.42);
            const season = 1 + ((req.seasonal_surge_pct || 0) / 100);
            const projectedDaily = base * dayMult * promoLift * adLift * season;
            return {
                status: "success",
                model_checkpoint: "RandomForestRegressor_100Trees_v2.4",
                inference_timestamp: new Date().toISOString(),
                data: {
                    target_day_index: req.day_of_week,
                    projected_daily_gmv_gbp: parseFloat(projectedDaily.toFixed(2)),
                    horizon_aggregate_gmv_gbp: parseFloat((projectedDaily * (req.horizon_days || 14) * 0.94).toFixed(2)),
                    confidence_interval_95: [
                        parseFloat((projectedDaily * 0.88).toFixed(2)),
                        parseFloat((projectedDaily * 1.14).toFixed(2))
                    ],
                    mape_accuracy_metric: "26.28%"
                }
            };
        }
    },
    recommend: {
        method: "GET",
        path: "/api/v1/recommend/skus",
        url: "http://localhost:8080/api/v1/recommend/skus?base_stock_code=22423&top_n=4",
        payload: {
            base_stock_code: "22423",
            top_n: 4,
            algorithm: "item_cosine_similarity"
        },
        handler: (req) => {
            const code = req.base_stock_code || "22423";
            const pool = RECS_CATALOG[code] || RECS_CATALOG["22423"];
            return {
                status: "success",
                model_checkpoint: "SparseCosineSimilarityMatrix_3182x4333",
                inference_timestamp: new Date().toISOString(),
                data: {
                    base_sku: code,
                    base_product_name: pool.name,
                    recommended_skus: pool.items.slice(0, req.top_n || 4).map(item => ({
                        stock_code: item.sku,
                        name: item.desc,
                        unit_price_gbp: item.price,
                        cosine_similarity_score: item.score
                    }))
                }
            };
        }
    },
    segment: {
        method: "POST",
        path: "/api/v1/segment/classify",
        url: "http://localhost:8080/api/v1/segment/classify",
        payload: {
            recency_days: 2,
            frequency_orders: 35,
            monetary_spend: 5391.21
        },
        handler: (req) => {
            const r = req.recency_days || 10;
            const f = req.frequency_orders || 5;
            const m = req.monetary_spend || 1000;
            let persona = "Occasional / Hibernating";
            let clusterId = 3;
            if (m > 2500 && f > 15 && r < 30) {
                persona = "Champions (VIP)";
                clusterId = 0;
            } else if (r > 60 && m > 1000) {
                persona = "At-Risk / Lapsing";
                clusterId = 1;
            } else if (r < 30) {
                persona = "Loyal Customers";
                clusterId = 2;
            }
            return {
                status: "success",
                model_checkpoint: "KMeans_K4_StandardScaler_Log1p",
                inference_timestamp: new Date().toISOString(),
                data: {
                    assigned_cluster_id: clusterId,
                    assigned_persona: persona,
                    log1p_rfm_vector: [
                        parseFloat(Math.log1p(r).toFixed(4)),
                        parseFloat(Math.log1p(f).toFixed(4)),
                        parseFloat(Math.log1p(m).toFixed(4))
                    ],
                    marketing_action: persona.includes("VIP") ? "EXCLUSIVE_PREVIEW_WHITE_GLOVE" : persona.includes("At-Risk") ? "DISCOUNTED_WIN_BACK_SEQUENCE" : "NURTURE_CROSS_SELL"
                }
            };
        }
    }
};

function initApiConsole() {
    const endpointSelect = document.getElementById("apiEndpointSelect");
    const methodBadge = document.getElementById("apiMethodBadge");
    const requestJson = document.getElementById("apiRequestJson");
    const responseJson = document.getElementById("apiResponseJson");
    const responseUrl = document.getElementById("apiResponseUrl");
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
        executeEndpoint(key);
    }

    function executeEndpoint(key) {
        const ep = API_ENDPOINTS[key || endpointSelect.value];
        if (!ep) return;

        let parsedBody = ep.payload;
        try {
            parsedBody = JSON.parse(requestJson.value);
        } catch (e) {
            showToast("Invalid JSON", "Request body contains invalid JSON syntax", "alert");
            return;
        }

        const simLatency = (Math.random() * 5 + 3.2).toFixed(1);
        if (latencyPill) latencyPill.textContent = `Latency: ${simLatency} ms`;

        const resp = ep.handler(parsedBody);
        responseJson.textContent = JSON.stringify(resp, null, 2);
        logAuditEvent("API", `Executed test call to ${ep.path} (${simLatency}ms, HTTP 200)`);
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
            executeEndpoint(endpointSelect.value);
            showToast("Endpoint Executed", `Status 200 OK | Returned in sub-10ms`, "success");
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


