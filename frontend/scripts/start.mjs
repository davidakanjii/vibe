import { cpSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';

const root = process.cwd();
const standalone = resolve(root, '.next/standalone');
if (!existsSync(resolve(standalone, 'server.js'))) {
  throw new Error('Production output is missing. Run npm run build before npm start.');
}
cpSync(resolve(root, 'public'), resolve(standalone, 'public'), { recursive: true, force: true });
cpSync(resolve(root, '.next/static'), resolve(standalone, '.next/static'), { recursive: true, force: true });
const server = spawn(process.execPath, [resolve(standalone, 'server.js')], {
  cwd: standalone,
  env: { ...process.env, NODE_ENV: 'production', HOSTNAME: process.env.HOSTNAME || '0.0.0.0', PORT: process.env.PORT || '3000' },
  stdio: 'inherit',
});
for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => server.kill(signal));
server.on('exit', code => process.exit(code ?? 1));
