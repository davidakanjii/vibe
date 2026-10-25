"""Run a real HTTP smoke test against local services. Creates labelled disposable test records."""
import json
import secrets
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor, Request
from urllib.error import HTTPError
from urllib.parse import urlparse
import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:3000')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    if urlparse(base).hostname not in ('127.0.0.1', 'localhost'):
        raise SystemExit('This smoke test is restricted to loopback development servers.')
    jar = CookieJar()
    client = build_opener(HTTPCookieProcessor(jar))
    csrf = ''

    def call(path, method='GET', payload=None, expected=200):
        headers = {'Origin': base, 'Content-Type': 'application/json'}
        if csrf:
            headers['X-CSRF-Token'] = csrf
        request = Request(base + '/api' + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers, method=method)
        try:
            response = client.open(request, timeout=30)
            status, body = response.status, response.read()
        except HTTPError as error:
            status, body = error.code, error.read()
        assert status == expected, f'{method} {path}: expected {expected}, received {status}: {body[:300]!r}'
        return json.loads(body) if body else None

    identity = secrets.token_hex(6)
    account = call('/auth/register', 'POST', {'email': f'smoke-{identity}@example.test', 'display_name': '[Test] HTTP smoke', 'password': secrets.token_urlsafe(24)}, 201)
    csrf = account['csrf_token']
    assert call('/auth/me')['user']['id'] == account['user']['id']
    org = call('/organisations', 'POST', {'name': '[Test] HTTP smoke ' + identity}, 201)
    start = datetime.now(timezone.utc) + timedelta(days=2)
    event = call('/events', 'POST', {'organisation_id': org['id'], 'title': '[Test] HTTP event', 'description': 'Disposable local integration test record', 'venue': 'Fictional venue', 'city': 'Lagos', 'genre': 'Afrobeats', 'starts_at': start.isoformat(), 'ends_at': (start + timedelta(hours=2)).isoformat(), 'capacity': 10, 'price_minor': 0}, 201)
    assert event['status'] == 'draft'
    call(f'/events/{event["id"]}/status', 'POST', {'status': 'published'}, 403)
    call('/me/preferences', 'PATCH', {'marketing_email': True})
    assert call('/me')['user']['marketing_consent'] is True
    call('/me/preferences', 'PATCH', {'marketing_email': False})
    post = call('/feed', 'POST', {'body': '[Test] Local HTTP smoke verifies persistence.'}, 201)
    assert any(item['id'] == post['id'] for item in call('/feed'))
    call(f'/posts/{post["id"]}/reactions', 'POST', {})
    call('/reports', 'POST', {'target_type': 'post', 'target_id': post['id'], 'reason': 'Disposable smoke-test report'}, 201)
    call('/tickets')
    call('/auth/logout', 'POST', {}, 204)
    call('/auth/me', expected=401)
    print('PASS: real HTTP registration/session/CSRF, organisation, event draft/licence denial, preferences, feed, reaction, report, tickets, logout.')
    print('Labelled [Test] records remain in the local development database. No external calls or payments were made.')


if __name__ == '__main__':
    main()
