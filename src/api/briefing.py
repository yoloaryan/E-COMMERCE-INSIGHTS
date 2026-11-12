"""
Executive Boardroom Briefing Pack & Multi-Engine Digest Exporter (Phase 23).

Aggregates live operational telemetry across 6 Nexus Retail AI engines:
1. Financial P&L Waterfall & Return Leakage Engine
2. Longitudinal Cohort Retention & RFM Segment Migration Engine
3. Inventory EOQ, Safety Stock & Purchase Order Optimization Engine
4. Market Basket Apriori Association & Cross-Sell Lift Engine
5. Autonomous Cross-Engine Telemetry Watchdog
6. Persistent SQLite WAL State Store

Produces structured JSON briefings and formatted Markdown board memos.
"""

from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.api.watchdog import get_watchdog_engine
from src.models.basket_rules import get_basket_engine
from src.models.cohort_analytics import get_cohort_engine
from src.models.financial_waterfall import get_waterfall_engine
from src.models.inventory_optimization import get_inventory_engine
from src.utils.state_store import get_state_store


class ExecutiveBriefingGenerator:
    """Synthesizes live multi-engine KPIs and executive directives into boardroom outputs."""

    @staticmethod
    def generate_briefing(country: str = "All", cogs_ratio: float = 0.58) -> Dict[str, Any]:
        finance = get_waterfall_engine().generate_waterfall_report(country=country, cogs_ratio=cogs_ratio)
        cohort_ret = get_cohort_engine().generate_retention_report(metric="customers", country=country)
        cohort_mig = get_cohort_engine().generate_migration_report()
        inventory = get_inventory_engine().generate_optimization_report()
        basket = get_basket_engine().generate_rules_report(min_lift=1.2, limit=5)
        watchdog = get_watchdog_engine().get_status()
        persistence = get_state_store().get_storage_diagnostics()

        fin_s = finance["summary"]
        ret_s = cohort_ret["summary"]
        mig_s = cohort_mig["summary"]
        inv_k = inventory["kpis"]
        bsk_s = basket["summary"]
        wd_latest = watchdog.get("latest") or {}

        def _fmt_inr(val: Any, decimals: int = 2) -> str:
            num = round(float(val or 0.0), decimals)
            neg = "-" if num < 0 else ""
            raw = f"{abs(num):.{decimals}f}"
            whole, *frac = raw.split(".")
            if len(whole) > 3:
                head, tail = whole[:-3], whole[-3:]
                groups = []
                while len(head) > 2:
                    groups.append(head[-2:])
                    head = head[:-2]
                if head:
                    groups.append(head)
                whole = ",".join(reversed(groups)) + "," + tail
            return f"{neg}₹{whole}" + (f".{frac[0]}" if frac else "")

        headline_kpis = [
            {
                "label": "Gross Ordered GMV",
                "value": _fmt_inr(fin_s['gross_gmv_gbp'], 2),
                "subtext": f"Return Rate: {fin_s['return_rate_pct']}% ({finance['filters']['country']})",
                "tone": "blue",
            },
            {
                "label": "Net Contribution Margin",
                "value": _fmt_inr(fin_s['net_contribution_margin_gbp'], 2),
                "subtext": f"{fin_s['contribution_margin_pct']}% Net Realized Margin",
                "tone": "green",
            },
            {
                "label": "Champion Stay Rate",
                "value": f"{mig_s['champion_stay_rate_pct']}%",
                "subtext": f"M1 Repeat: {ret_s['avg_month1_retention_pct']}% • Best: {ret_s['best_cohort_month']}",
                "tone": "gold",
            },
            {
                "label": "Watchdog Health & EOQ Savings",
                "value": f"{wd_latest.get('health_score', 100)}/100",
                "subtext": f"{_fmt_inr(inv_k['annual_eoq_savings_gbp'], 0)}/yr EOQ • Top Lift {bsk_s['top_lift']}x",
                "tone": "alert" if float(wd_latest.get("health_score", 100)) < 75.0 else "green",
            },
        ]

        engine_audit_rows = [
            {
                "subsystem": "Financial P&L & Return Radar",
                "architecture": "5-Step GMV-to-Contribution Bridge",
                "benchmark_metric": f"{_fmt_inr(fin_s['return_leakage_gbp'], 0)} Return Leakage ({fin_s['return_rate_pct']}%)",
                "business_impact": f"{_fmt_inr(fin_s['net_contribution_margin_gbp'], 0)} Net Realized Margin",
            },
            {
                "subsystem": "Cohort Retention & Migration",
                "architecture": "M0–M12 Matrix + 4x4 RFM Markov",
                "benchmark_metric": f"{mig_s['champion_stay_rate_pct']}% Stay • M1 {ret_s['avg_month1_retention_pct']}%",
                "business_impact": f"{mig_s['champions_slipped_count']} Champions Slipped • {mig_s['winback_upgrades_count']} Win-Backs",
            },
            {
                "subsystem": "Inventory & Supply EOQ",
                "architecture": "Wilson EOQ + ABC-XYZ + Safety Stock",
                "benchmark_metric": f"{inv_k['critical_reorder_skus']} Critical SKUs <= ROP",
                "business_impact": f"{_fmt_inr(inv_k['annual_eoq_savings_gbp'], 0)}/yr EOQ Cost Savings",
            },
            {
                "subsystem": "Market Basket Affinity",
                "architecture": "Pairwise Support / Confidence / Lift",
                "benchmark_metric": f"Top Lift {bsk_s['top_lift']}x ({basket['total_baskets_mined']} baskets)",
                "business_impact": f"Avg 10%-Off Bundle Offer: {_fmt_inr(bsk_s['avg_bundle_offer_gbp'], 2)}",
            },
            {
                "subsystem": "Persistence & Watchdog Telemetry",
                "architecture": f"{persistence['engine']} {persistence['journal_mode']} + 4-Engine Sweep",
                "benchmark_metric": f"Health {wd_latest.get('health_score', 100)}/100 • {persistence['total_persisted_records']} Rows",
                "business_impact": f"Zero-downtime ACID telemetry ({persistence['size_kb']} KB)",
            },
        ]

        directives: List[Dict[str, str]] = []
        for d in (wd_latest.get("directives") or [])[:4]:
            directives.append({
                "title": f"[{d['subsystem']}] {d['title']}",
                "detail": d["detail"],
            })

        if finance.get("high_return_skus"):
            top_ret = finance["high_return_skus"][0]
            directives.append({
                "title": f"[Financial Leakage] Audit Top Return SKU {top_ret['stock_code']}",
                "detail": f"SKU {top_ret['stock_code']} accounts for {_fmt_inr(top_ret['refund_leakage_gbp'], 2)} in refund leakage ({top_ret['root_cause_driver']}).",
            })

        return {
            "status": "success",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "platform_version": "Nexus Retail AI v4.0-prod",
            "country": finance["filters"]["country"],
            "executive_health_score": wd_latest.get("health_score", 100.0),
            "headline_kpis": headline_kpis,
            "engine_audit_rows": engine_audit_rows,
            "strategic_directives": directives,
        }

    @staticmethod
    def render_markdown_memo(briefing: Dict[str, Any]) -> str:
        """Formats structured executive briefing into a boardroom-ready Markdown report."""
        lines = [
            "# Nexus Retail AI — Executive Boardroom Briefing",
            "",
            f"- **Generated (UTC):** {briefing['generated_at']}",
            f"- **Market Scope:** {briefing['country']}",
            f"- **Platform Version:** {briefing['platform_version']}",
            f"- **Watchdog Health Score:** {briefing['executive_health_score']}/100",
            "",
            "## 1. Headline Financial & Intelligence KPIs",
            "",
            "| Metric | Current Value | Context |",
            "| :--- | :--- | :--- |",
        ]
        for kpi in briefing.get("headline_kpis", []):
            lines.append(f"| {kpi['label']} | **{kpi['value']}** | {kpi['subtext']} |")

        lines.extend([
            "",
            "## 2. Multi-Engine Production Audit",
            "",
            "| Subsystem | Architecture | Live Benchmark | Business Impact |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for row in briefing.get("engine_audit_rows", []):
            lines.append(
                f"| {row['subsystem']} | {row['architecture']} | {row['benchmark_metric']} | {row['business_impact']} |"
            )

        lines.extend([
            "",
            "## 3. Prioritized Board Strategic Directives",
            "",
        ])
        for idx, d in enumerate(briefing.get("strategic_directives", []), start=1):
            lines.append(f"{idx}. **{d['title']}** — {d['detail']}")

        lines.append("")
        return "\n".join(lines)

