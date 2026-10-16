import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { auth } from './auth';
import type { Dashboard, IndicatorPanel, Panel, PanelId } from './contracts';
import { PanelHeading, PanelLoading, ReadNotice, RecoveryBoundary, titles } from './PanelParts';
import { layout } from './layout';
import { Ticker, useTicker } from './Ticker';

function PanelSlot({
  id,
  panel,
  loading,
  refresh,
}: {
  id: PanelId;
  panel?: Panel | IndicatorPanel;
  loading: boolean;
  refresh: () => Promise<void>;
}) {
  const [attempt, setAttempt] = useState(0);
  // A retry creates a new React.lazy identity; rejected import promises are otherwise cached.
  const { Gdp, Indicator } = useMemo(
    () => ({
      Gdp: lazy(() => import('./GdpPanel').then((m) => ({ default: m.GdpPanel }))),
      Indicator: lazy(() => import('./IndicatorPanel').then((m) => ({ default: m.IndicatorPanel }))),
    }),
    [attempt],
  );
  return (
    <RecoveryBoundary
      key={attempt}
      label={titles[id][1]}
      retry={() => {
        void refresh().then(() => setAttempt((n) => n + 1));
      }}
    >
      <Suspense fallback={<PanelLoading id={id} />}>
        {panel ? (
          panel.id === 'gdp' ? (
            <Gdp panel={panel} loading={false} />
          ) : (
            <Indicator panel={panel} />
          )
        ) : loading ? (
          <PanelLoading id={id} />
        ) : (
          <section className="panel" aria-labelledby={`${id}-title`}>
            <PanelHeading id={id} loading={false} />
            <div className="unavailable-chart">
              <span>—</span>
              <p>Connect to the API to load stored observations.</p>
            </div>
          </section>
        )}
      </Suspense>
    </RecoveryBoundary>
  );
}

