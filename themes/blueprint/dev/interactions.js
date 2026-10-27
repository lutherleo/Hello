// Interaction checks against the preview servers (see README): search, hide-cracked
// memory, copy button, your-crew row, navbar clock. Prints results; exits non-zero on failure.
// node dev/interactions.js <outdir>
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  await p.goto("http://127.0.0.1:8765/challenges", { waitUntil: "networkidle" });
  await p.keyboard.press("/");
  console.log("search focused:", await p.evaluate(() => document.activeElement.id));
  await p.keyboard.type("lattice");
  await p.waitForTimeout(200);
  console.log("visible parts after 'lattice':", await p.locator(".bp-part:visible").count());
  await p.keyboard.press("Escape");
  await p.waitForTimeout(200);
  console.log("visible after Esc:", await p.locator(".bp-part:visible").count());
  await p.fill("#bp-search-input", "zzzz");
  await p.waitForTimeout(200);
  console.log("no-match message:", await p.locator("text=No targets match").count());
  await p.fill("#bp-search-input", "");
  await p.click("text=Hide cracked");
  await p.reload({ waitUntil: "networkidle" });
  console.log("hide cracked remembered:", await p.locator("text=Show cracked").isVisible(), "visible parts:", await p.locator(".bp-part:visible").count());
  await p.click("text=Show cracked");
  await p.locator(".bp-part").nth(3).click();
  await p.waitForSelector(".modal.show .bp-copy");
  console.log("copy button:", await p.locator(".modal.show .bp-copy").count());
  await p.screenshot({ path: process.argv[2] + "/qol-modal.png" });
  await p.keyboard.press("Escape");
  console.log("clock:", await p.locator(".bp-clock").innerText());
  await p.goto("http://127.0.0.1:8765/scoreboard", { waitUntil: "networkidle" });
  await p.waitForSelector(".bp-graph__plot svg");
  console.log("my row:", await p.locator("tr.bp-row--me").count(), await p.locator("tr.bp-row--me a").innerText());
  await p.click("text=Find my crew");
  await p.waitForTimeout(400);
  await p.screenshot({ path: process.argv[2] + "/qol-ledger.png" });
  console.log("errors:", errs);
  await b.close();
})();
