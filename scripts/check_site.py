#!/usr/bin/env python3
"""Pre-publish checks for the Fridge-Worthy static site.

Usage:
    python3 scripts/check_site.py [--site DIR] [--shots DIR] [--no-browser]

Static checks:
  - no inline <style>, no inline <script> code (JSON data blocks are allowed), no style= or on*= attributes
  - every http(s) URL is SITE_URL, REPO_URL (or a path under it), or https://wa.me/
  - og:image is not fridge.jpg
  - no og:/twitter: tag and no site text file contains a term from the private blocklist
  - every local file referenced from HTML/CSS exists
  - the private scanner passes on the site folder (if configured)
  - the Chat prompt in index.html's <template> matches the fenced prompt in guides/chat.md
Browser checks (Python Playwright, Chromium, served with the real _headers so CSP applies),
on the main page and demo/, at 320, 375, 430, 768 and 1280 px wide:
  - no horizontal scroll, no console errors / page errors / CSP violations / outside requests
  - every visible link, button, and summary is at least 44x44 px
  Main page only:
  - fonts load; "Copy the Chat prompt" puts the guide's prompt on the clipboard and shows "Copied"
  - Copy link and share links work; nav highlights the section on screen
Optional environment variables (both point to a private list or script kept outside the repo):
  FW_PRIVATE_BLOCKLIST  path to a text file of banned terms, one per line (# starts a comment).
                        Matched case-insensitively (short terms as whole words) against og:/twitter: tags and all site text files.
  FW_SCAN_PRIVATE       path to a private scanner script, run as: bash SCRIPT SITE_DIR.
                        Skipped if not set.
Exit code 0 = all passed.
"""
import argparse
import functools
import html
import html.parser
import http.server
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SITE_URL = "https://fridge-worthy.pages.dev/"
REPO_URL = "https://github.com/cristchey83/fridge-worthy"
ALLOWED_URL_PREFIXES = (SITE_URL, REPO_URL + "/", "https://wa.me/")
ALLOWED_URL_EXACT = {REPO_URL, "https://wa.me"}
# XML namespace identifiers are never fetched by the browser.
NAMESPACE_URLS = {"http://www.w3.org/2000/svg"}
WIDTHS = (320, 375, 430, 768, 1280)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SITE = ROOT / "site"
TEXT_EXT = {".html", ".css", ".js", ".svg", ".txt", ".json", ".xml", ""}

failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL:", msg)


def text_files(site):
    for p in sorted(site.rglob("*")):
        if p.is_file() and p.suffix in TEXT_EXT:
            yield p


class PageParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []          # (attr, value)
        self.meta = []          # (property/name, content)
        self.problems = []
        self._script = None     # attrs of an open <script>
        self._script_text = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k, v in attrs:
            if k == "style":
                self.problems.append(f"style= attribute on <{tag}>")
            if k.startswith("on"):
                self.problems.append(f"inline event handler {k}= on <{tag}>")
            if k in ("href", "src", "poster", "content") and v:
                self.refs.append((k, v))
            if k == "srcset" and v:
                for part in v.split(","):
                    self.refs.append(("src", part.strip().split(" ")[0]))
        if tag == "style":
            self.problems.append("inline <style> block")
        if tag == "script":
            self._script, self._script_text = a, ""
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key:
                self.meta.append((key, a.get("content", "")))

    def handle_data(self, data):
        if self._script is not None:
            self._script_text += data

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            is_data = self._script.get("type", "").lower() in ("application/json", "application/ld+json")
            if self._script_text.strip() and not is_data:
                self.problems.append("inline <script> code")
            if not self._script.get("src") and not is_data and not self._script_text.strip():
                self.problems.append("<script> without src")
            self._script = None


def is_local_ref(v):
    return not re.match(r"^(https?:|mailto:|sms:|tel:|data:|#|//)", v) and v != ""


def term_in(term, low):
    """Case-folded match; terms of 4 chars or fewer must be whole words."""
    if len(term) <= 4:
        return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", low) is not None
    return term in low


