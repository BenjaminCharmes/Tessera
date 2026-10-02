import { chromium } from "@playwright/test";
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } });
const errs = [];
p.on("pageerror", (e) => errs.push("PAGEERROR " + String(e).slice(0, 300)));
await p.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await p.getByText("ide-core", { exact: true }).first().click();
await p.waitForTimeout(1500);
await p.getByText("Statistiques", { exact: true }).first().click();
await p.waitForTimeout(3000);
await p.screenshot({ path: process.argv[2] + "/stats.png" });
const lignes = p.locator("table tbody tr");
console.log("lignes de runs:", await lignes.count());
if (await lignes.count()) {
  await lignes.first().click();
  await p.waitForTimeout(3000);
  await p.screenshot({ path: process.argv[2] + "/run-rouvert.png" });
  const t = await p.locator("body").innerText();
  console.log(t.split("\n").filter((l) => /CODEUR|REVIEWER|SÉCURITÉ|VALIDATEUR|Historique|Run ticket/.test(l)).slice(0, 12).join("\n"));
}
console.log("ERREURS:", errs.join("\n"));
await b.close();
