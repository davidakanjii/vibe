export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const csrf = document.cookie.split('; ').find(value => value.startsWith('vs_csrf='))?.split('=')[1];
  const response = await fetch('/api' + path, {
    credentials: 'same-origin', ...options,
    headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': decodeURIComponent(csrf) } : {}), ...options.headers },
  });
  if (!response.ok) {
    let message = 'The service is temporarily unavailable. Please try again.';
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : body.detail?.[0]?.msg || message; } catch {}
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
