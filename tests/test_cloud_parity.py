"""
Verification Suite for Cloud Full-Stack Parity & On-Demand ES Module Code-Splitting.
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_code_split_modules_exist_and_export_initializers():
    app_js = (ROOT_DIR / "app.js").read_text(encoding="utf-8")
    matches = re.findall(r'path:\s*"\./(js/modules/[^"?]+\.js)[^"]*",\s*initName:\s*"([^"]+)"', app_js)
    assert len(matches) == 7, f"Expected 7 code-split lazy route bindings, found {len(matches)}: {matches}"

    for rel_path, init_fn in matches:
        mod_file = ROOT_DIR / rel_path
        assert mod_file.exists(), f"Missing code-split module: {rel_path}"
        content = mod_file.read_text(encoding="utf-8")
        assert re.search(rf"export\s+(?:async\s+)?function\s+{init_fn}\(", content), f"{rel_path} must export {init_fn}"


def test_zero_hardcoded_localhost_urls_in_runtime_clients():
    for rel in [
        "app.js",
        "js/modules/pricing-lab.js",
        "js/modules/fraud-radar.js",
        "js/modules/warehouse-lab.js",
        "js/modules/survival-xai.js",
        "js/modules/tax-invoice.js",
        "js/modules/conformal-budget.js",
    ]:
        text = (ROOT_DIR / rel).read_text(encoding="utf-8")
        # Only console diagnostic text may mention host; all fetch/WebSocket calls must use nexusApiUrl/nexusWsUrl
        bad_fetches = re.findall(r'(?:fetch|WebSocket|window\.open)\(\s*["\'`][^"\'`]*localhost:8000', text)
        assert not bad_fetches, f"Found hardcoded localhost:8000 call in {rel}: {bad_fetches}"

    html = (ROOT_DIR / "index.html").read_text(encoding="utf-8")
    assert '<meta name="nexus-api-base"' in html
    assert 'js/core/api-config.js' in html
    assert 'href="http://localhost:8000/docs"' not in html


def test_cloud_blueprints_and_docker_copy_split_js():
    dockerfile = (ROOT_DIR / "Dockerfile").read_text(encoding="utf-8")
    nginx_conf = (ROOT_DIR / "nginx.conf").read_text(encoding="utf-8")
    render_yaml = (ROOT_DIR / "render.yaml").read_text(encoding="utf-8")

    assert "COPY js/ /usr/share/nginx/html/js/" in dockerfile
    assert "location /api/" in nginx_conf
    assert "location /ws/" in nginx_conf
    assert "nexus-retail-api" in render_yaml
    assert "source: /api/*" in render_yaml
    assert "source: /ws/*" in render_yaml
    assert "path: /js/*" in render_yaml

