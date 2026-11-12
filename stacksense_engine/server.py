"""Zero-dependency HTTP server: JSON API + static web UI (Python standard library only)."""
import json
import os
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from . import kb, llm
from .describe import parse_description
from .recommend import recommend
from .schema import public_schema
from .validate import validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
SCENARIOS = os.path.join(ROOT, "scenarios")
MAX_BODY = 1_000_000
MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml",
        ".png": "image/png", ".ico": "image/x-icon"}


def _scenarios():
    out = []
    for group in ("public", "edge"):
        d = os.path.join(SCENARIOS, group)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".json") or name == "stacksense_public_scenarios.json":
                continue
            try:
                with open(os.path.join(d, name), encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            proj = data.get("project", {}) if isinstance(data, dict) else {}
            out.append({"id": data.get("scenario_id", name[:-5]) if isinstance(data, dict) else name[:-5],
                        "group": group, "file": name,
                        "name": proj.get("name") if isinstance(proj, dict) else None, "data": data})
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "StackSense/1.0"

    def log_message(self, fmt, *args):  # quieter console
        if os.environ.get("STACKSENSE_QUIET") != "1":
            sys.stderr.write("  %s %s\n" % (self.command, self.path))

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("request body too large (max 1 MB)")
        raw = self.rfile.read(n) if n else b""
        try:
            return json.loads(raw.decode("utf-8") or "null")
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"body is not valid JSON: {e}")

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        if path == "/api/health":
            return self._send(200, {"ok": True, "llm": llm.status()})
        if path == "/api/schema":
            return self._send(200, public_schema())
        if path == "/api/scenarios":
            return self._send(200, _scenarios())
        if path == "/api/kb":
            return self._send(200, kb.export())
        if path == "/" or path == "":
            path = "/index.html"
        fp = os.path.normpath(os.path.join(WEB, path.lstrip("/")))
        if not fp.startswith(WEB) or not os.path.isfile(fp):
            return self._send(404, {"error": "not found"})
        with open(fp, "rb") as f:
            data = f.read()
        return self._send(200, data, MIME.get(os.path.splitext(fp)[1], "application/octet-stream"))

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            body = self._body()
        except ValueError as e:
            return self._send(400, {"error": str(e)})
        if u.path == "/api/recommend":
            lenient = q.get("lenient", ["0"])[0] == "1"
            return self._send(200, recommend(body, lenient=lenient))
        if u.path == "/api/validate":
            v = validate(body, lenient=q.get("lenient", ["0"])[0] == "1")
            return self._send(200, {"valid": not v["errors"], "validation_errors": v["errors"],
                                    "assumptions": v["assumptions"], "unknown_fields": v["unknown_fields"]})
        if u.path == "/api/describe":
            text = (body or {}).get("text", "") if isinstance(body, dict) else ""
            res = parse_description(text)
            res["source"] = "deterministic"
            if isinstance(body, dict) and body.get("use_llm") and llm.enabled():
                res["llm"] = llm.suggest_fields(text)
            return self._send(200, res)
        return self._send(404, {"error": "not found"})


def serve(host="127.0.0.1", port=8000, open_browser=None):
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}/"
    print(f"StackSense UI running at {url}  (Ctrl+C to stop)")
    print(f"LLM features: {llm.status()['message']}")
    if open_browser is None:
        open_browser = os.environ.get("STACKSENSE_OPEN_BROWSER", "1") == "1" and host != "0.0.0.0"
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
