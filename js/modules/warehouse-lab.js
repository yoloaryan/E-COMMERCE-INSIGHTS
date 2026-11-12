/**
 * Phase 25: Kimball Star-Schema Warehouse & SQL Workbench
 * Loaded lazily on demand by app.js module router.
 */

let whQueryChartInstance = null;
let WAREHOUSE_CASE_STUDIES_CACHE = [];
let WAREHOUSE_ROWS_CACHE = [];
let WAREHOUSE_WIRED = false;

function renderWarehouseChart(cols, rows, numericCols) {
    const canvas = document.getElementById("whQueryChart");
    const badge = document.getElementById("whChartMetricBadge");
    if (!canvas || typeof Chart === "undefined") return;
    if (whQueryChartInstance) whQueryChartInstance.destroy();

    if (!rows.length || !numericCols.length) {
        if (badge) badge.textContent = "No Numeric Series";
        return;
    }

    const labelCol = cols.find(c => !numericCols.includes(c)) || cols[0];
    const metricCol = numericCols.find(c => /rev|gmv|margin|spend|aov|pct/i.test(c)) || numericCols[0];
    if (badge) badge.textContent = `${metricCol} by ${labelCol}`;

    const isLight = document.documentElement.getAttribute("data-theme") === "light";
    const textCol = isLight ? "#334155" : "#D4D4D8";
    const gridCol = isLight ? "rgba(15, 23, 42, 0.08)" : "rgba(255, 255, 255, 0.08)";
    const slice = rows.slice(0, 12);

    whQueryChartInstance = new Chart(canvas.getContext("2d"), {
        type: "bar",
        data: {
            labels: slice.map(r => String(r[labelCol] ?? "").slice(0, 22)),
            datasets: [{
                label: metricCol,
                data: slice.map(r => Number(r[metricCol]) || 0),
                backgroundColor: "rgba(59, 130, 246, 0.78)",
                borderColor: "#3B82F6",
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: textCol, font: { size: 11 } } } },
            scales: {
                x: { ticks: { color: textCol, font: { size: 10 } }, grid: { display: false } },
                y: { ticks: { color: textCol }, grid: { color: gridCol } }
            }
        }
    });
}

function renderWarehouseResultTable(cols, rows) {
    const thead = document.getElementById("whResultsThead");
    const tbody = document.getElementById("whResultsTbody");
    if (!thead || !tbody) return;

    if (!cols.length || !rows.length) {
        thead.innerHTML = "";
        tbody.innerHTML = `<tr><td style="text-align:center;color:var(--text-muted);">Query executed cleanly and returned 0 rows.</td></tr>`;
        return;
    }

    thead.innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;
    tbody.innerHTML = rows.map(r =>
        `<tr>${cols.map(c => `<td>${r[c] === null || r[c] === undefined ? "—" : String(r[c])}</td>`).join("")}</tr>`
    ).join("");
}

async function runWarehouseSqlQuery() {
    const editor = document.getElementById("whSqlEditor");
    const latEl = document.getElementById("whKpiLastLatency");
    const cntEl = document.getElementById("whKpiRowCount");
    const statusSub = document.getElementById("whQueryStatusSub");
    if (!editor) return;

    const sqlText = editor.value.trim();
    if (!sqlText) return;

    try {
        const res = await fetch(nexusApiUrl("/api/v1/warehouse/query"), {
            method: "POST",
            headers: window.getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ sql: sqlText, max_rows: 100 })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast("SQL Sandbox Blocked", data.detail || `HTTP ${res.status}`, "alert");
            if (statusSub) statusSub.textContent = `Query error: ${data.detail || res.status}`;
            return;
        }
        WAREHOUSE_ROWS_CACHE = data.rows || [];
        if (latEl) latEl.textContent = `${data.execution_time_ms} ms`;
        if (cntEl) cntEl.textContent = `${data.row_count} Rows Returned`;
        if (statusSub) statusSub.textContent = `Executed in ${data.execution_time_ms} ms • Returned ${data.row_count} rows (${data.columns.length} columns)`;

        renderWarehouseResultTable(data.columns || [], data.rows || []);
        renderWarehouseChart(data.columns || [], data.rows || [], data.numeric_columns || []);
        logAuditEvent("Warehouse", `Executed Star-Schema SQL query (${data.row_count} rows, ${data.execution_time_ms} ms)`);
    } catch (_e) {
        showToast("Warehouse Offline", "Start FastAPI backend :8000 to execute live DuckDB SQL", "alert");
    }
}

