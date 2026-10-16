import type { SessionInfo, Tokens } from './contracts';

export const API = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010').replace(/\/$/, '');
const AUTH_PROXY = import.meta.env.VITE_AUTH_SAME_ORIGIN_PROXY === 'true';
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
type Listener = () => void;

class AuthClient {
  tokens: Tokens | null = null; // Deliberately memory-only: no localStorage, sessionStorage, or IndexedDB.
  state: 'checking' | 'signed-in' | 'signed-out' | 'connection-error' = 'checking';
  message = '';
  private listeners = new Set<Listener>();
  private flight: Promise<void> | null = null;
  private generation = 0;
  private channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('economic-session') : null;

  constructor() {
    this.channel?.addEventListener('message', (event) => {
      if (event.data?.type === 'logout') this.clear();
      if (event.data?.type === 'login') {
        this.clear('checking');
        void this.bootstrap();
      }
    });
  }
  subscribe = (listener: Listener) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };
  private emit() {
    this.listeners.forEach((listener) => listener());
  }
  private clear(state: typeof this.state = 'signed-out') {
    this.invalidate();
    this.tokens = null;
    this.state = state;
    this.message = '';
    this.emit();
  }
  private invalidate() {
    this.generation++;
    this.flight = null;
  }
  private current(generation: number) {
    if (generation !== this.generation)
      throw new DOMException('The session changed while the request was pending.', 'AbortError');
  }
  private async lock<T>(operation: () => Promise<T>): Promise<T> {
    if (navigator.locks) return navigator.locks.request('economic-session-mutation', operation);
    return operation();
  }
  async call<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      const timeout = AbortSignal.timeout(12000);
      response = await fetch((AUTH_PROXY && path.startsWith('/api/v1/auth/') ? '' : API) + path, {
        ...init,
        signal: init.signal ? AbortSignal.any([init.signal, timeout]) : timeout,
        cache: 'no-store',
      });
    } catch {
      throw new ApiError(0, 'connection_error', 'Cannot reach the API. Check your connection and retry.');
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        body.error?.code || 'request_failed',
        body.error?.message || 'The request failed. Please retry.',
      );
    }
    if (response.status === 204) return undefined as T;
    try {
      return await response.json();
    } catch {
      throw new ApiError(0, 'interrupted_response', 'The API response was interrupted. Please retry.');
    }
  }
  private action(csrf?: string) {
    return {
      'Content-Type': 'application/json',
      'X-CSRF-Protection': '1',
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
    };
  }
  private session() {
    return this.call<SessionInfo>('/api/v1/auth/session', {
      credentials: 'include',
      ...(AUTH_PROXY ? { method: 'POST', headers: this.action(), body: '{}' } : {}),
    });
  }
  async login(username: string, password: string) {
    this.clear('checking');
    const generation = this.generation;
    try {
      await this.lock(async () => {
        this.current(generation);
        const tokens = await this.call<Tokens>('/api/v1/auth/login', {
          method: 'POST',
          credentials: 'include',
          headers: this.action(),
          body: JSON.stringify({ username, password }),
        });
        this.current(generation);
        this.tokens = tokens;
        this.state = 'signed-in';
        this.message = '';
        this.emit();
      });
    } catch (error) {
      if (generation === this.generation) this.clear();
      throw error;
    }
    this.current(generation);
    this.channel?.postMessage({ type: 'login' });
  }
  async bootstrap() {
    const generation = this.generation;
    try {
      await this.renew();
    } catch (error) {
      if (generation === this.generation) {
        this.state = 'connection-error';
        this.message = (error as Error).message;
        this.emit();
      }
    }
  }
  async renew(): Promise<void> {
    if (this.flight) return this.flight;
    const generation = this.generation;
    const flight = this.lock(async () => {
      this.current(generation);
      // Bootstrap from the actual shared cookie inside the lock, never an old tab's CSRF/session identity.
      const info = await this.session();
      this.current(generation);
      const tokens = await this.call<Tokens>('/api/v1/auth/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: this.action(info.csrf_token),
        body: '{}',
      });
      this.current(generation);
      // Set-Cookie has arrived before this body resolves. Confirmation is idempotent, including after loss.
      try {
        await this.call('/api/v1/auth/confirm', {
          method: 'POST',
          credentials: 'include',
          headers: this.action(info.csrf_token),
          body: '{}',
        });
      } catch (error) {
        this.current(generation);
        if (!(error instanceof ApiError) || error.status !== 0) throw error;
        await this.call('/api/v1/auth/confirm', {
          method: 'POST',
          credentials: 'include',
          headers: this.action(info.csrf_token),
          body: '{}',
        });
      }
      this.current(generation);
      this.tokens = tokens;
      this.state = 'signed-in';
      this.message = '';
      this.emit();
    })
      .catch((error) => {
        if (generation === this.generation && error instanceof ApiError && error.status === 401) this.clear();
        throw error;
      })
      .finally(() => {
        if (this.flight === flight) this.flight = null;
      });
    this.flight = flight;
    return flight;
  }
  async read<T>(path: string, signal?: AbortSignal): Promise<T> {
    signal?.throwIfAborted();
    const generation = this.generation;
    if (!this.tokens || Date.parse(this.tokens.access_expires_at) <= Date.now() + 30000) await this.renew();
    for (let attempt = 0; attempt < 2; attempt++) {
      signal?.throwIfAborted();
      this.current(generation);
      try {
        const result = await this.call<T>(path, {
          signal,
          credentials: 'omit',
          headers: { Authorization: `Bearer ${this.tokens?.access_token}` },
        });
        signal?.throwIfAborted();
        this.current(generation);
        return result;
      } catch (error) {
        signal?.throwIfAborted();
        this.current(generation);
        if (attempt === 0 && error instanceof ApiError && error.code === 'access_token_expired') {
          await this.renew();
          continue;
        }
        if (error instanceof ApiError && error.status === 401) this.clear();
        throw error;
      }
    }
    throw new Error('Unreachable request state');
  }
  async logout() {
    this.invalidate();
    const generation = this.generation;
    const tokens = this.tokens;
    await this.lock(async () => {
      this.current(generation);
      const validBearer = tokens && Date.parse(tokens.access_expires_at) > Date.now();
      const info = validBearer ? tokens! : await this.session();
      this.current(generation);
      await this.call('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
          ...this.action(info.csrf_token),
          ...(validBearer ? { Authorization: `Bearer ${tokens!.access_token}` } : {}),
        },
        body: '{}',
      });
      this.current(generation);
      this.clear();
    });
    this.channel?.postMessage({ type: 'logout' });
  }
}
export const auth = new AuthClient();
