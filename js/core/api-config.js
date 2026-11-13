/**
 * Prism Retail - Unified Local / Docker / Cloud API Endpoint Resolver
 * Seamlessly routes requests across:
 *   1. Local dual-process dev (http.server :8080 + FastAPI :8000)
 *   2. Docker Compose / Nginx reverse proxy (:80 / :8080 same-origin /api/ & /ws/)
 *   3. Render / Vercel Cloud Blueprints (same-origin rewrite proxy or ?api= override)
 */

(function initPrismApiConfig() {
    const STORAGE_KEY = "prism_api_base";
    const LEGACY_STORAGE_KEY = "nexus_api_base";

    function normalizeBase(url) {
        return String(url || "").trim().replace(/\/+$/, "");
    }

    function detectInitialBase() {
        try {
            const params = new URLSearchParams(window.location.search);
            const qp = params.get("api");
            if (qp) {
                if (qp.toLowerCase() === "reset") {
                    localStorage.removeItem(STORAGE_KEY);
                    localStorage.removeItem(LEGACY_STORAGE_KEY);
                } else {
                    const clean = normalizeBase(qp);
                    localStorage.setItem(STORAGE_KEY, clean);
                    return clean;
                }
            }
            const stored = normalizeBase(localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY));
            if (stored) return stored;
        } catch (_e) {}

        const metaEl = typeof document !== "undefined"
            ? (document.querySelector('meta[name="prism-api-base"]') || document.querySelector('meta[name="nexus-api-base"]'))
            : null;
        const metaBase = normalizeBase(metaEl ? metaEl.getAttribute("content") : "");
        if (metaBase) return metaBase;

        const host = window.location.hostname || "localhost";
        const port = window.location.port || "";
        const isLocalHost = host === "localhost" || host === "127.0.0.1";

        if (isLocalHost && port && port !== "8000" && port !== "80" && port !== "443") {
            return `${window.location.protocol}//${host}:8000`;
        }
        return "";
    }

    let activeBase = detectInitialBase();
    let modeLabel = activeBase ? activeBase : "same-origin";

    async function probeNginxSameOriginProxy() {
        const host = window.location.hostname || "localhost";
        const isLocalHost = host === "localhost" || host === "127.0.0.1";
        if (!isLocalHost || !activeBase) return;
        try {
            const res = await fetch(`${window.location.origin}/health`, { method: "GET" });
            if (res.ok) {
                const body = await res.json().catch(() => null);
                if (body && body.service === "e-commerce-ml-api") {
                    activeBase = "";
                    modeLabel = "nginx-proxy";
                    nexusSyncDomEndpoints();
                }
            }
        } catch (_e) {}
    }

    window.nexusGetApiBase = function nexusGetApiBase() {
        return activeBase;
    };

    window.nexusSetApiBase = function nexusSetApiBase(newBase) {
        activeBase = normalizeBase(newBase);
        modeLabel = activeBase || "same-origin";
        try {
            if (activeBase) localStorage.setItem(STORAGE_KEY, activeBase);
            else localStorage.removeItem(STORAGE_KEY);
        } catch (_e) {}
        nexusSyncDomEndpoints();
        return activeBase;
    };

    window.nexusApiUrl = function nexusApiUrl(path = "") {
        const cleanPath = path.startsWith("/") ? path : `/${path}`;
        return activeBase ? `${activeBase}${cleanPath}` : cleanPath;
    };

    window.nexusWsUrl = function nexusWsUrl(path = "/ws/live-orders") {
        const cleanPath = path.startsWith("/") ? path : `/${path}`;
        if (activeBase) {
            return activeBase.replace(/^https:/i, "wss:").replace(/^http:/i, "ws:") + cleanPath;
        }
        const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
        return `${wsProto}//${window.location.host}${cleanPath}`;
    };

    window.nexusSyncDomEndpoints = function nexusSyncDomEndpoints() {
        if (typeof document === "undefined") return;
        const docsLink = document.getElementById("headerApiStatus");
        if (docsLink) {
            docsLink.setAttribute("href", window.nexusApiUrl("/docs"));
            docsLink.setAttribute("data-api-mode", modeLabel);
        }

        const webhookMap = {
            shopifyEndpointUrl: "/api/v1/integrations/webhook/shopify",
            stripeEndpointUrl: "/api/v1/integrations/webhook/stripe",
            wooEndpointUrl: "/api/v1/integrations/webhook/woocommerce",
        };
        Object.entries(webhookMap).forEach(([elId, epPath]) => {
            const el = document.getElementById(elId);
            if (el) el.textContent = window.nexusApiUrl(epPath);
        });
    };

    window.NEXUS_CONFIG = {
        get apiBase() {
            return activeBase;
        },
        get mode() {
            return modeLabel;
        },
    };
    window.PRISM_CONFIG = window.NEXUS_CONFIG;
    window.prismApiUrl = window.nexusApiUrl;
    window.prismWsUrl = window.nexusWsUrl;
    window.prismGetApiBase = window.nexusGetApiBase;
    window.prismSetApiBase = window.nexusSetApiBase;
    window.prismSyncDomEndpoints = window.nexusSyncDomEndpoints;

    if (typeof document !== "undefined") {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => {
                window.nexusSyncDomEndpoints();
                probeNginxSameOriginProxy();
            });
        } else {
            window.nexusSyncDomEndpoints();
            probeNginxSameOriginProxy();
        }
    }
})();