def load_blocklist():
    path = os.environ.get("FW_PRIVATE_BLOCKLIST")
    if not path:
        print("skipped private blocklist (FW_PRIVATE_BLOCKLIST not set)")
        return []
    p = Path(path).expanduser()
    if not p.is_file():
        fail("FW_PRIVATE_BLOCKLIST file not found")
        return []
    terms = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            terms.append(line)
    print(f"loaded {len(terms)} private blocklist term(s)")
    return terms


def check_static(site):
    print(f"== Static checks on {site}")
    blocklist = load_blocklist()
    html_files = sorted(site.rglob("*.html"))
    if not (site / "index.html").exists():
        fail("site/index.html missing")
    for f in html_files:
        rel = f.relative_to(site)
        p = PageParser()
        p.feed(f.read_text(encoding="utf-8"))
        for prob in p.problems:
            fail(f"{rel}: {prob}")
        for key, content in p.meta:
            if key.startswith("og:") or key.startswith("twitter:"):
                low = content.lower()
                if key.startswith("og:image") and "fridge.jpg" in low:
                    fail(f"{rel}: {key} uses fridge.jpg")
                for bad in blocklist:
                    if term_in(bad, low):
                        fail(f"{rel}: {key} contains a blocklisted term")
        if str(rel) != "404.html" and any(k == "robots" and "noindex" in c for k, c in p.meta):
            fail(f"{rel}: still has noindex")
        for attr, v in p.refs:
            if attr == "content":
                continue
            if v.startswith("//"):
                fail(f"{rel}: protocol-relative URL {v}")
            if is_local_ref(v):
                path = v.split("#")[0].split("?")[0]
                target = (site / path.lstrip("/") if path.startswith("/") else f.parent / path).resolve()
                if not target.exists():
                    fail(f"{rel}: missing file {v}")
    for f in sorted(site.rglob("*.css")):
        for v in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", f.read_text(encoding="utf-8")):
            if is_local_ref(v):
                if not (f.parent / v).resolve().exists():
                    fail(f"{f.relative_to(site)}: missing file {v}")
            elif not v.startswith("data:"):
                fail(f"{f.relative_to(site)}: external url() {v}")

    # URL allowlist across every served text file. Font license texts are skipped:
    # they're legal notices, never fetched or linked.
    for f in text_files(site):
        rel = f.relative_to(site)
        if rel.parts[0] == "fonts" and f.suffix == ".txt":
            continue
        for url in re.findall(r"https?://[^\s\"'<>)\\]+", f.read_text(encoding="utf-8")):
            url = url.rstrip(".,;")
            if url in NAMESPACE_URLS or url in ALLOWED_URL_EXACT or url.startswith(ALLOWED_URL_PREFIXES):
                continue
            fail(f"{rel}: URL not allowed: {url}")

    # Private blocklist across every site text file (terms are never printed).
    for f in text_files(site):
        low = f.read_text(encoding="utf-8", errors="replace").lower()
        hits = sum(1 for bad in blocklist if term_in(bad, low))
        if hits:
            fail(f"{f.relative_to(site)}: contains {hits} blocklisted term(s)")

    print("== Private-string scan")
    scanner = os.environ.get("FW_SCAN_PRIVATE")
    if not scanner:
        print("skipped private scan (FW_SCAN_PRIVATE not set)")
    elif not Path(scanner).expanduser().is_file():
        fail("FW_SCAN_PRIVATE script not found")
    else:
        r = subprocess.run(["bash", str(Path(scanner).expanduser()), str(site)], capture_output=True, text=True)
        print((r.stdout + r.stderr).strip())
        if r.returncode != 0:
            fail("private scan found private strings")


def chat_prompt_from_guide():
    """The fenced code block under '## The prompt' in guides/chat.md."""
    guide = ROOT / "guides" / "chat.md"
    if not guide.exists():
        fail("guides/chat.md missing")
        return None
    m = re.search(r"^## The prompt\s*\n```[^\n]*\n(.*?)^```", guide.read_text(encoding="utf-8"), re.S | re.M)
    if not m:
        fail("guides/chat.md: no fenced prompt under '## The prompt'")
        return None
    return m.group(1)


