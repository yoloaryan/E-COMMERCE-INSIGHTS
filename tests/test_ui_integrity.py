"""
Static & Structural UI/UX Integrity Verification Suite for Nexus Retail AI.
Guards all 14 dashboard modules, DOM IDs, labels, dialog semantics, toast styles,
and API console endpoint alignments across index.html, style.css, and app.js.
"""

from collections import Counter
from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT_DIR / "index.html"
STYLE_CSS = ROOT_DIR / "style.css"
APP_JS = ROOT_DIR / "app.js"


def test_all_15_tabs_and_navigation_match():
    """Verify every sidebar data-tab maps 1-to-1 with a tab-pane section and JS tabMeta."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    js = APP_JS.read_text(encoding="utf-8")

    nav_tabs = re.findall(r'class="nav-item[^"]*"\s+data-tab="([^"]+)"', html)
    pane_tabs = re.findall(r'<section\s+id="tab-([^"]+)"\s+class="tab-pane', html)

    assert len(nav_tabs) == 15, f"Expected 15 navigation modules, found {len(nav_tabs)}: {nav_tabs}"
    assert set(nav_tabs) == set(pane_tabs), f"Tab mismatch: nav={set(nav_tabs) ^ set(pane_tabs)}"

    # Confirm cache-bust versions match cleanly between CSS and JS
    css_ver = re.search(r'style\.css\?v=([0-9.]+)', html)
    js_ver = re.search(r'app\.js\?v=([0-9.]+)', html)
    assert css_ver and js_ver
    assert css_ver.group(1) == js_ver.group(1)

    # Confirm every tab appears in JS tabMeta
    for tab in nav_tabs:
        assert (f"{tab}:" in js or f'"{tab}":' in js), f"Tab '{tab}' missing from tabMeta in app.js"


def test_no_duplicate_dom_ids_and_valid_labels():
    """Assert zero duplicate HTML IDs and every <label for='...'> resolves to a real control."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    all_ids = re.findall(r'\bid="([^"]+)"', html)
    counts = Counter(all_ids)
    dupes = {k: v for k, v in counts.items() if v > 1}
    assert not dupes, f"Duplicate DOM IDs found in index.html: {dupes}"

    id_set = set(all_ids)
    label_fors = re.findall(r'<label[^>]+for="([^"]+)"', html)
    missing_targets = [target for target in label_fors if target not in id_set]
    assert not missing_targets, f"<label for='...'> targets missing from DOM: {missing_targets}"


def test_api_console_targets_fastapi_and_toast_styles():
    """Verify Developer API Console points to FastAPI :8000 and all toast classes exist in CSS."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")
    js = APP_JS.read_text(encoding="utf-8")

    assert "localhost:8080/api/" not in html, "Found stale :8080/api/ reference in index.html"
    assert "localhost:8080/api/" not in js, "Found stale :8080/api/ reference in app.js"

    for toast_cls in ["success", "alert", "danger", "warning", "info"]:
        assert f".toast.{toast_cls}" in css, f"Missing CSS rule for .toast.{toast_cls}"


def test_native_auth_dialog_accessibility_contract():
    """Verify native <dialog id='authSignInDialog'> follows top-layer accessibility best practices."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    match = re.search(r'<dialog[^>]+id="authSignInDialog"[^>]*>', html)
    assert match, "authSignInDialog <dialog> missing from index.html"
    tag = match.group(0)
    assert 'closedby="any"' in tag
    assert 'aria-labelledby="authDialogTitle"' in tag
    assert 'role="dialog"' not in tag
    assert 'aria-modal=' not in tag


def test_liquid_glass_design_system_and_fallbacks():
    """Verify Liquid Glass tokens, dark/light color-scheme parity, and accessibility fallbacks."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert '<meta name="color-scheme" content="light dark">' in html
    assert "--glass-bg:" in css
    assert "--glass-shadow:" in css
    assert "backdrop-filter: var(--glass-backdrop)" in css
    assert "@media (prefers-reduced-transparency: reduce)" in css
    assert "@supports not (backdrop-filter: blur(1px))" in css
    assert "@media (forced-colors: active)" in css
