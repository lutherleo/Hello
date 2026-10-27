"""Preview server for the Blueprint CTFd theme.

Renders the theme's real Jinja templates with mocked CTFd globals and serves a
mocked /api/v1 so the compiled core JS (Alpine, ctfd-js, ECharts) runs. Stdlib
plus Jinja2 only.

    python3 dev/preview_server.py . <path to a CTFd checkout> [port]
        [--anon] [--empty] [--ended] [--api-error] [--users] [--stress] [--hidden-scores]
"""
import json
import re
import mimetypes
import os
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from jinja2 import ChainableUndefined, Environment, FileSystemLoader
from markupsafe import Markup

THEME = os.path.abspath(sys.argv[1])
CTFD = os.path.abspath(sys.argv[2])
PORT = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 8765
ANON = "--anon" in sys.argv
EMPTY = "--empty" in sys.argv
ENDED = "--ended" in sys.argv        # the CTF finished an hour ago
API_ERROR = "--api-error" in sys.argv  # /api/v1/challenges answers 403
SOLO = "--users" in sys.argv         # user mode: no teams
STRESS = "--stress" in sys.argv      # long names, many categories and teams
HIDDEN = "--hidden-scores" in sys.argv  # score visibility set so the scoreboard API answers 403
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

if ENDED:
    CONFIGS.start, CONFIGS.end = NOW - 3 * 86400, NOW - 3600
if SOLO:
    CONFIGS.user_mode = "users"

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
    "teams.join": "/teams/join",
    "teams.new": "/teams/new",
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
    def __init__(self, name, label=None, type_="text"):
        self.name, self._label, self.type = name, label or name.replace("_", " ").title(), type_
        self.description = ""
        self.choices = [("", "--")]
        self.data = None
        if name in ("submit",):
            self.type = "submit"
        elif name in ("nonce",):
            self.type = "hidden"
        elif "password" in name or name == "confirm":
            self.type = "password"

    def label(self, **kw):
        return Markup(f'<label for="{self.name}" class="{kw.get("class", "")}">{self._label}</label>')

    def __call__(self, **kw):
        cls = kw.get("class", "")
        if self.type == "submit":
            return Markup(f'<input type="submit" id="{self.name}" class="{cls}" value="{self._label}">')
        if self.type == "hidden":
            return Markup(f'<input type="hidden" name="{self.name}" value="x">')
        if "select" in cls or self.name in ("field", "country", "language", "captain_id", "expiration"):
            opts = "".join(f"<option>{c[1] if isinstance(c, tuple) else c}</option>" for c in self.choices)
            return Markup(f'<select id="{self.name}" name="{self.name}" class="{cls}">{opts}</select>')
        if self.name == "description":
            return Markup(f'<textarea id="{self.name}" name="{self.name}" class="{cls}"></textarea>')
        return Markup(f'<input type="{self.type}" id="{self.name}" name="{self.name}" class="{cls}">')


class Form:
    def __init__(self, *fields, **kw):
        for f in fields:
            setattr(self, f.name, f)
        self.extra = []

    def __getattr__(self, name):
        # Any field a template asks for exists.
        if name.startswith("__"):
            raise AttributeError(name)
        f = Field(name)
        setattr(self, name, f)
        return f


class AnyForms:
    """Forms.<group>.<FormName>(**kw) returns a permissive Form."""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **kw: Form()


FORMS = Obj(
    teams=AnyForms(),
    users=AnyForms(),
    auth=Obj(
        LoginForm=lambda: Form(Field("name", "User Name or Email"), Field("password", "Password", "password"),
                               Field("submit", "Submit", "submit"), Field("nonce", "", "hidden")),
        RegistrationForm=lambda: Form(Field("name", "User Name"), Field("email", "Email", "email"),
                                      Field("password", "Password", "password"),
                                      Field("submit", "Submit", "submit"), Field("nonce", "", "hidden")),
    )
)

