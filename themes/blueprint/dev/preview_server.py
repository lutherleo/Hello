"""Preview server for the Blueprint CTFd theme.

Renders the theme's real Jinja templates with mocked CTFd globals and serves a
mocked /api/v1 so the compiled core JS (Alpine, ctfd-js, ECharts) runs. Stdlib
plus Jinja2 only.

    python3 dev/preview_server.py . <path to a CTFd checkout> [port] [--anon|--empty]
"""
import json
import mimetypes
import os
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

THEME = os.path.abspath(sys.argv[1])
CTFD = os.path.abspath(sys.argv[2])
PORT = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 8765
ANON = "--anon" in sys.argv
EMPTY = "--empty" in sys.argv
NOW = int(time.time())


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, name):
        return None


CONFIGS = Obj(
    ctf_name="CSAW CTF '26",
    ctf_theme="blueprint",
    ctf_logo=None,
    ctf_small_icon="/themes/blueprint/static/img/favicon.ico",
    user_mode="teams",
    account_visibility="public",
    score_visibility="public",
    start=NOW + 3 * 86400 + 4 * 3600,
    end=NOW + 5 * 86400,
    theme_settings={"organizer": "OSIRIS Lab", "revision": "26", "contact": "ctf@example.org"},
    theme_header="",
    theme_footer="",
    view_self_submissions=True,
    challenge_ratings="public",
    social_shares=False,
    tos_or_privacy=False,
)

MANIFEST = json.load(open(os.path.join(THEME, "static", "manifest.json")))


class Assets:
    def css(self, key, theme=None):
        return Markup(f'<link rel="stylesheet" href="/themes/blueprint/static/{MANIFEST[key]["file"]}">')

    def js(self, key, theme=None, type="module", defer=False, extra=""):
        a = MANIFEST[key]
        attrs = f'type="{type}" ' if type else ""
        html = ""
        for i in a.get("imports", []):
            html += f'<script {attrs}src="/themes/blueprint/static/{MANIFEST[i]["file"]}"></script>'
        html += f'<script {attrs}src="/themes/blueprint/static/{a["file"]}"></script>'
        return Markup(html)


ROUTES = {
    "views.static_html": "/",
    "challenges.listing": "/challenges",
    "scoreboard.listing": "/scoreboard",
    "users.listing": "/users",
    "teams.listing": "/teams",
    "users.private": "/user",
    "teams.private": "/team",
    "views.notifications": "/notifications",
    "views.settings": "/settings",
    "auth.login": "/login",
    "auth.register": "/register",
    "auth.logout": "/logout",
    "auth.reset_password": "/reset_password",
    "auth.oauth_login": "/oauth",
    "admin.view": "/admin",
}


def url_for(endpoint, **kw):
    if endpoint in ("views.themes", "views.themes_beta"):
        return f"/themes/{kw['theme']}/static/{kw['path']}"
    if endpoint == "views.files":
        return f"/files/{kw['path']}"
    return ROUTES.get(endpoint, "/" + endpoint)


class Field:
    def __init__(self, name, label, type_="text"):
        self.name, self._label, self.type = name, label, type_

    def label(self, **kw):
        return Markup(f'<label for="{self.name}" class="{kw.get("class", "")}">{self._label}</label>')

    def __call__(self, **kw):
        cls = kw.get("class", "")
        if self.type == "submit":
            return Markup(f'<input type="submit" id="{self.name}" class="{cls}" value="{self._label}">')
        if self.type == "hidden":
            return Markup(f'<input type="hidden" name="{self.name}" value="x">')
        return Markup(f'<input type="{self.type}" id="{self.name}" name="{self.name}" class="{cls}">')


class Form:
    def __init__(self, *fields):
        for f in fields:
            setattr(self, f.name, f)
        self.extra = []


FORMS = Obj(
    auth=Obj(
        LoginForm=lambda: Form(Field("name", "User Name or Email"), Field("password", "Password", "password"),
                               Field("submit", "Submit", "submit"), Field("nonce", "", "hidden")),
        RegistrationForm=lambda: Form(Field("name", "User Name"), Field("email", "Email", "email"),
                                      Field("password", "Password", "password"),
                                      Field("submit", "Submit", "submit"), Field("nonce", "", "hidden")),
    )
)

