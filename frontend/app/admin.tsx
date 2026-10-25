'use client';

import { useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, CalendarDays, FileText, ShieldCheck, Users, Wallet, Check, RefreshCw } from 'lucide-react';
import { api } from '../lib/api';

type AdminUser = { id: string; email: string; username?: string; display_name: string; suspended: boolean; platform_admin: boolean; mfa_enabled: boolean };
type AdminOrg = { id: string; name: string; licence: { expires_at: string; max_channels: number; max_listeners: number } | null };
type Metrics = { registered_users: number; live_events: number; posts: number; verified_ticket_revenue_minor: number };
type Audit = { id: string; actor_id: string | null; action: string; resource_id: string; created_at: string };

export default function AdminPortal({ notify, developmentMfaSkip = false }: { notify: (value: string) => void; developmentMfaSkip?: boolean }) {
  const cache = useQueryClient();
  const [tab, setTab] = useState('Overview'); const [busy, setBusy] = useState(false);
  const metrics = useQuery({ queryKey: ['admin', 'metrics'], queryFn: () => api<Metrics>('/admin/metrics') });
  const users = useQuery({ queryKey: ['admin', 'users'], queryFn: () => api<AdminUser[]>('/admin/users'), enabled: tab === 'Accounts' });
  const orgs = useQuery({ queryKey: ['admin', 'organisations'], queryFn: () => api<AdminOrg[]>('/admin/organisations'), enabled: tab === 'Licensing' });
  const audit = useQuery({ queryKey: ['admin', 'audit'], queryFn: () => api<Audit[]>('/admin/audit'), enabled: tab === 'Audit log' });
  async function suspend(user: AdminUser) {
    setBusy(true);
    try { await api(`/admin/users/${user.id}/status`, { method: 'PUT', body: JSON.stringify({ suspended: !user.suspended }) }); await cache.invalidateQueries({ queryKey: ['admin'] }); notify(user.suspended ? 'Account reinstated.' : 'Account suspended. Existing sessions were revoked.'); }
    catch (error) { notify((error as Error).message); } finally { setBusy(false); }
  }
  async function license(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); const data = Object.fromEntries(new FormData(event.currentTarget));
    try { await api(`/admin/organisations/${data.organisation_id}/licence`, { method: 'PUT', body: JSON.stringify({ expires_at: new Date(String(data.expires_at)).toISOString(), max_channels: Number(data.max_channels), max_listeners: Number(data.max_listeners) }) }); await cache.invalidateQueries({ queryKey: ['admin'] }); notify('Organisation licence updated and audited.'); }
    catch (error) { notify((error as Error).message); } finally { setBusy(false); }
  }
  return <>
    <section className="page-title"><div><div className="eyebrow"><span />PLATFORM OPERATIONS</div><h1>Keep the culture moving.</h1><p>Administrator controls are authorised and audited by the API.</p></div><span className="soft-tag"><ShieldCheck size={13} />{developmentMfaSkip ? 'Local testing · MFA skipped' : 'MFA protected'}</span></section>
    <div className="admin-tabs" aria-label="Administration sections">{['Overview', 'Accounts', 'Licensing', 'Audit log'].map(value => <button key={value} onClick={() => setTab(value)} className={value === tab ? 'selected' : ''}>{value}</button>)}<button aria-label="Refresh administration data" onClick={() => cache.invalidateQueries({ queryKey: ['admin'] })}><RefreshCw size={15} /></button></div>
    {metrics.isError ? <div className="form-error" role="alert">{metrics.error.message} Sign out and sign in using a verified administrator authenticator code.</div> : <>
      {tab === 'Overview' && <><div className="metric-grid">{[
        { name: 'Registered accounts', value: metrics.data?.registered_users, Icon: Users, detail: 'All persisted accounts, including local test accounts.' },
        { name: 'Live events', value: metrics.data?.live_events, Icon: CalendarDays, detail: 'Events whose lifecycle status is live.' },
        { name: 'Community posts', value: metrics.data?.posts, Icon: FileText, detail: 'All persisted community posts.' },
        { name: 'Verified ticket revenue', value: metrics.data ? new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN' }).format(metrics.data.verified_ticket_revenue_minor / 100) : undefined, Icon: Wallet, detail: 'Successful server-verified ticket payments in NGN.' },
      ].map(({ name, value, Icon, detail }) => <article className="panel metric-card" key={name}><Icon size={20} /><span>{name}</span><strong>{value ?? '—'}</strong><p>{detail}</p></article>)}</div><div className="info-note"><Activity size={20} /><span>Listener concurrency, audio quality and provider uptime are not connected to telemetry yet. No operational values are estimated here.</span></div></>}
      {tab === 'Accounts' && <section className="panel"><h2>Accounts & access</h2><p>Suspension blocks sign-in and revokes active sessions. Administrators cannot suspend their own account.</p>{users.isError && <div className="form-error">{users.error.message}</div>}<div className="table-scroll"><table className="admin-table"><caption>Platform user accounts</caption><thead><tr><th>Account</th><th>Access</th><th>Status</th><th>Action</th></tr></thead><tbody>{users.data?.map(user => <tr key={user.id}><td><b>{user.display_name}</b><small>{user.username ? '@' + user.username : user.email}</small></td><td>{user.platform_admin ? 'Administrator' : 'Member'}<small>{user.mfa_enabled ? 'MFA enrolled' : 'MFA not enrolled'}</small></td><td><span className="soft-tag">{user.suspended ? 'Suspended' : 'Active'}</span></td><td><button className="text-button" disabled={busy} onClick={() => suspend(user)}>{user.suspended ? 'Reinstate' : 'Suspend'}</button></td></tr>)}</tbody></table></div>{users.isPending && <p>Loading accounts…</p>}</section>}
      {tab === 'Licensing' && <div className="studio-grid"><section className="panel"><h2>Organisation licences</h2><p>Set the channel policy and licence expiry. Live listener capacity still requires SFU admission reconciliation.</p>{orgs.isError && <div className="form-error">{orgs.error.message}</div>}{orgs.data?.map(org => <article className="admin-org" key={org.id}><b>{org.name}</b><small>{org.licence ? `${org.licence.max_channels} channels · ${org.licence.max_listeners} listener policy · Expires ${new Date(org.licence.expires_at).toLocaleString()}` : 'No active licence configured'}</small></article>)}</section><section className="panel"><h2>Issue or update a licence</h2><form onSubmit={license}><label>Organisation<select name="organisation_id" defaultValue="" required><option value="" disabled>Select organisation</option>{orgs.data?.map(org => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label><label>Expires at<input name="expires_at" type="datetime-local" required /></label><div className="form-grid"><label>DJ channels<input name="max_channels" type="number" min={1} max={32} defaultValue={4} required /></label><label>Listener policy limit<input name="max_listeners" type="number" min={1} max={100000} defaultValue={100} required /></label></div><button className="button full" disabled={busy || !orgs.data?.length}>{busy ? 'Saving…' : 'Save licence'}<Check size={16} /></button></form><p className="privacy-note">Manual provisioning is an audited operator action. It does not confirm a subscription payment.</p></section></div>}
      {tab === 'Audit log' && <section className="panel"><h2>Recent permission & operation events</h2><p>Most recent 100 events. Passwords, authenticator keys and session tokens are excluded.</p>{audit.isError && <div className="form-error">{audit.error.message}</div>}<div className="table-scroll"><table className="admin-table"><caption>Recent audit events</caption><thead><tr><th>Action</th><th>Resource</th><th>Time</th></tr></thead><tbody>{audit.data?.map(item => <tr key={item.id}><td>{item.action}</td><td><code>{item.resource_id}</code></td><td>{new Date(item.created_at).toLocaleString()}</td></tr>)}</tbody></table></div></section>}
    </>}
  </>;
}
