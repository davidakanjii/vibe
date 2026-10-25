import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, sep, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const startup = fileURLToPath(new URL('./start.mjs', import.meta.url));
function fixture(t, built = true) {
  const base = resolve(tmpdir());
  const root = mkdtempSync(join(base, 'vibesync-start-'));
  t.after(() => {
    assert.ok(resolve(root).startsWith(base + sep) && basename(root).startsWith('vibesync-start-'));
    rmSync(root, { recursive: true, force: true });
  });
  if (built) {
    for (const dir of ['public', '.next/static', '.next/standalone']) mkdirSync(join(root, dir), { recursive: true });
    writeFileSync(join(root, 'public/icon.svg'), '<svg/>');
    writeFileSync(join(root, '.next/static/asset.js'), '// fixture');
    writeFileSync(join(root, '.next/standalone/server.js'), 'process.stdout.write(JSON.stringify({hostname:process.env.HOSTNAME,port:process.env.PORT,mode:process.env.NODE_ENV}));');
  }
  return root;
}
test('standalone startup overrides the container hostname and preserves the hosting port', t => {
  const root = fixture(t);
  const result = spawnSync(process.execPath, [startup], { cwd: root, env: { ...process.env, HOSTNAME: 'container-hostname.invalid', PORT: '10000' }, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), { hostname: '0.0.0.0', port: '10000', mode: 'production' });
  assert.ok(existsSync(join(root, '.next/standalone/public/icon.svg')));
  assert.ok(existsSync(join(root, '.next/standalone/.next/static/asset.js')));
});
test('standalone startup defaults to port 3000 without a hosting port', t => {
  const root = fixture(t);
  const env = { ...process.env }; delete env.PORT;
  const result = spawnSync(process.execPath, [startup], { cwd: root, env, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(JSON.parse(result.stdout).port, '3000');
});
test('standalone startup explains a missing production build', t => {
  const root = fixture(t, false);
  const result = spawnSync(process.execPath, [startup], { cwd: root, encoding: 'utf8' });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Run npm run build before npm start/);
});
