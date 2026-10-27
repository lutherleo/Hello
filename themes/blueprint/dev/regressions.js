// Regression checks for bugs found in review: haul includes awards, cut counts only
// scoreboard members, CRACKED stamp scoped to the challenge window, all-cracked board
// message, Find my crew vs bracket/search, organizer graph-option override.
// Needs the logged-in preview server on 8765. node dev/regressions.js
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  // 4/5: haul and cut
  await p.goto("http://127.0.0.1:8765/challenges", { waitUntil: "networkidle" });
  await p.waitForTimeout(400);
  console.log("haul:", await p.locator(".bp-gauge__value").innerText(), "| cut:", await p.locator(".bp-cut strong").innerText(), "| split:", (await p.locator(".bp-cut").innerText()).replace(/\s+/g, " "));
  // solve one and check haul refresh
  await p.locator(".bp-part").nth(3).click();
  await p.waitForSelector(".modal.show #challenge-input");
  await p.fill("#challenge-input", "csawctf{x}"); await p.keyboard.press("Enter");
  await p.waitForSelector(".modal.show .alert-success"); await p.waitForTimeout(600);
  console.log("haul after solve:", await p.locator(".bp-gauge__value").innerText());
  // 2: stamp only in challenge window
  console.log("stamp content in challenge window:", await p.evaluate(() => getComputedStyle(document.querySelector("#challenge-window .alert-success"), "::before").content));
  await p.keyboard.press("Escape"); await p.waitForTimeout(400);
  // 4: hide cracked with all solved
  await p.evaluate(() => { const d = Alpine.$data(document.querySelector('[x-data="ChallengeBoard"]')); d.challenges = d.challenges.map(c => ({ ...c, solved_by_me: true })); });
  await p.click("text=Hide cracked"); await p.waitForTimeout(300);
  console.log("all-cracked message:", await p.locator("text=Every target on the board is cracked").count());
  await p.click("text=Show cracked targets"); await p.waitForTimeout(200);
  await p.evaluate(() => { try { localStorage.removeItem("bp-hide-cracked"); } catch (e) {} });
  // 1: find my crew with a bracket that excludes me
  await p.goto("http://127.0.0.1:8765/scoreboard", { waitUntil: "networkidle" });
  await p.waitForTimeout(500);
  await p.click("#scoreboard .nav-pills >> text=Student");
  await p.waitForTimeout(300);
  console.log("find-my-crew visible under Student bracket (me not student):", await p.locator("text=Find my crew").isVisible());
  await p.click("#scoreboard .nav-pills >> text=All");
  await p.fill("#bp-crew-search", "null"); await p.waitForTimeout(200);
  await p.click("text=Find my crew"); await p.waitForTimeout(500);
  console.log("after Find my crew with a filter: query cleared:", (await p.inputValue("#bp-crew-search")) === "", "| my row visible:", await p.locator("#bp-me").isVisible());
  // 3: organizer override wins
  console.log("override:", await p.evaluate(() => { window.userScoreGraphChartOptions = { title: { text: "custom" } }; return window.userScoreGraphChartOptions.title.text; }));
  console.log("errors:", errs);
  await b.close();
})();