def check_prompt(site):
    """The <template id="chat-prompt"> text must equal the guide's prompt (ignoring a trailing newline)."""
    print("== Chat prompt matches guides/chat.md")
    expected = chat_prompt_from_guide()
    m = re.search(r'<template id="chat-prompt">(.*?)</template>', (site / "index.html").read_text(encoding="utf-8"), re.S)
    if not m:
        fail("index.html: <template id=\"chat-prompt\"> missing")
        return expected
    if expected is not None and html.unescape(m.group(1)).rstrip("\n") != expected.rstrip("\n"):
        fail("index.html: Chat prompt <template> differs from guides/chat.md")
    return expected


def parse_headers(site):
    """Read the /* block of a Cloudflare Pages _headers file."""
    hdrs, active = {}, False
    path = site / "_headers"
    if not path.exists():
        fail("_headers missing")
        return hdrs
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            active = line.strip() == "/*"
            continue
        if active and ":" in line:
            k, v = line.strip().split(":", 1)
            hdrs[k.strip()] = v.strip()
    for need in ("Content-Security-Policy", "X-Content-Type-Options", "Referrer-Policy",
                 "Permissions-Policy", "Strict-Transport-Security"):
        if need not in hdrs:
            fail(f"_headers missing {need}")
    return hdrs


def serve(site, headers):
    class H(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            for k, v in headers.items():
                self.send_header(k, v)
            super().end_headers()

        def log_message(self, *a):
            pass

    H.extensions_map = {**H.extensions_map, ".woff2": "font/woff2", ".svg": "image/svg+xml",
                        ".js": "text/javascript", ".css": "text/css"}
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=str(site)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}/"


PAGES = (("", "site"), ("demo/", "demo"))   # (path, screenshot name); interactive checks run on the main page only


def check_browser(site, shots, expected_prompt):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Python Playwright isn't installed.\n"
              "Install with: pip install playwright && python3 -m playwright install chromium (or run with --no-browser)")
        sys.exit(2)

    print("== Browser checks")
    headers = parse_headers(site)
    if "Content-Security-Policy" not in headers:
        return
    httpd, base = serve(site, headers)
    shots.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for w in WIDTHS:
                for path, name in PAGES:
                    check_page(browser, base, path, name, w, shots, expected_prompt)
            browser.close()
    finally:
        httpd.shutdown()
    print(f"Screenshots: {shots}")