const order: PanelId[] = ['gdp', 'debt', 'trade', 'gst', 'inflation', 'expenditure'];
export function App() {
  const [, redraw] = useState(0);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [owner, setOwner] = useState<string | null>(null);
  const pending = useRef<Promise<void> | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const ownerRef = useRef<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  useEffect(
    () =>
      auth.subscribe(() => {
        const next = auth.state === 'signed-in' ? auth.tokens?.user.id || null : null;
        if (next !== ownerRef.current) {
          controllerRef.current?.abort();
          controllerRef.current = null;
          pending.current = null;
          ownerRef.current = next;
          setDashboard(null);
          setOwner(null);
          setError('');
          setBusy(false);
        }
        redraw((n) => n + 1);
      }),
    [],
  );
  useEffect(() => {
    void auth.bootstrap();
  }, []);
  const signedIn = auth.state === 'signed-in';
  const userId = auth.tokens?.user.id;
  const ticker = useTicker(signedIn, userId);
  const [scale, setScale] = useState(() => (innerWidth > 760 ? Math.min(innerWidth, 1248) / 1248 : 1));
  const wrap = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const observer = new ResizeObserver(([e]) =>
      setScale(innerWidth > 760 ? Math.min(e.contentRect.width, 1248) / 1248 : 1),
    );
    if (wrap.current) observer.observe(wrap.current);
    return () => observer.disconnect();
  }, []);
  const load = useCallback((): Promise<void> => {
    if (pending.current) return pending.current;
    if (auth.state !== 'signed-in') return Promise.resolve();
    const user = auth.tokens?.user.id || null;
    const controller = new AbortController();
    controllerRef.current = controller;
    setBusy(true);
    const request = (async () => {
      try {
        const result = await auth.read<Dashboard>('/api/v1/dashboard', controller.signal);
        if (result.schema_version !== '1' || !Array.isArray(result.panels))
          throw new Error('The dashboard response is incompatible. Please retry.');
        if (!controller.signal.aborted && auth.state === 'signed-in' && auth.tokens?.user.id === user) {
          setDashboard(result);
          setOwner(user);
          setError('');
        }
      } catch (e) {
        if (!controller.signal.aborted) setError((e as Error).message);
      } finally {
        if (controllerRef.current === controller) {
          setBusy(false);
          pending.current = null;
        }
      }
    })();
    pending.current = request;
    return request;
  }, []);
  useEffect(() => {
    if (!signedIn) return;
    void load();
    const poll = () => {
      if (!document.hidden) void load();
    };
    const timer = window.setInterval(poll, 60000);
    document.addEventListener('visibilitychange', poll);
    window.addEventListener('online', poll);
    return () => {
      controllerRef.current?.abort();
      controllerRef.current = null;
      pending.current = null;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', poll);
      window.removeEventListener('online', poll);
    };
  }, [signedIn, userId, load]);
  useEffect(() => {
    if (!signedIn) return;
    const timer = window.setInterval(() => {
      if (!document.hidden && auth.tokens && Date.parse(auth.tokens.access_expires_at) < Date.now() + 60000) {
        const session = auth.tokens.csrf_token;
        void auth.renew().catch((e) => {
          if (e.name !== 'AbortError' && auth.state === 'signed-in' && auth.tokens?.csrf_token === session)
            setError(e.message);
        });
      }
    }, 15000);
    return () => window.clearInterval(timer);
  }, [signedIn, userId]);
  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setLoginError('');
    const data = new FormData(event.currentTarget);
    try {
      await auth.login(String(data.get('username')), String(data.get('password')));
    } catch (e) {
      setLoginError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }
  async function signOut() {
    setLogoutError('');
    try {
      await auth.logout();
    } catch (e) {
      setLogoutError((e as Error).message);
    }
  }
  const visible = owner === userId ? dashboard : null;
  return (
    <div
      className="app-shell canvas-wrap"
      ref={wrap}
      style={{ '--design-scale': scale } as React.CSSProperties}
    >
      <div className={`reference-canvas ${signedIn ? 'authenticated' : ''}`}>
        <img
          src={layout.canvas.src}
          srcSet={layout.canvas.srcSet}
          className="canvas-skin"
          alt=""
          aria-hidden="true"
          decoding="async"
        />
        <a className="skip-link" href="#main">
          Skip to dashboard
        </a>
        <header className="masthead">
          <h1 className="sr-only">ECONOMIC INDICATOR</h1>
          <div className="account">
            {signedIn ? (
              <>
                <span>{auth.tokens?.user.username}</span>
                <button
                  onClick={() => {
                    void load();
                    void ticker.reload();
                  }}
                  disabled={busy}
                  aria-label="Refresh stored dashboard data"
                >
                  {busy ? 'Updating…' : '↻ Refresh view'}
                </button>
                <button onClick={() => void signOut()}>Sign out ↗</button>
              </>
            ) : (
              <span>Secure access</span>
            )}
          </div>
        </header>
        <Ticker
          key={signedIn ? auth.tokens?.csrf_token : 'signed-out'}
          signedIn={signedIn}
          items={signedIn ? ticker.snapshot?.ticker || visible?.ticker || [] : []}
          error={ticker.error}
          retry={ticker.reload}
        />
        {logoutError && (
          <p className="global-error" role="alert">
            {logoutError}
          </p>
        )}
        {!signedIn ? (
          <main id="main" className="login-layout">
            <div className="login-intro">
              <span className="section-kicker">YOUR ECONOMIC OBSERVATORY</span>
              <h2>
                Perspective,
                <br />
                <em>grounded in data.</em>
              </h2>
              <p>
                Explore India’s growth alongside the world.
                <br />
                Clear periods. Traceable sources. One shared picture.
              </p>
              <div className="intro-rule" />
              <span className="intro-foot">
                WORLD BANK WDI <span>·</span> ANNUAL GDP GROWTH
              </span>
            </div>
            <section className="login-card" aria-labelledby="login-title">
              <span className="card-overline">MEMBER ACCESS</span>
              <h2 id="login-title">Welcome back</h2>
              <p>Sign in to your indicators dashboard.</p>
              {auth.state === 'checking' ? (
                <div className="session-check" role="status">
                  Restoring your session…
                </div>
              ) : auth.state === 'connection-error' ? (
                <div className="session-check">
                  <p role="alert">{auth.message}</p>
                  <button className="primary" onClick={() => void auth.bootstrap()}>
                    Retry connection
                  </button>
                </div>
              ) : (
                <form onSubmit={signIn}>
                  <label htmlFor="username">Username</label>
                  <input id="username" name="username" autoComplete="username" required maxLength={100} />
                  <label htmlFor="password">Password</label>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    maxLength={1024}
                  />
                  {loginError && (
                    <p role="alert" className="login-error">
                      {loginError}
                    </p>
                  )}
                  <button className="primary" disabled={submitting}>
                    {submitting ? 'Signing in…' : 'Sign in'}
                    <span aria-hidden="true">→</span>
                  </button>
                </form>
              )}
              <p className="login-security">◈ Your session stays signed in for up to seven days.</p>
            </section>
          </main>
        ) : (
          <main id="main" className="dashboard">
            <ReadNotice error={error} retained={!!visible} retry={() => void load()} />
            <div className="sr-only" role="status">
              {busy ? 'Updating stored dashboard data' : 'Dashboard view ready'}
            </div>
            <div className="panel-grid">
              {order.map((id) => (
                <PanelSlot
                  key={`${userId}-${id}`}
                  id={id}
                  panel={visible?.panels.find((p) => p.id === id)}
                  loading={!visible && busy}
                  refresh={load}
                />
              ))}
            </div>
          </main>
        )}
      </div>
    </div>
  );
}