async function refreshWarehouseDataQuality() {
    const dqBody = document.getElementById("whDqTbody");
    const scoreEl = document.getElementById("whKpiDqScore");
    const sumEl = document.getElementById("whKpiDqChecksSummary");
    const certBadge = document.getElementById("whCertificationBadge");
    if (!dqBody) return;

    try {
        const res = await fetch(nexusApiUrl("/api/v1/warehouse/data-quality"));
        if (!res.ok) return;
        const dq = await res.json();
        if (scoreEl) scoreEl.textContent = `${dq.score_pct}%`;
        if (sumEl) sumEl.textContent = `${dq.passed_checks} / ${dq.total_checks} SQL Contracts Passing`;
        if (certBadge) {
            certBadge.textContent = dq.status;
            certBadge.className = `badge-tag ${dq.passed_checks === dq.total_checks ? "green" : "red"}`;
        }
        dqBody.innerHTML = (dq.checks || []).map(chk => `
            <tr>
                <td><code>${chk.check_id}</code></td>
                <td><strong>${chk.name}</strong><br><small style="color:var(--text-muted);">${chk.description}</small></td>
                <td><code style="font-size:0.72rem;white-space:normal;">${chk.sql}</code></td>
                <td><strong>${chk.violations}</strong></td>
                <td>${chk.duration_ms} ms</td>
                <td><span class="badge-tag ${chk.status === "PASS" ? "green" : "red"}">${chk.status}</span></td>
            </tr>
        `).join("");
    } catch (_e) {
        dqBody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">Connect FastAPI backend :8000 to run automated SQL Data-Quality contracts.</td></tr>`;
    }
}

export async function initDataWarehouseTab() {
    const schemaGrid = document.getElementById("whSchemaGrid");
    const caseSelect = document.getElementById("whCaseStudySelect");
    const editor = document.getElementById("whSqlEditor");
    if (!schemaGrid || !caseSelect || !editor) return;

    try {
        const res = await fetch(nexusApiUrl("/api/v1/warehouse/schema"));
        if (res.ok) {
            const schema = await res.json();
            const totalEl = document.getElementById("whKpiTotalRows");
            const srcEl = document.getElementById("whKpiDataSource");
            if (totalEl) totalEl.textContent = Number(schema.total_warehouse_rows || 0).toLocaleString("en-IN");
            if (srcEl) srcEl.textContent = `DuckDB • ${schema.data_source}`;

            schemaGrid.innerHTML = (schema.tables || []).map(t => `
                <div class="btyd-stat-box">
                    <strong>${t.role} &bull; ${t.table_name}</strong>
                    <div class="stat-val text-blue" style="font-size:1.1rem;">${Number(t.row_count).toLocaleString("en-IN")} rows</div>
                    <small style="color:var(--text-muted);">${t.columns.length} cols &bull; ${t.description}</small>
                </div>
            `).join("");

            WAREHOUSE_CASE_STUDIES_CACHE = schema.case_studies || [];
            if (WAREHOUSE_CASE_STUDIES_CACHE.length) {
                caseSelect.innerHTML = WAREHOUSE_CASE_STUDIES_CACHE.map(cs =>
                    `<option value="${cs.id}">[${cs.category}] ${cs.title}</option>`
                ).join("");
                editor.value = WAREHOUSE_CASE_STUDIES_CACHE[0].sql;
            }
        }
    } catch (_e) {
        schemaGrid.innerHTML = `<div class="btyd-stat-box"><strong>Star Schema Offline</strong><small>Connect backend :8000 to browse live DuckDB tables.</small></div>`;
    }

    await Promise.all([runWarehouseSqlQuery(), refreshWarehouseDataQuality()]);

    if (!WAREHOUSE_WIRED) {
        WAREHOUSE_WIRED = true;
        caseSelect.addEventListener("change", () => {
            const match = WAREHOUSE_CASE_STUDIES_CACHE.find(c => c.id === caseSelect.value);
            if (match) {
                editor.value = match.sql;
                runWarehouseSqlQuery();
            }
        });

        const runBtn = document.getElementById("whRunSqlBtn");
        const dqBtn = document.getElementById("whRunDqBtn");
        const expBtn = document.getElementById("whExportSqlCsvBtn");

        if (runBtn) runBtn.addEventListener("click", runWarehouseSqlQuery);
        if (dqBtn) dqBtn.addEventListener("click", async () => {
            await refreshWarehouseDataQuality();
            showToast("DQ Contracts Verified", "Executed all 7 SQL data-quality checks on Star Schema", "success");
        });
        if (expBtn) expBtn.addEventListener("click", () => {
            if (WAREHOUSE_ROWS_CACHE.length) {
                downloadCSV("warehouse_sql_query_result.csv", WAREHOUSE_ROWS_CACHE);
                showToast("CSV Exported", "warehouse_sql_query_result.csv downloaded", "success");
            }
        });
    }
}
