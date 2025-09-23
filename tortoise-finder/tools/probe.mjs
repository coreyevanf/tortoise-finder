import { chromium } from "@playwright/test";
import fs from "fs";
import path from "path";
import AxeBuilder from "@axe-core/playwright";

const url = process.argv[2] || "http://localhost:3000";
const outDir = process.argv[3] || "artifacts";
await fs.promises.mkdir(outDir, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext();
const page = await ctx.newPage();

const logs = [], requests = [];
page.on("console", m => logs.push({ type: m.type(), text: m.text() }));
page.on("pageerror", e => logs.push({ type: "error", text: e.message }));
page.on("requestfailed", r => requests.push({ url: r.url(), failure: r.failure() }));
page.on("response", async r => {
  if (r.status() >= 400) requests.push({ url: r.url(), status: r.status() });
});

await page.goto(url, { waitUntil: "networkidle" });

// Basic a11y audit
const axe = await new AxeBuilder({ page }).analyze();

// Snapshot artifacts
const pngPath = path.join(outDir, "screenshot.png");
const htmlPath = path.join(outDir, "dom.html");
await page.screenshot({ path: pngPath, fullPage: true });
await fs.promises.writeFile(htmlPath, await page.content(), "utf8");

const result = {
  url,
  title: await page.title(),
  screenshot: pngPath,
  domSnapshot: htmlPath,
  console: logs.slice(-50),
  networkIssues: requests.slice(-100),
  a11y: { violations: axe.violations.slice(0, 20) }
};

const jsonPath = path.join(outDir, "probe.json");
await fs.promises.writeFile(jsonPath, JSON.stringify(result, null, 2));
console.log(jsonPath); // <-- agent can read this
await browser.close();
