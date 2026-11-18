// Reine Vektorsuche ueber das qmd-Paket (ohne Query-Erweiterung): node qmd_vektor.mjs <dbpfad> <n>  (den DB-Pfad bestimmt nachbarn.qmd_db_pfad)
// Abfrage per stdin (UTF-8). stdout: JSON-Array [{score, file, title}], file absolut.
// Exit 3: Index-Datenbank fehlt, Exit 1: sonstiger Fehler (Meldung auf stderr).
import { pathToFileURL } from "node:url";
import { join } from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

function fehler(code, text) {
  console.error(text);
  process.exit(code);
}

try {
  const [dbPath, n] = process.argv.slice(2);
  if (!dbPath) fehler(1, "DB-Pfad fehlt");
  const abfrage = readFileSync(0, "utf8");
  const paket = process.env.VERKNUEPFEN_QMD_PAKET
    || join(execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim(), "@tobilu/qmd");
  const qmd = await import(pathToFileURL(join(paket, "dist/index.js")).href);
  if (!existsSync(dbPath)) fehler(3, "qmd-Index nicht gefunden: " + dbPath);
  const store = await qmd.createStore({ dbPath });
  try {
    const ordner = {};
    for (const c of await store.listCollections()) ordner[c.name] = c.pwd;
    const treffer = await store.searchVector(abfrage, { limit: Number(n || 20) });
    const aus = [];
    for (const r of treffer) {
      const teile = String(r.displayPath).split("/");
      const pwd = ordner[teile[0]];
      if (pwd === undefined) continue;
      aus.push({ score: r.score, file: pwd.replace(/\/+$/, "") + "/" + teile.slice(1).join("/"), title: r.title });
    }
    console.log(JSON.stringify(aus));
  } finally {
    await store.close();
  }
} catch (e) {
  fehler(1, String((e && e.message) || e));
}
