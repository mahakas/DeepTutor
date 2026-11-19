import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

// Resolve <web>/locales by walking up from the compiled test location
// (dist/node-tests/tests/*.js) until we find the locales directory.
function findLocalesRoot(): string {
  let dir = __dirname;
  for (let i = 0; i < 8; i++) {
    const candidate = path.join(dir, "locales");
    // TypeScript copies only statically imported JSON to dist. Require both
    // namespaces so coverage is tested against the complete source catalogs.
    if (fs.existsSync(path.join(candidate, "en", "common.json"))) return candidate;
    dir = path.dirname(dir);
  }
  throw new Error("could not locate locales/ directory from " + __dirname);
}

function listJsonFiles(dir: string): string[] {
  const out: string[] = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...listJsonFiles(full));
    else if (ent.isFile() && ent.name.endsWith(".json")) out.push(full);
  }
  return out;
}

// A "namespace key" is a dotted identifier such as `settingsTour.appearance.title`
// (lowercase camelCase segments, no whitespace). These are code-side keys whose
// value must be real translated copy — never the key itself. Plain-English keys
// like "Back" or proper nouns like "Chart.js" do not match (the latter starts
// uppercase), so they are correctly excluded.
const NAMESPACE_KEY = /^[a-z][A-Za-z0-9]*(\.[A-Za-z0-9]+)+$/;

const localesRoot = findLocalesRoot();
const enRoot = path.join(localesRoot, "en");

for (const file of listJsonFiles(enRoot)) {
  const rel = path.relative(localesRoot, file).replaceAll("\\", "/");
  test(`en locale ${rel} has no untranslated placeholder values`, () => {
    const json = JSON.parse(fs.readFileSync(file, "utf8")) as Record<
      string,
      unknown
    >;
    const placeholders: string[] = [];
    for (const [key, value] of Object.entries(json)) {
      if (NAMESPACE_KEY.test(key) && value === key) placeholders.push(key);
    }
    assert.deepEqual(
      placeholders,
      [],
      `Found namespace keys whose value equals the key (untranslated placeholders): ${placeholders.join(", ")}`,
    );
  });
}

// Persian is the deployment default. Do not silently regress to English when
// adding a source string or lose interpolation arguments in translated copy.
for (const bundle of ["app.json", "common.json"]) {
  const en = JSON.parse(fs.readFileSync(path.join(enRoot, bundle), "utf8")) as Record<string, string>;
  const fa = JSON.parse(fs.readFileSync(path.join(localesRoot, "fa", bundle), "utf8")) as Record<string, string>;

  test(`fa ${bundle} covers every source key and has no extra keys`, () => {
    assert.deepEqual(Object.keys(fa).sort(), Object.keys(en).sort());
  });

  test(`fa ${bundle} is flat, nonempty and preserves interpolation occurrences`, () => {
    const placeholders = (value: string) =>
      [...value.matchAll(/\{\{\s*([A-Za-z0-9_]+)\s*\}\}/g)]
        .map((match) => match[1]).sort();
    for (const [key, source] of Object.entries(en)) {
      const translated = fa[key];
      assert.equal(typeof translated, "string", key);
      assert.ok(translated.trim(), key);
      // Compare against the displayed value: English also has rename-table
      // entries where the literal lookup key is not the sentence being shown.
      assert.deepEqual(placeholders(translated), placeholders(source), key);
    }
  });
}
