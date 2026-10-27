# Blueprint — a CTFd theme

A CTFd 3.8 theme that draws the CTF as a heist crew's planning sheets for a
crypto exchange: the floor plan, the crew, the plan, and a cold-storage vault
of **Hashbar (Ħ)**, a made-up in-game coin. The tone takes its cue from heist
films; no film names, characters or quotes are used.

Hashbar is plainly play money. The theme names no real cryptocurrency, shows
no prices, and has no wallet-connect or payment anything. The sample cover
page says Hashbar exists only on the scoreboard and that organizers never ask
for wallet addresses, seed phrases, private keys or payments. Points are only
relabelled; CTFd's scoring is unchanged.

- **Two prints.** Dark mode is a cyanotype blueprint (white line on Prussian
  blue); light mode is a whiteprint (blue line on warm paper). Blueprint is the
  default; the switch is in the navbar and in the footer's title block.
- **One accent: the redline,** the checker's red pencil. It marks what you act
  on (primary buttons, submit) and what you captured (the stamp on solved
  challenges, the podium deltas on the scoreboard).
- **The cover is the job briefing** (`pages/index.html`): a floor plan of the
  exchange (SOC, trading floor, server hall, hot wallet, cold storage) with
  the crew's route, guards and camera cones marked in red marker, a
  countdown to the job, the four-step plan beside a vault-door detail
  drawing, the crew of specialists, and the rules of the job.
- **The challenge board is "The Job".** Each category is a lettered section
  with a crew role scrawled beside it (pwn is The Demolitions, rev The
  Safecracker, and so on); each challenge is a numbered target (`A-01`) and
  solved ones get a red CRACKED stamp. Challenge values show as Hashbar.
  The header shows your crew's haul as a dimension line and, in teams mode,
  **your cut**: the haul divided by the number of crew members (read from
  `/api/v1/teams/me`). Also an index of specialties and "Hide cracked".
