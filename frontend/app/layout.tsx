import type { Metadata, Viewport } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'VibeSync — Find your frequency', description: 'Discover your next night out. Connect with your community and tune into authorised live DJ channels.', manifest: '/manifest.webmanifest', appleWebApp: { capable: true, title: 'VibeSync', statusBarStyle: 'black-translucent' } };
export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#101110' };
export default function Layout({ children }: { children: React.ReactNode }) { return <html lang="en"><body>{children}</body></html>; }
