# Blueprint — a CTFd theme

A CTFd 3.8 theme that draws the whole CTF as an engineering sheet.

- **Two prints.** Dark mode is a cyanotype blueprint (white line on Prussian
  blue); light mode is a whiteprint (blue line on warm paper). Blueprint is the
  default; the switch is in the navbar and in the footer's title block.
- **One accent: the redline,** the checker's red pencil. It marks what you act
  on (primary buttons, submit) and what you captured (the stamp on solved
  challenges, the podium deltas on the scoreboard).
- **Challenges are parts on a drawing.** Each category is a lettered section
  (A, B, C…), each challenge a numbered part (`A-01`), solved parts get a red
  CAPTURED stamp. The board header shows points captured as a dimension line,
  an index of sections with per-section progress, and a "Hide captured" toggle.
- **The scoreboard is a revision table.** Top three get revision-delta
  triangles. The top-10 graph is drawn as SVG step lines in the print's colors
  (it replaces core's ECharts canvas); hovering a legend entry or a table row
  highlights that team's line, clicking a legend entry pins it.
- **Every page ends in a title block** (project, sheet number, drawn by,
  revision, print, contact).

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

Fonts (Barlow Condensed, Barlow, IBM Plex Mono) load from Google Fonts.

## Theme settings

Admin Panel → Config → Theme → Theme Settings (JSON). Core's keys
(`challenge_window_size`, `challenge_category_order`, `challenge_order`) still
work. Blueprint adds:

```json
{
  "organizer": "OSIRIS Lab",
  "revision": "26",
  "contact": "ctf@example.org"
}
```

These fill the footer title block. Without them it shows `OSIRIS Lab`, `26`
and `—`.

## What changed from core

| File | Change |
| --- | --- |
| `templates/base.html` | Fonts, `blueprint.css`/`blueprint.js` (replaces core's color mode switcher), sheet frame, title-block footer |
| `templates/components/navbar.html` | Drafting-style nav, active-page marker, print switch |
| `templates/challenges.html` | Sections and parts board, progress gauge, section index, hide-captured |
| `templates/scoreboard.html` | SVG top-10 graph with linked highlighting, revision-table standings |
| `templates/login.html`, `register.html`, `reset_password.html` | Forms set in an "access permit" panel |
| `templates/errors/*`, `components/error_sheet.html` | Error pages as checker's notes |
| everything else | Core's markup, restyled by `blueprint.css` |

The challenge modal (`challenge.html`) keeps core's markup so challenge-type
plugins that extend it keep working; it is restyled by CSS only.

## Previewing without CTFd

`dev/preview_server.py` renders these templates with Jinja2 and a mocked
`/api/v1`, so core's JS runs against fake challenges and teams:

```bash
cd themes/blueprint
python3 dev/preview_server.py . /path/to/CTFd 8765            # logged in
python3 dev/preview_server.py . /path/to/CTFd 8766 --anon     # logged out
python3 dev/preview_server.py . /path/to/CTFd 8767 --empty    # no challenges
node dev/screenshots.js /tmp/shots                             # needs Playwright
```

It needs a CTFd checkout only for the standard challenge plugin's
`view.html`/`view.js`. It is a preview, not a test of CTFd itself: before the
event, check the theme on a real CTFd instance.