- **The scoreboard is "The Ledger".** Crew balances in Hashbar, the cut per
  member (balance divided by members, teams mode), and a made-up wallet ID
  per crew (a hash of the account, `hb_…`; not an address on any chain). Top
  three get revision-delta triangles. The top-10 graph is drawn as SVG step lines in the print's colors
  (it replaces core's ECharts canvas); hovering a legend entry or a table row
  highlights that team's line, clicking a legend entry pins it.
- **Every page ends in a title block** (the job, sheet, planned by,
  revision, clearance, print, contact). Login is "Check in", registration
  is "Join the crew", error pages are a "Change of plan".

### Quality of life

- **Your haul is your real score:** the board's haul and cut come from
  CTFd's own score (awards and hint costs included) and the cut divides by
  the members the scoreboard counts, so both match the ledger.
- **Search the board:** filter targets by name, specialty or tag. Press `/`
  to jump to the search box, Esc to clear it.
- **Hide cracked** is remembered per browser.
- **Copy button** beside a challenge's connection info.
- **Live job clock** in the navbar on wide screens (starts in / ends in).
- **The Ledger:** your crew's row is marked, "Find my crew" scrolls to it,
  and "Find a crew…" filters the table. On phones the ledger drops the cut
  and wallet columns so it fits without sideways scrolling.
- **New players** land on "Assemble your crew" with two clear choices (start
  or join a crew); the create, join and invite forms share the login panel.
- **Hidden scores:** when score visibility hides the scoreboard, the ledger
  says it is sealed instead of breaking or claiming it is empty.
- **Solo mode:** with CTFd in users mode, the wording drops "crew" and the
  split is hidden.
- **Profile and team pages** use the theme's colors for core's graphs and
  show scores in Hashbar.
- **Accessibility:** a skip-to-content link, text contrast of at least 4.5:1
  in both prints, labelled icon links, and reduced motion respected.

## Install

1. Copy this folder into your CTFd install as `CTFd/themes/blueprint`.
2. Admin Panel → Config → Theme → choose **blueprint**.
3. Optional: Admin Panel → Pages → `index` → paste
   [`pages/index.html`](pages/index.html) (format: HTML) for the cover sheet.
   Fill in the `[bracketed]` placeholders. Its countdown reads the CTF's
   configured start/end times, so it needs no edits.

No build step. The theme reuses core's compiled JS/CSS (in `static/assets`,
copied from CTFd 3.8.9's `core` theme) and layers
`static/css/blueprint.css` and `static/js/blueprint.js` on top. The SCSS/JS
sources under `assets/` are core's, kept so the bundle can be rebuilt with
`yarn build` if you ever need to change core behavior.

Fonts (Barlow Condensed, Barlow, IBM Plex Mono, and Permanent Marker for the
red-marker notes) load from Google Fonts.

## Theme settings

Admin Panel → Config → Theme → Theme Settings (JSON). Core's keys
(`challenge_window_size`, `challenge_category_order`, `challenge_order`) still
work. Blueprint adds:

```json
{
  "organizer": "OSIRIS Lab",
  "revision": "26",
  "contact": "ctf@example.org",
  "category_roles": { "osint": "The Lookout", "hardware": "The Wheelman" },
  "currency": { "name": "Hashbar", "symbol": "Ħ" }
}
```

`currency` renames the in-game coin everywhere the theme shows it (board,
challenge window, ledger, footer). The sample cover page is static HTML, so
rename it there by hand too.

`organizer`, `revision` and `contact` fill the footer title block; without
them it shows `OSIRIS Lab`, `26` and `—`. `category_roles` names the crew
role shown beside a category on the challenge board (matched without regard
to case). Built in: pwn / binary exploitation → The Demolitions, rev /
reversing → The Safecracker, web → The Inside Man, crypto → The Codebreaker,
forensics / incident response → The Cleaner, misc → The Grifter, osint /
recon → The Lookout, hardware → The Wheelman, intro → The Rookie. Categories
with no role show none.

## What changed from core

| File | Change |
| --- | --- |
| `templates/base.html` | Fonts, `blueprint.css`/`blueprint.js` (replaces core's color mode switcher), sheet frame, title-block footer |
| `templates/components/navbar.html` | Drafting-style nav, active-page marker, print switch |
| `templates/challenges.html` | "The Job" board: sections with crew roles, numbered targets in Hashbar, haul gauge, your cut, hide-cracked |
| `templates/scoreboard.html` | "The Ledger": SVG top-10 graph with linked highlighting, balances, cut per member, wallet IDs |
| `templates/macros/coin.html` | The coin's name and symbol, from `theme_settings.currency` |
| `templates/login.html`, `register.html`, `reset_password.html` | Forms set in a "crew credentials" panel |
| `templates/errors/*`, `components/error_sheet.html` | Error pages as a "change of plan" |
| everything else | Core's markup, restyled by `blueprint.css` |

The challenge modal (`challenge.html`) keeps core's markup so challenge-type
plugins that extend it keep working; it is restyled by CSS only.

## Previewing without CTFd

`dev/preview_server.py` renders these templates with Jinja2 and a mocked
`/api/v1`, so core's JS runs against fake challenges and teams:

```bash
cd themes/blueprint
python3 dev/preview_server.py . /path/to/CTFd 8765              # logged in
python3 dev/preview_server.py . /path/to/CTFd 8766 --anon       # logged out
python3 dev/preview_server.py . /path/to/CTFd 8767 --empty      # no challenges
python3 dev/preview_server.py . /path/to/CTFd 8768 --ended      # CTF over
python3 dev/preview_server.py . /path/to/CTFd 8769 --api-error  # challenges API 403
python3 dev/preview_server.py . /path/to/CTFd 8770 --users      # solo mode
python3 dev/preview_server.py . /path/to/CTFd 8771 --stress     # long names, 120 teams
python3 dev/preview_server.py . /path/to/CTFd 8772 --hidden-scores  # scoreboard hidden
node dev/screenshots.js /tmp/shots     # every page, both prints, desktop + phone
node dev/interactions.js /tmp/shots    # search, copy, ledger, skip link checks
node dev/regressions.js                # bugs found in review stay fixed
```

Both scripts need Playwright with Chromium.

It needs a CTFd checkout only for the standard challenge plugin's
`view.html`/`view.js`. It is a preview, not a test of CTFd itself: before the
event, check the theme on a real CTFd instance.
