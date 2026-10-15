import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Tokens } from './contracts';

let broadcast: (event: { data: { type: string } }) => void;
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}
const json = (value: unknown) => new Response(JSON.stringify(value), { status: 200 });
const tokens = (id = 'a'): Tokens => ({
  user: { id, username: id },
  csrf_token: 'test-csrf-' + id,
  session_expires_at: new Date(Date.now() + 86400000).toISOString(),
  access_token: 'test-access-' + id,
  token_type: 'bearer',
  expires_in: 900,
  access_expires_at: new Date(Date.now() + 900000).toISOString(),
});
beforeEach(() => {
  vi.resetModules();
  vi.stubGlobal('navigator', {});
  vi.stubGlobal(
    'BroadcastChannel',
    class {
      addEventListener(_name: string, listener: typeof broadcast) {
        broadcast = listener;
      }
      postMessage() {}
    },
  );
});

describe('auth state authority under delayed responses', () => {
  it('does not publish an interrupted renewal after another tab logs out', async () => {
    const confirm = deferred<Response>();
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json(tokens()))
      .mockReturnValueOnce(confirm.promise);
    vi.stubGlobal('fetch', fetch);
    const { auth } = await import('./auth');
    const renewal = auth.renew();
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    broadcast({ data: { type: 'logout' } });
    confirm.resolve(new Response(null, { status: 204 }));
    await renewal.catch(() => {});
    expect(auth.state).toBe('signed-out');
    expect(auth.tokens).toBeNull();
  });
  it('does not let an old renewal overwrite a newer account login', async () => {
    const confirm = deferred<Response>();
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(tokens('a')))
      .mockResolvedValueOnce(json(tokens('a')))
      .mockReturnValueOnce(confirm.promise)
      .mockResolvedValueOnce(json(tokens('b')));
    vi.stubGlobal('fetch', fetch);
    const { auth } = await import('./auth');
    const renewal = auth.renew();
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    await auth.login('b', 'test-only-password');
    confirm.resolve(new Response(null, { status: 204 }));
    await renewal.catch(() => {});
    expect(auth.tokens?.user.id).toBe('b');
  });
  it('clears the session when the read retried after renewal is revoked', async () => {
    const expired = { error: { code: 'access_token_expired', message: 'renew' } };
    const revoked = { error: { code: 'invalid_session', message: 'sign in' } };
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(expired), { status: 401 }))
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(revoked), { status: 401 }));
    vi.stubGlobal('fetch', fetch);
    const { auth } = await import('./auth');
    auth.tokens = tokens();
    auth.state = 'signed-in';
    await expect(auth.read('/api/v1/dashboard')).rejects.toThrow('sign in');
    expect(auth.state).toBe('signed-out');
    expect(auth.tokens).toBeNull();
  });
  it('does not start session mutation for an already cancelled read', async () => {
    const fetch = vi.fn().mockRejectedValue(new Error('not a real network call'));
    vi.stubGlobal('fetch', fetch);
    const { auth } = await import('./auth');
    const controller = new AbortController();
    controller.abort();
    await expect(auth.read('/api/v1/dashboard', controller.signal)).rejects.toThrow();
    expect(fetch).not.toHaveBeenCalled();
  });
  it('ignores an old rejected read after a different account signs in', async () => {
    const oldRead = deferred<Response>();
    const fetch = vi
      .fn()
      .mockReturnValueOnce(oldRead.promise)
      .mockResolvedValueOnce(json(tokens('b')));
    vi.stubGlobal('fetch', fetch);
    const { auth } = await import('./auth');
    auth.tokens = tokens('a');
    auth.state = 'signed-in';
    const read = auth.read('/api/v1/dashboard');
    await auth.login('b', 'test-only-password');
    oldRead.resolve(new Response(JSON.stringify({ error: { code: 'invalid_session' } }), { status: 401 }));
    await expect(read).rejects.toThrow('session changed');
    expect(auth.tokens?.user.id).toBe('b');
  });
  it('cancels a waiting read without cancelling another read sharing renewal', async () => {
    const session = deferred<Response>();
    const fetch = vi
      .fn()
      .mockReturnValueOnce(session.promise)
      .mockResolvedValueOnce(json(tokens()))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(json({ ok: true }));
    vi.stubGlobal('fetch', fetch);
    const { auth } = await import('./auth');
    const controller = new AbortController();
    const cancelled = auth.read('/api/v1/dashboard', controller.signal);
    const active = auth.read('/api/v1/dashboard');
    controller.abort();
    session.resolve(json(tokens()));
    await expect(cancelled).rejects.toThrow();
    await expect(active).resolves.toEqual({ ok: true });
    expect(fetch).toHaveBeenCalledTimes(4);
  });
});
