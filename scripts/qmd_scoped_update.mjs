// Re-index ONLY the named QMD collections (the `qmd update` CLI has no
// collection filter and re-indexes every collection on the machine).
// Uses QMD's own SDK `store.update({collections})` against the same index
// file the CLI uses, in DB-only mode (no config rewrite).
//
// Usage: node scripts/qmd_scoped_update.mjs <collection> [<collection> ...]
import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const names = process.argv.slice(2);
if (names.length === 0) {
  console.error("qmd_scoped_update: give at least one collection name");
  process.exit(2);
}

const globalRoot = execSync("npm root -g", { encoding: "utf8" }).trim();
const entry = join(globalRoot, "@tobilu", "qmd", "dist", "index.js");
if (!existsSync(entry)) {
  console.error(`qmd_scoped_update: QMD SDK not found at ${entry}`);
  process.exit(2);
}
const { createStore } = await import(pathToFileURL(entry).href);

const dbPath =
  process.env.INDEX_PATH ||
  join(process.env.XDG_CACHE_HOME || join(homedir(), ".cache"), "qmd", "index.sqlite");
const store = await createStore({ dbPath });
try {
  // listCollections() reads the registry itself; getStatus() omits empty
  // collections, which a fresh instance legitimately has.
  const known = new Set((await store.listCollections()).map((c) => c.name));
  const missing = names.filter((n) => !known.has(n));
  if (missing.length) {
    console.error(`qmd_scoped_update: not registered: ${missing.join(", ")} (run configure-search.ps1)`);
    process.exit(3);
  }
  const r = await store.update({ collections: names });
  console.log(
    `scoped update: ${r.collections} collection(s) - ${r.indexed} new, ${r.updated} updated, ` +
      `${r.unchanged} unchanged, ${r.removed} removed; ${r.needsEmbedding} hashes need vectors`,
  );
} finally {
  await store.close?.();
}