setattr(FORMS, "self", AnyForms())  # "self" cannot be a keyword to Obj()

env = Environment(
    loader=FileSystemLoader([os.path.join(THEME, "templates"),
                             os.path.join(CTFD, "CTFd", "plugins", "challenges", "assets")]),
    extensions=["jinja2.ext.i18n"],
    autoescape=True,
    undefined=ChainableUndefined,
)
env.install_null_translations(newstyle=True)
env.filters["pluralize"] = lambda n, s="s": "" if n == 1 else s
env.filters["isoformat"] = lambda d: d if isinstance(d, str) else ""
env.globals.update(
    Configs=CONFIGS,
    Assets=Assets(),
    Plugins=Obj(styles="", scripts="", user_menu_pages=[]),
    Session=Obj(nonce="nonce", id=0 if ANON else 7),
    User=Obj(name=None if ANON else "kernel_panic", email="kp@example.org", verified=True),
    Team=Obj(id=None if (ANON or SOLO) else 3, name=None if (ANON or SOLO) else "Segfault Society"),
    authed=lambda: not ANON,
    is_admin=lambda: False,
    registration_visible=lambda: True,
    get_locale=lambda: "en",
    Languages=Obj(names={"en": "English", "de": "Deutsch", "ja": "日本語"}),
    url_for=url_for,
    Forms=FORMS,
    integrations=Obj(mlc=lambda: False),
    get_mode_as_word=lambda plural=False, capitalize=False: ("User" if SOLO else "Team") if capitalize else ("user" if SOLO else "team"),
    meta="",
    can_send_mail=lambda: False,
    scores_visible=lambda: True,
    accounts_visible=lambda: True,
    lookup_country_code=lambda c: {"US": "United States", "DE": "Germany", "IN": "India", "BR": "Brazil"}.get(c, c),
)

