import type { NextConfig } from 'next';
const config: NextConfig = {
  output: 'standalone',
  turbopack: { root: process.cwd() },
  async rewrites() { return [{ source: '/api/:path*', destination: `${process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'}/api/:path*` }]; },
  async headers() { return [{ source: '/:path*', headers: [{ key: 'X-Content-Type-Options', value: 'nosniff' }, { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' }, { key: 'Permissions-Policy', value: 'camera=(), geolocation=(), microphone=(self)' }, { key: 'Content-Security-Policy', value: `default-src 'self'; script-src 'self' 'unsafe-inline'${process.env.NODE_ENV === 'development' ? " 'unsafe-eval'" : ''}; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://images.unsplash.com; connect-src 'self' wss: https:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'` }] }]; }
};
export default config;
