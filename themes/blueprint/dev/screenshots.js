// Screenshot the preview server's pages at several widths, in both prints.
// Needs three preview servers: 8765 (logged in), 8766 --anon, 8767 --empty.
// node dev/screenshots.js <outdir> [only-substring]
const { chromium } = require("playwright");
const path = require("path");

const out = process.argv[2];
const only = process.argv[3] || "";

const shots = [
  { name: "cover", url: "http://127.0.0.1:8765/" },
  { name: "challenges", url: "http://127.0.0.1:8765/challenges", wait: ".bp-part" },
  { name: "challenge-modal", url: "http://127.0.0.1:8765/challenges", wait: ".bp-part", modal: 3 },
  { name: "challenges-anon", url: "http://127.0.0.1:8766/challenges", wait: ".bp-part" },
  { name: "challenges-empty", url: "http://127.0.0.1:8767/challenges", wait: ".bp-empty" },
  { name: "scoreboard", url: "http://127.0.0.1:8765/scoreboard", wait: ".bp-graph__plot svg" },
  { name: "login", url: "http://127.0.0.1:8766/login" },
  { name: "register", url: "http://127.0.0.1:8766/register" },
  { name: "404", url: "http://127.0.0.1:8765/nope" },
];

const widths = [
  { tag: "desktop", width: 1440, height: 900 },
  { tag: "mobile", width: 390, height: 844 },
];

(async () => {
  const proxy = process.env.HTTPS_PROXY
    ? { server: process.env.HTTPS_PROXY, bypass: "127.0.0.1,localhost" }
    : undefined;
  const browser = await chromium.launch({ proxy });
  for (const mode of ["dark", "light"]) {
    for (const w of widths) {
      const ctx = await browser.newContext({ viewport: { width: w.width, height: w.height } });
      await ctx.addInitScript(m => localStorage.setItem("theme", m), mode);
      for (const s of shots) {
        if (only && !s.name.includes(only)) continue;
        const page = await ctx.newPage();
        const errors = [];
        page.on("pageerror", e => errors.push("pageerror: " + e.message));
        page.on("console", m => m.type() === "error" && errors.push("console: " + m.text()));
        await page.goto(s.url, { waitUntil: "networkidle" });
        if (s.wait) await page.waitForSelector(s.wait, { timeout: 8000 }).catch(e => errors.push("wait: " + e.message));
        if (s.modal) {
          await page.locator(".bp-part").nth(s.modal).click();
          await page.waitForSelector(".modal.show .challenge-name", { timeout: 8000 }).catch(e => errors.push("modal: " + e.message));
          await page.waitForTimeout(500);
        }
        await page.waitForTimeout(400);
        const file = path.join(out, `${s.name}-${mode}-${w.tag}.png`);
        await page.screenshot({ path: file, fullPage: !s.modal });
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
        console.log(file, overflow ? "HORIZONTAL-OVERFLOW" : "", errors.filter(e => !/status of 404/.test(e)).join(" | "));
        await page.close();
      }
      await ctx.close();
    }
  }
  await browser.close();
})();
