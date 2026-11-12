"""Captures screenshots of the *running* StackSense UI with headless Edge/Chrome (no mock-ups).

Starts `stacksense.py serve` on a private port and opens deep links such as `/?scenario=P2&run=1`.
For a region shot it first asks the browser for the rendered DOM (the UI publishes the position of
every `sec-*` section in <html data-boxes>), then captures the full page and crops that region with
Pillow. Output: report/build/img/*.png
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "build", "img")
PORT = 8791
WIDTH = 1280
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/microsoft-edge",
]

# name, query, region: None = top of page (height h) | (first_section_id, last_section_id), max height
SHOTS = [
    ("configure", "scenario=P2", None, 820),
    ("kb", "tab=kb", None, 760),
    ("about", "tab=about", None, 560),
    *[(f"P{i}_overview", f"scenario=P{i}&run=1", ("sec-summary", "sec-kpis"), 900) for i in range(1, 7)],
    ("P2_core", "scenario=P2&run=1", ("sec-core", "sec-core-grid"), 1700),
    ("P2_support", "scenario=P2&run=1", ("sec-support", "sec-support-grid"), 1300),
    ("P2_notes", "scenario=P2&run=1", ("sec-notes", "sec-notes"), 900),
    ("P2_trace", "scenario=P2&run=1", ("sec-trace", "sec-trace"), 900),
    ("P2_cost", "scenario=P2&run=1&open=sec-cost", ("sec-kpis", "sec-kpis"), 900),
    ("P4_core", "scenario=P4&run=1", ("sec-core", "sec-core-grid"), 1700),
    ("P4_support", "scenario=P4&run=1", ("sec-support", "sec-support-grid"), 1500),
    ("P4_notes", "scenario=P4&run=1", ("sec-notes", "sec-notes"), 1100),
    ("P3_whatif", "scenario=P3&run=1&whatif=requirements.realtime:false", None, 560),
    ("E01_missing", "scenario=E01&run=1", None, 520),
    ("E02_invalid", "scenario=E02&run=1", None, 960),
    ("E03_notes", "scenario=E03&run=1", ("sec-notes", "sec-notes"), 1000),
    ("E05_notes", "scenario=E05&run=1", ("sec-notes", "sec-notes"), 700),
    ("E06_overview", "scenario=E06&run=1", ("sec-summary", "sec-kpis"), 900),
    ("E08_core", "scenario=E08&run=1", ("sec-core", "sec-core-grid"), 1100),
    ("E09_infeasible", "scenario=E09&run=1", None, 640),
    ("E10_overview", "scenario=E10&run=1", ("sec-summary", "sec-core-grid"), 1300),
    ("E10_notes", "scenario=E10&run=1", ("sec-notes", "sec-notes"), 800),
    ("E11_notes", "scenario=E11&run=1", ("sec-notes", "sec-notes"), 800),
    ("E12_core", "scenario=E12&run=1", ("sec-core", "sec-core-grid"), 900),
    ("E13_notes", "scenario=E13&run=1", ("sec-notes", "sec-notes"), 900),
    ("P5_notes", "scenario=P5&run=1", ("sec-notes", "sec-notes"), 900),
    ("E20_notes", "scenario=E20&run=1", ("sec-notes", "sec-notes"), 800),
]


def find_browser():
    for b in BROWSERS:
        if os.path.isfile(b):
            return b
    for name in ("msedge", "google-chrome", "chromium", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    raise SystemExit("No Edge/Chrome found for screenshots")


def _browser(browser, profile, *args):
    return subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                           f"--user-data-dir={profile}", "--virtual-time-budget=12000", *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)


def boxes_for(browser, profile, url, height=1000):
    dom = _browser(browser, profile, f"--window-size={WIDTH},{height}", "--dump-dom", url).stdout
    m = re.search(r'data-boxes="([^"]*)"', dom)
    return json.loads(html.unescape(m.group(1))) if m else {}


def trim_bottom(im):
    from PIL import Image, ImageChops
    bg = Image.new("RGB", im.size, im.getpixel((im.width - 2, im.height - 2)))
    box = ImageChops.difference(im.convert("RGB"), bg).getbbox()
    if box and box[3] < im.height - 24:
        im = im.crop((0, 0, im.width, box[3] + 16))
    return im


def capture(only=None):
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    env = dict(os.environ, STACKSENSE_OPEN_BROWSER="0", STACKSENSE_QUIET="1", STACKSENSE_LLM="off")
    srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "stacksense.py"), "serve", "--port", str(PORT)],
                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        browser = find_browser()
        profile = tempfile.mkdtemp(prefix="ss-shots-")
        for name, qs, region, max_h in SHOTS:
            if only and name not in only:
                continue
            path = os.path.join(OUT, name + ".png")
            url = f"http://localhost:{PORT}/?{qs}&theme=light"
            if region is None:
                _browser(browser, profile, f"--window-size={WIDTH},{max_h}", f"--screenshot={path}", url)
                Image.open(path).pipe(trim_bottom).save(path) if hasattr(Image.Image, "pipe") else \
                    trim_bottom(Image.open(path)).save(path)
            else:
                # the UI hides every other result section (?isolate=...), so the capture is the real render
                ids = ",".join(dict.fromkeys(region))
                _browser(browser, profile, f"--window-size={WIDTH},{max_h + 120}", f"--screenshot={path}",
                         f"{url}&isolate={ids}")
                im = trim_bottom(Image.open(path))
                im.crop((0, 0, im.width, min(im.height, max_h + 80))).save(path)
            print("  captured", name)
        shutil.rmtree(profile, ignore_errors=True)
    finally:
        srv.terminate()


if __name__ == "__main__":
    capture(set(sys.argv[1:]) or None)