env = Environment(
    loader=FileSystemLoader([os.path.join(THEME, "templates"),
                             os.path.join(CTFD, "CTFd", "plugins", "challenges", "assets")]),
    extensions=["jinja2.ext.i18n"],
    autoescape=True,
)
env.install_null_translations(newstyle=True)
env.filters["pluralize"] = lambda n, s="s": "" if n == 1 else s
env.globals.update(
    Configs=CONFIGS,
    Assets=Assets(),
    Plugins=Obj(styles="", scripts="", user_menu_pages=[]),
    Session=Obj(nonce="nonce", id=0 if ANON else 7),
    User=Obj(name=None if ANON else "kernel_panic", email="kp@example.org", verified=True),
    Team=Obj(id=None if ANON else 3, name=None if ANON else "Segfault Society"),
    authed=lambda: not ANON,
    is_admin=lambda: False,
    registration_visible=lambda: True,
    get_locale=lambda: "en",
    Languages=Obj(names={"en": "English", "de": "Deutsch", "ja": "日本語"}),
    url_for=url_for,
    Forms=FORMS,
    integrations=Obj(mlc=lambda: False),
    get_mode_as_word=lambda plural=False, capitalize=False: "Team" if capitalize else "team",
    meta="",
    can_send_mail=lambda: False,
)

CATS = {
    "pwn": [("Bufferbloat", 100, 412), ("Heap of Trouble", 250, 88), ("ret2sheet", 400, 17), ("Kernel Draft", 500, 2)],
    "rev": [("Tracing Paper", 100, 390), ("Obfuscated Elevation", 300, 61), ("VM in the Margins", 450, 9)],
    "web": [("Title Block Injection", 150, 301), ("CSRF Revision", 250, 122), ("Template Tolerance", 350, 40),
            ("Proxy Plotter", 500, 5)],
    "crypto": [("Lattice Hatching", 200, 77), ("Diffie-Hellman Dimensions", 300, 31), ("Isometric Keys", 500, 0)],
    "forensics": [("Cyanotype", 100, 455), ("Deleted Layers", 300, 52)],
}
CHALLENGES = []
SOLVED = {1, 2, 5, 8, 9, 15}
cid = 0
for cat, items in CATS.items():
    for name, value, solves in items:
        cid += 1
        CHALLENGES.append({
            "id": cid, "type": "standard", "name": name, "value": value, "solves": solves,
            "solved_by_me": (cid in SOLVED) and not ANON, "category": cat, "tags": [],
            "template": "/plugins/challenges/assets/view.html", "script": "/plugins/challenges/assets/view.js",
        })
CHALLENGES.append({"id": 99, "type": "hidden", "name": "???", "value": 0, "solves": None, "solved_by_me": False,
                   "category": "web", "tags": [], "template": "", "script": ""})
if EMPTY:
    CHALLENGES = []

TEAMS = ["Segfault Society", "Null Pointer Club", "0xDEADBEEF", "Shell Shocked", "Rubber Duckies",
         "Off By One", "Heap Heroes", "Kernel Sanders", "Bit Flippers", "Tandon Tinkerers", "Packet Rats",
         "Root Cause"]


def scoreboard():
    return [{"pos": i + 1, "account_id": i + 1, "account_url": f"/teams/{i + 1}", "account_type": "team",
             "oauth_id": None, "name": n, "score": 4200 - i * 290 - (i * i * 7), "bracket_id": None,
             "bracket_name": "Student" if i % 3 == 0 else None,
             "members": [{"id": i * 10 + m, "name": f"member{m}", "score": 0} for m in range(1 + (i % 4))]}
            for i, n in enumerate(TEAMS)]


def top10():
    out = {}
    start = NOW - 30 * 3600
    for i, n in enumerate(TEAMS[:10]):
        solves = []
        t = start
        total = 4200 - i * 290 - (i * i * 7)
        acc = 0
        k = 0
        while acc < total:
            v = [100, 250, 150, 300, 500, 200][(k + i) % 6]
            v = min(v, total - acc)
            acc += v
            t += 3600 * (1 + ((k * 7 + i * 3) % 5)) // 2
            solves.append({"challenge_id": k, "account_id": i + 1, "team_id": i + 1, "user_id": 1,
                           "value": v, "date": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(t))})
            k += 1
        out[str(i + 1)] = {"id": i + 1, "account_url": f"/teams/{i + 1}", "name": n, "score": total,
                           "bracket_id": None, "bracket_name": None, "solves": solves}
    return out


