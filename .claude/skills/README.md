# Design skills

Five skills for building and checking frontends, vendored from their public
upstream repositories. Each folder keeps its upstream license.

| Folder | Skill | Upstream | Commit |
| --- | --- | --- | --- |
| `taste-skill/` | Taste Skill (`design-taste-frontend`): art direction from 247 curated sites, browser-checked | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) `skills/taste-skill` | `12af471` |
| `web-design-guidelines/` | Audits UI code against Vercel's Web Interface Guidelines | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) `skills/web-design-guidelines` | `063bee9` |
| `ui-ux-pro-max/`, `design-system/` | Design system generation: palettes, font pairings, tokens, component specs | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) `.claude/skills/` | `28b3b8d` |
| `21st-ui/` | 21st.dev component library via the 21st MCP server | [21st-dev/magic-mcp](https://github.com/21st-dev/magic-mcp) `skills/21st-ui` | `6b5299e` |
| `playwright-cli/` | Drive a real browser from the command line | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) `skills/playwright-cli` | `b1a5903` |

## Setup

- **21st.dev MCP**: the repo's `.mcp.json` registers the server. Get a free key
  at <https://21st.dev/mcp> and export it as `API_KEY_21ST` before starting
  Claude Code.
- **Taste Skill** scripts need Node 22+ and Chrome/Chromium.
- **Playwright CLI**: `npm install -g @playwright/cli` (see the skill's
  `SKILL.md`).
- **Web Design Guidelines** fetches the current rules from GitHub on each run.

To update a skill, re-copy its folder from the upstream path above.