def check_page(browser, base, path, name, w, shots, expected_prompt):
    main_page = path == ""
    ctx = browser.new_context(viewport={"width": w, "height": 800 if w >= 768 else 740},
                              permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    errors, outside = [], []
    page.on("console", lambda m: errors.append(f"console {m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: errors.append(f"request failed: {r.url}"))

    def route(r):
        if r.request.url.startswith(base):
            r.continue_()
        else:
            outside.append(r.request.url)
            r.abort()
    page.route("**/*", route)
    page.add_init_script("""
      window.__csp = [];
      document.addEventListener('securitypolicyviolation',
        e => window.__csp.push(e.violatedDirective + ' ' + (e.blockedURI || 'inline')));
    """)
    page.goto(base + path, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    tag = f"[/{path} {w}px]"

    if main_page:
        # Fonts actually loaded from /fonts
        fonts = page.evaluate("[...document.fonts].filter(f => f.status === 'loaded').map(f => f.family)")
        for fam in ("Inter", "Playfair Display", "Caveat"):
            if not any(fam in f for f in fonts):
                fail(f"{tag} font not loaded: {fam}")

    sw = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    if sw[0] > sw[1]:
        fail(f"{tag} horizontal scroll: scrollWidth {sw[0]} > {sw[1]}")
    # Items inside a horizontal scroll container (overflow-x: auto/scroll) are allowed off-screen.
    wide = page.evaluate("""() => [...document.querySelectorAll('body *')]
        .filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > innerWidth + 1 && getComputedStyle(e).position !== 'fixed'; })
        .filter(e => { for (let a = e.parentElement; a; a = a.parentElement) { if (['auto', 'scroll'].includes(getComputedStyle(a).overflowX)) return false; } return true; })
        .slice(0, 5).map(e => e.tagName + '.' + e.className)""")
    if wide:
        fail(f"{tag} elements overflow the viewport: {wide}")

    # Tap targets (open every <details> so their links are measured too)
    page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    small = page.evaluate("""() => [...document.querySelectorAll('a[href], button, summary')]
        .filter(e => { const cs = getComputedStyle(e); return cs.display !== 'none' && cs.visibility !== 'hidden' && e.getClientRects().length; })
        .map(e => { const r = e.getBoundingClientRect(); return [e.textContent.trim().slice(0, 30), Math.round(r.width), Math.round(r.height)]; })
        .filter(x => x[1] < 44 || x[2] < 44)""")
    for label, bw, bh in small:
        fail(f"{tag} tap target {label!r} is {bw}x{bh}px (< 44)")
    page.evaluate("document.querySelectorAll('details').forEach(d => d.open = false)")

    if main_page:
        check_main_interactions(page, tag, expected_prompt)

    # Screenshot (full page, from the top)
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    page.wait_for_timeout(2000 if main_page else 300)  # let 'Copied' labels reset
    page.screenshot(path=str(shots / f"{name}-{w}.png"), full_page=True)

    for c in page.evaluate("window.__csp"):
        fail(f"{tag} CSP violation: {c}")
    for e in errors:
        fail(f"{tag} {e}")
    for u in outside:
        fail(f"{tag} request outside the site: {u}")
    ctx.close()


def check_main_interactions(page, tag, expected_prompt):
    # Copy the Chat prompt
    btn = page.locator("#copy-prompt")
    btn.scroll_into_view_if_needed()
    btn.click()
    page.wait_for_timeout(200)
    if "Copied" not in btn.inner_text():
        fail(f"{tag} copy-prompt button didn't show 'Copied'")
    clip = page.evaluate("navigator.clipboard.readText()")
    tpl = page.evaluate("document.getElementById('chat-prompt').content.textContent")
    if clip != tpl or "THE ONE RULE" not in clip:
        fail(f"{tag} clipboard didn't receive the Chat prompt ({len(clip)} chars)")
    elif expected_prompt is not None and clip.rstrip("\n") != expected_prompt.rstrip("\n"):
        fail(f"{tag} copied Chat prompt differs from guides/chat.md")

    # Copy link
    page.locator("#copy-link").click()
    page.wait_for_timeout(150)
    if page.evaluate("navigator.clipboard.readText()") != SITE_URL:
        fail(f"{tag} Copy link didn't copy SITE_URL")
    for sel, want in (("#wa-link", "https://wa.me/?text="), ("#sms-link", "sms:?&body="), ("#mail-link", "mailto:?subject=")):
        href = page.get_attribute(sel, "href")
        if not href.startswith(want) or "fridge-worthy.pages.dev" not in href:
            fail(f"{tag} {sel} href wrong: {href[:60]}")

    # Nav highlighting
    for section, link in (("how", "#how"), ("paths", "#paths")):
        page.evaluate(f"document.getElementById('{section}').scrollIntoView({{behavior: 'instant', block: 'start'}})")
        page.wait_for_timeout(250)
        cur = page.evaluate("[...document.querySelectorAll('nav.jump [aria-current]')].map(e => e.getAttribute('href') || e.dataset.navId)")
        if cur != [link]:
            fail(f"{tag} nav highlight after scrolling to #{section}: {cur}")
    page.evaluate("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'})")
    page.wait_for_timeout(250)
    cur = page.evaluate("[...document.querySelectorAll('nav.jump [aria-current]')].map(e => e.getAttribute('href'))")
    if cur != ["#more"]:
        fail(f"{tag} nav highlight at page bottom: {cur}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=str(DEFAULT_SITE))
    ap.add_argument("--shots", default=os.path.join(tempfile.gettempdir(), "fridge-worthy-shots"))
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    site = Path(a.site).resolve()
    check_static(site)
    expected_prompt = check_prompt(site)
    if not a.no_browser:
        check_browser(site, Path(a.shots), expected_prompt)
    if failures:
        print(f"\n{len(failures)} check(s) FAILED")
        sys.exit(1)
    print("\nAll checks passed")


if __name__ == "__main__":
    main()