def challenge_view(c):
    tpl = env.get_template("view.html")
    return tpl.render(
        challenge=Obj(id=c["id"], name=c["name"], value=c["value"], category=c["category"],
                      html=Markup("<p>The checker left a note in the margin of this drawing. "
                                  "Connect to the service, follow the dimension lines, and bring back the flag.</p>"
                                  "<p>Flag format: <code>csawctf{...}</code></p>"),
                      connection_info="nc pwn.chal.example.org 31337", byline="Author: drafting_dept"),
        max_attempts=0, attempts=0, rating=None, ratings={"up": 12, "down": 1, "count": 13},
        solves=c["solves"], tags=["beginner"] if c["value"] <= 150 else [],
        hints=[Obj(id=1, content=None, title="Where to start", cost=50, html="")],
        files=["/files/abc123/schematic.tar.gz?token=x"], request=Obj(endpoint="challenges.listing"),
    )


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def render(self, template, endpoint, code=200, **ctx):
        req = Obj(endpoint=endpoint, script_root="", full_path=self.path, path=urlparse(self.path).path)
        html = env.get_template(template).render(request=req, **ctx)
        self.send_bytes(html.encode(), "text/html; charset=utf-8", code)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/v1/challenges/attempt":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            ok = data.get("submission", "").startswith("csawctf{")
            return self.send_json({"success": True, "data": {
                "status": "correct" if ok else "incorrect",
                "message": "Correct" if ok else "Incorrect"}})
        self.send_json({"success": True, "data": {}})

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        if path.startswith("/themes/"):
            parts = path.split("/", 4)
            fp = os.path.join(THEME, "static", parts[4])
            if os.path.isfile(fp):
                ctype = mimetypes.guess_type(fp)[0] or "application/octet-stream"
                return self.send_bytes(open(fp, "rb").read(), ctype)
            return self.send_bytes(b"", "text/plain", 404)
        if path.startswith("/plugins/challenges/assets/"):
            fp = os.path.join(CTFD, "CTFd", path.lstrip("/"))
            return self.send_bytes(open(fp, "rb").read(), "application/javascript")
        if path == "/api/v1/challenges":
            return self.send_json({"success": True, "data": CHALLENGES})
        if path.startswith("/api/v1/challenges/") and path.endswith("/solves"):
            return self.send_json({"success": True, "data": [
                {"account_id": 1, "name": t, "date": "2026-10-27T10:00:00+00:00", "account_url": "/teams/1"}
                for t in TEAMS[:5]]})
        if path.startswith("/api/v1/challenges/"):
            c = next(c for c in CHALLENGES if str(c["id"]) == path.rsplit("/", 1)[1])
            d = dict(c, description="", connection_info="", attribution="", next_id=None, solution_id=None,
                     view=challenge_view(c),
                     type_data={"id": "standard", "name": "standard",
                                "scripts": {"view": "/plugins/challenges/assets/view.js"}})
            return self.send_json({"success": True, "data": d})
        if path == "/api/v1/scoreboard":
            return self.send_json({"success": True, "data": [] if EMPTY else scoreboard()})
        if path.startswith("/api/v1/scoreboard/top/"):
            return self.send_json({"success": True, "data": {} if EMPTY else top10()})
        if path == "/api/v1/teams/me":
            return self.send_json({"success": True, "data": {"id": 3, "name": "Segfault Society",
                                                              "members": [7, 8, 9, 10]}})
        if path.startswith("/api/v1/brackets"):
            return self.send_json({"success": True, "data": [{"id": 1, "name": "Student"}, {"id": 2, "name": "Open"}]})
        if path.startswith("/api/v1/"):
            return self.send_json({"success": True, "data": [], "meta": {"pagination": {}}})
        if path == "/":
            content = Markup(open(os.path.join(THEME, "pages", "index.html")).read())
            return self.render("page.html", "views.static_html", content=content)
        if path == "/challenges":
            return self.render("challenges.html", "challenges.listing", errors=[], infos=[])
        if path == "/scoreboard":
            return self.render("scoreboard.html", "scoreboard.listing", errors=[], infos=[])
        if path == "/login":
            return self.render("login.html", "auth.login", errors=[], infos=[])
        if path == "/register":
            return self.render("register.html", "auth.register", errors=[], infos=[])
        if path == "/notifications":
            return self.render("notifications.html", "views.notifications", errors=[], infos=[])
        return self.render("errors/404.html", "x", code=404)


HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