CATS = {
    "pwn": [("Bufferbloat", 100, 412), ("Heap of Trouble", 250, 88), ("ret2sheet", 400, 17), ("Kernel Draft", 500, 2)],
    "rev": [("Tracing Paper", 100, 390), ("Obfuscated Elevation", 300, 61), ("VM in the Margins", 450, 9)],
    "web": [("Title Block Injection", 150, 301), ("CSRF Revision", 250, 122), ("Template Tolerance", 350, 40),
            ("Proxy Plotter", 500, 5)],
    "crypto": [("Lattice Hatching", 200, 77), ("Diffie-Hellman Dimensions", 300, 31), ("Isometric Keys", 500, 0)],
    "forensics": [("Cyanotype", 100, 455), ("Deleted Layers", 300, 52)],
}
if STRESS:
    CATS = {
        "pwn": [("A Remarkably Long Challenge Name That Wraps Across Several Lines Of The Card", 500, 3)],
        "Reverse Engineering And Binary Analysis": [("x", 50, 999), ("unbrokenstringwithoutanyspacesatallforwrapping", 300, 12)],
        "web": [("Web %d" % i, 100 + i * 25, 40 - i) for i in range(14)],
        "crypto": [("Crypto %d" % i, 200, 5) for i in range(3)],
        "forensics": [("Forensics", 100, 1)], "misc": [("Misc", 50, 300)], "osint": [("OSINT", 100, 80)],
        "hardware": [("Hardware", 400, 2)], "intro": [("Intro", 10, 1200)], "blockchain": [("Chain", 300, 9)],
        "incident response": [("IR", 200, 20)], "mobile": [("APK", 250, 33)],
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
if STRESS:
    TEAMS = ["Team %03d" % i for i in range(120)]
    TEAMS[4] = "AnExtremelyLongTeamNameWithNoSpacesThatShouldWrapInsteadOfOverflowingTheLedger"
    TEAMS[7] = "A team name with plenty of words that goes on and on well past the width of a phone"


class Page:
    def __init__(self, items, page=1, pages=3):
        self.items, self.page, self.pages, self.total = items, page, pages, len(items) * pages
        self.next_num = page + 1 if page < pages else None


AFFIL = ["NYU Tandon", "", "Universidade de Sao Paulo", "IIT Bombay", "TU Munich", ""]
COUNTRY = ["US", None, "BR", "IN", "DE", "US"]


def team_obj(i, name):
    return Obj(id=i + 1, name=name, website="https://example.org" if i % 2 == 0 else "",
               affiliation=AFFIL[i % 6], country=COUNTRY[i % 6], bracket_id=1 if i % 3 == 0 else None,
               bracket=Obj(name="Student"), oauth_id=None, captain_id=7, fields=[],
               members=[Obj(id=7 + m, name=n, score=s, bracket_id=None)
                        for m, (n, s) in enumerate([("kernel_panic", 1450), ("nullbyte", 1100),
                                                     ("ropchain", 800), ("hex_maniac", 242)])])


def solves_list():
    out = []
    for c in CHALLENGES[:6]:
        out.append(Obj(challenge=Obj(id=c["id"], name=c["name"], category=c["category"], value=c["value"]),
                       date="2026-10-26T1%d:20:00+00:00" % (len(out)), user=Obj(name="kernel_panic", id=7)))
    return out


AWARDS = [Obj(name="First blood", value=50, category="Bonus", description="First crew to crack Kernel Draft",
              icon="trophy", date="2026-10-26T12:00:00+00:00")]
NOTIFICATIONS = [
    Obj(id=2, title="Kernel Draft patched", date="2026-10-26T14:05:00+00:00",
        html=Markup("<p>The service was restarted with a fix. Flags submitted before 14:00 still count.</p>")),
    Obj(id=1, title="Doors are open", date="2026-10-25T23:40:00+00:00",
        html=Markup("<p>Good luck, crews. Questions go to the help desk channel.</p>")),
]


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

    def do_HEAD(self):
        # ctfd-js polls notification counts with HEAD.
        self.send_response(200)
        self.send_header("Result-Count", "0")
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/v1/challenges/attempt":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            ok = data.get("submission", "").startswith("csawctf{")
            if ok:
                for c in CHALLENGES:
                    if c["id"] == data.get("challenge_id"):
                        c["solved_by_me"] = True
                        c["solves"] = (c["solves"] or 0) + 1
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
        if path == "/api/v1/challenges" and API_ERROR:
            return self.send_json({"success": False, "errors": {"": ["CSAW CTF '26 has not started yet"]}}, 403)
        if path == "/api/v1/challenges":
            return self.send_json({"success": True, "data": CHALLENGES})
        if path.startswith("/api/v1/challenges/") and path.endswith("/solves"):
            return self.send_json({"success": True, "data": [
                {"account_id": 1, "name": t, "date": "2026-10-27T10:00:00+00:00", "account_url": "/teams/1"}
                for t in TEAMS[:5]]})
        if path.startswith("/api/v1/challenges/") and path.endswith("/solution"):
            # Same shape as CTFd for a challenge without a solution.
            return self.send_json({"success": True, "data": {"id": None, "state": "hidden"}})
        if path.startswith("/api/v1/challenges/"):
            c = next((c for c in CHALLENGES if str(c["id"]) == path.rsplit("/", 1)[1]), None)
            if c is None:
                return self.send_json({"success": False}, 404)
            d = dict(c, description="", connection_info="", attribution="", next_id=None, solution_id=None, solution_state="hidden",
                     view=challenge_view(c),
                     type_data={"id": "standard", "name": "standard",
                                "scripts": {"view": "/plugins/challenges/assets/view.js"}})
            return self.send_json({"success": True, "data": d})
        if path.startswith("/api/v1/scoreboard") and HIDDEN:
            return self.send_json({"success": False, "errors": {"": ["Scores are currently hidden"]}}, 403)
        if path == "/api/v1/scoreboard":
            return self.send_json({"success": True, "data": [] if EMPTY else scoreboard()})
        if path.startswith("/api/v1/scoreboard/top/"):
            return self.send_json({"success": True, "data": {} if EMPTY else top10()})
        m = re.match(r"^/api/v1/(teams|users)/[^/]+/(solves|fails|awards)$", path)
        if m:
            kind = m.group(2)
            if kind == "solves":
                data = [{"challenge_id": x.challenge.id, "date": x.date,
                         "challenge": {"id": x.challenge.id, "name": x.challenge.name,
                                       "category": x.challenge.category, "value": x.challenge.value},
                         "user": {"id": 7, "name": "kernel_panic"}} for x in solves_list()]
            elif kind == "fails":
                data = [{"challenge_id": 3, "date": "2026-10-26T10:05:00+00:00"}] * 4
            else:
                data = [{"name": "First blood", "value": 50, "date": "2026-10-26T12:00:00+00:00", "category": "Bonus"}]
            return self.send_json({"success": True, "data": data, "meta": {"count": len(data)}})
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
            infos = ["CSAW CTF '26 has ended"] if ENDED else []
            errors = ["CSAW CTF '26 has not started yet"] if API_ERROR else []
            return self.render("challenges.html", "challenges.listing", errors=errors, infos=infos)
        if path == "/scoreboard":
            errors = ["Scores are currently hidden"] if HIDDEN else []
            return self.render("scoreboard.html", "scoreboard.listing", errors=errors, infos=[])
        if path == "/login":
            return self.render("login.html", "auth.login", errors=[], infos=[])
        if path == "/register":
            return self.render("register.html", "auth.register", errors=[], infos=[])
        if path == "/teams":
            return self.render("teams/teams.html", "teams.listing", teams=Page([team_obj(i, n) for i, n in enumerate(TEAMS)]),
                               q=None, field=None, prev_page="#", next_page="#")
        if path == "/users":
            users = [team_obj(i, n) for i, n in enumerate(["kernel_panic", "nullbyte", "ropchain", "hex_maniac",
                                                           "a_very_long_username_that_keeps_going_and_going_forever"])]
            return self.render("users/users.html", "users.listing", users=Page(users), q=None, field=None,
                               prev_page="#", next_page="#")
        if path == "/team":
            team = team_obj(2, "0xDEADBEEF")
            return self.render("teams/private.html", "teams.private", team=team, solves=solves_list(), awards=AWARDS,
                               place="3rd", score=3592, errors=[], user=Obj(id=7))
        if path == "/user":
            u = team_obj(0, "kernel_panic")
            u.team = Obj(name="0xDEADBEEF"); u.team_id = 3; u.solves = solves_list(); u.awards = AWARDS
            acct = Obj(place="3rd", get_score=lambda admin=False: 1450)
            return self.render("users/private.html", "users.private", user=u, account=acct, errors=[])
        if path == "/settings":
            return self.render("settings.html", "views.settings", name="kernel_panic", email="kp@example.org",
                               website="", affiliation="NYU Tandon", country="US", language="en", tokens=[
                                   Obj(id=1, created="2026-10-20T10:00:00+00:00", expiration="2026-11-20T10:00:00+00:00",
                                       description="scripts")], errors=[])
        if path == "/team/enroll":  # what /team shows a player with no crew yet
            return self.render("teams/team_enrollment.html", "teams.private", errors=[], infos=[])
        if path == "/teams/join":
            return self.render("teams/join_team.html", "teams.join", errors=[], infos=[])
        if path == "/teams/new":
            return self.render("teams/new_team.html", "teams.new", errors=[], infos=[])
        if path == "/teams/invite":
            return self.render("teams/invite.html", "teams.invite", team=team_obj(2, "0xDEADBEEF"), errors=[], infos=[])
        if path == "/notifications":
            return self.render("notifications.html", "views.notifications", notifications=NOTIFICATIONS,
                               errors=[], infos=[])
        return self.render("errors/404.html", "x", code=404)


HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
