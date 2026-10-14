import { createRequire } from 'node:module';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after } from 'node:test';
const require = createRequire(import.meta.url);
const ts = require('typescript');
const folder = mkdtempSync(join(tmpdir(), 'homestretch-core-'));
writeFileSync(join(folder, 'package.json'), '{"type":"commonjs"}');
for (const name of ['protocol', 'curlCounter', 'curlSession']) {
  const source = readFileSync(new URL(`../src/wearable/${name}.ts`, import.meta.url), 'utf8');
  writeFileSync(join(folder, `${name}.js`), ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText);
}
after(() => rmSync(folder, { recursive: true, force: true }));
export const protocol = require(join(folder, 'protocol.js'));
export const { CurlCounter } = require(join(folder, 'curlCounter.js'));
export const { CurlSession } = require(join(folder, 'curlSession.js'));
