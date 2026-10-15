import { lazy, Suspense, useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { auth } from './auth';
import type { Panel } from './contracts';
const GdpPanel = lazy(() => import('./GdpPanel').then((module) => ({ default: module.GdpPanel })));

const remaining = [
  ['02', 'Debt to GDP', 'India & US comparison', 'Annual public debt'],
  ['03', 'Trade Balance', 'Exports & imports', 'Merchandise trade'],
  ['04', 'GST Collection', 'Revenue & monthly average', 'Goods & services tax'],
  ['05', 'Inflation', 'India CPI & policy target', 'Consumer prices'],
  ['06', 'Government Expenditure', 'Revenue & capital', 'Union government actuals'],
];

export function App() {
  const [, redraw] = useState(0);
  const [panel, setPanel] = useState<Panel | null>(null);
  const [panelOwner, setPanelOwner] = useState<string | null>(null);
  const pendingRead = useRef<Promise<void> | null>(null);
  const readController = useRef<AbortController | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loginError, setLoginError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  useEffect(() => auth.subscribe(() => redraw((n) => n + 1)), []);
  useEffect(() => {
    void auth.bootstrap();
  }, []);
  const signedIn = auth.state === 'signed-in';
  const userId = auth.tokens?.user.id;
  const load = useCallback((): Promise<void> => {
    if (pendingRead.current) return pendingRead.current;
    const owner = auth.tokens?.user.id || null;
    const controller = new AbortController();
    readController.current = controller;
    setBusy(true);
    pendingRead.current = (async () => {
      try {
        const result = await auth.read<Panel>('/api/v1/panels/gdp', controller.signal);
        if (!controller.signal.aborted && auth.tokens?.user.id === owner) {
          setPanel(result);
          setPanelOwner(owner);
          setError('');
        }
      } catch (e) {
        if (!controller.signal.aborted) setError((e as Error).message);
      } finally {
        if (readController.current === controller) {
          setBusy(false);
          pendingRead.current = null;
        }
      }
    })();
    return pendingRead.current;
  }, []);
  useEffect(() => {
    if (!signedIn) {
      readController.current?.abort();
      pendingRead.current = null;
      setPanel(null);
      setPanelOwner(null);
      setError('');
      return;
    }
    let active = true;
    let pending = false;
    const poll = async () => {
      if (!active || pending || document.hidden) return;
      pending = true;
      await load();
      pending = false;
    };
    void poll();
    const interval = window.setInterval(() => {
      void poll();
    }, 60000);
    const visible = () => {
      if (!document.hidden) void poll();
    };
    document.addEventListener('visibilitychange', visible);
    return () => {
      active = false;
      readController.current?.abort();
      pendingRead.current = null;
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', visible);
    };
  }, [signedIn, userId, load]);
  useEffect(() => {
    if (!signedIn) return;
    const timer = window.setInterval(() => {
      if (!document.hidden && auth.tokens && Date.parse(auth.tokens.access_expires_at) < Date.now() + 60000) {
        void auth.renew().catch((e) => setError(e.message));
      }
    }, 15000);
    return () => window.clearInterval(timer);
  }, [signedIn]);
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
  return (
    <div className="app-shell">
      <header className="masthead">
        <div className="brand-mark" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </div>
        <div>
          <p className="eyebrow">THE ECONOMIC PICTURE</p>
          <h1>ECONOMIC INDICATOR</h1>
          <p className="tagline">A clearer view of the numbers that shape India.</p>
        </div>
        <div className="account">
          {signedIn ? (
            <>
              <span className="account-dot" />
              {auth.tokens?.user.username}
              <button onClick={() => void signOut()}>Sign out ↗</button>
            </>
          ) : (
            <span className="secure-label">◈ Secure dashboard</span>
          )}
        </div>
      </header>
      <div className="market-strip">
        <span className="strip-label">MARKET PULSE</span>
        <div>
          <span className="muted-dot" />
          Market feed pending access verification
        </div>
        <span className="strip-end">NSE / BSE · —</span>
      </div>
      {logoutError && (
        <p className="global-error" role="alert">
          {logoutError}
        </p>
      )}
      {!signedIn ? (
        <main className="login-layout">
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
        <main className="dashboard">
          <div className="dashboard-intro">
            <div>
              <span className="section-kicker">MACROECONOMIC OVERVIEW</span>
              <p>
                India, in context<span>Annual observations · stored independently</span>
              </p>
            </div>
            <button onClick={() => void load()} disabled={busy} aria-label="Refresh stored GDP data">
              {busy ? '↻ Updating…' : '↻ Refresh view'}
            </button>
          </div>
          <div className="panel-grid">
            <Suspense
              fallback={
                <section className="panel gdp-placeholder" aria-label="GDP loading">
                  <div className="panel-heading">
                    <h2>GDP Growth · India vs World</h2>
                  </div>
                  <div className="gdp-content skeleton" role="status">
                    Loading GDP panel…
                  </div>
                </section>
              }
            >
              <GdpPanel
                panel={panelOwner === userId ? panel : null}
                error={error}
                loading={busy && !panel}
                retry={() => void load()}
              />
            </Suspense>
            {remaining.map(([number, title, subtitle, caption]) => (
              <section className="panel reserved-panel" key={number} aria-label={`${title} — reserved`}>
                <div className="panel-heading">
                  <div>
                    <span className="panel-number">{number}</span>
                    <h2>
                      {title}
                      <span>{subtitle}</span>
                    </h2>
                  </div>
                  <span className="status reserved">Reserved</span>
                </div>
                <div className="reserved-content">
                  <div className="reserved-motif" aria-hidden="true">
                    <i />
                    <i />
                    <i />
                    <i />
                    <i />
                  </div>
                  <span className="reserved-value">—</span>
                  <h3>{caption}</h3>
                  <p>
                    This panel is reserved for the next stage.
                    <br />
                    No observations are connected.
                  </p>
                  <span className="reserved-tag">SOURCE VERIFICATION PENDING</span>
                </div>
              </section>
            ))}
          </div>
        </main>
      )}
      <footer>
        <span>ECONOMIC INDICATOR</span>
        <p>Public data. Explicit periods. Informed perspective.</p>
        <span>GDP SLICE · 01 / 06</span>
      </footer>
    </div>
  );
}
