import { useCallback, useEffect, useRef, useState } from 'react';
import { auth } from './auth';
import { change, exchangeTime, ist, metric, type TickerItem, type TickerSnapshot } from './contracts';
import { Details } from './Details';

export function useTicker(signedIn: boolean, userId: string | undefined) {
  const sessionKey = auth.tokens?.csrf_token || null;
  const [result, setResult] = useState<{
    user: string | null;
    session: string | null;
    data: TickerSnapshot | null;
    error: string;
  }>({
    user: null,
    session: null,
    data: null,
    error: '',
  });
  const pending = useRef<Promise<void> | null>(null),
    controller = useRef<AbortController | null>(null);
  const load = useCallback(() => {
    if (pending.current) return pending.current;
    if (auth.state !== 'signed-in') return Promise.resolve();
    const user = auth.tokens?.user.id || null,
      session = auth.tokens?.csrf_token || null,
      abort = new AbortController();
    controller.current = abort;
    const request = (async () => {
      try {
        const data = await auth.read<TickerSnapshot>('/api/v1/ticker', abort.signal);
        if (data.schema_version !== '1' || !Array.isArray(data.ticker))
          throw new Error('Incompatible ticker response.');
        if (
          !abort.signal.aborted &&
          auth.state === 'signed-in' &&
          auth.tokens?.user.id === user &&
          auth.tokens?.csrf_token === session
        )
          setResult({ user, session, data, error: '' });
      } catch (e) {
        if (
          !abort.signal.aborted &&
          (e as Error).name !== 'AbortError' &&
          auth.state === 'signed-in' &&
          auth.tokens?.user.id === user &&
          auth.tokens?.csrf_token === session
        )
          setResult((old) => ({
            user,
            session,
            data: old.user === user && old.session === session ? old.data : null,
            error: (e as Error).message,
          }));
      } finally {
        if (controller.current === abort) {
          controller.current = null;
          pending.current = null;
        }
      }
    })();
    pending.current = request;
    return request;
  }, []);
  useEffect(() => {
    if (!signedIn) {
      setResult({ user: null, session: null, data: null, error: '' });
      return;
    }
    void load();
    const poll = () => {
      if (!document.hidden) void load();
    };
    const timer = window.setInterval(poll, 30000);
    window.addEventListener('online', poll);
    document.addEventListener('visibilitychange', poll);
    return () => {
      controller.current?.abort();
      controller.current = null;
      pending.current = null;
      window.clearInterval(timer);
      window.removeEventListener('online', poll);
      document.removeEventListener('visibilitychange', poll);
    };
  }, [signedIn, userId, sessionKey, load]);
  return {
    snapshot: result.user === userId && result.session === sessionKey ? result.data : null,
    error: result.user === userId && result.session === sessionKey ? result.error : '',
    reload: load,
  };
}
export function Ticker({
  items,
  error,
  retry,
  signedIn,
}: {
  items: TickerItem[];
  error: string;
  retry: () => Promise<void>;
  signedIn: boolean;
}) {
  const allClosed = items.length === 3 && items.every((t) => t.state === 'closed');
  return (
    <div className="market-strip" aria-label="Market snapshots">
      <Details
        label="Market quote sources and timestamps"
        className={`market-badge ${allClosed ? 'closed' : ''}`}
        button={allClosed && !error ? 'CLOSED' : 'QUOTES'}
      >
        {error && (
          <p role="alert">
            Market connection lost; retained snapshots. {error}
            <button onClick={() => void retry()}>Retry market connection</button>
          </p>
        )}
        <p>
          Previous-close comparisons are calculated by the API. Quote time, provider response time and
          collection time refer to different events. NSE snapshots have no verified latency guarantee. No
          changes are simulated.
        </p>
        {!items.length && <p>No stored market snapshots.</p>}
        {items.map((t) => (
          <section key={t.id}>
            <h3>
              {t.label} · {error ? 'stale' : t.state}
            </h3>
            <p>
              {metric(t.value, '')} points · {change(t.change_percent, 'relative_percent')} versus previous
              close {metric(t.previous_close, '')}. Point change: {metric(t.change_points, '')}.
            </p>
            <p>
              Exchange timestamp: {exchangeTime(t.exchange_timestamp, t.exchange_timestamp_precision)} (
              {t.exchange_timestamp_precision || '—'} precision). Provider response:{' '}
              {ist(t.provider_timestamp)}. Collected: {ist(t.retrieved_at)}.
            </p>
            <p>
              Market {t.market_state}; status transition {ist(t.market_status_at)}, checked{' '}
              {ist(t.market_status_checked_at)}. Verified regular close: {ist(t.market_session_close_at)}.
            </p>
            <p>
              Previous-close basis: {t.previous_close_basis?.replaceAll('_', ' ') || '—'}.{' '}
              {t.error_kind?.replaceAll('_', ' ')}
              {t.retained ? ' · retained observation' : ''}
            </p>
            {t.source_url && (
              <p>
                <a href={t.source_url} target="_blank" rel="noreferrer">
                  {t.exchange} via {t.provider_id.toUpperCase()} ↗
                </a>
              </p>
            )}
          </section>
        ))}
      </Details>
      <div
        className="ticker-track"
        tabIndex={0}
        role="region"
        aria-label="Exchange quotes; scroll horizontally for more"
      >
        {[...items, ...items].map((t, i) => (
          <span
            className={`ticker-item ${error ? 'stale' : t.state}`}
            key={`${t.id}-${i}`}
            aria-hidden={i >= items.length ? true : undefined}
          >
            <span>
              <b className={t.id === 'nifty_bank' ? 'manrope' : ''}>{t.label}</b>{' '}
              <strong className={t.change_percent?.startsWith('-') ? 'down' : 'up'}>
                {metric(t.value, '')} ({change(t.change_percent, 'relative_percent')})
              </strong>
            </span>
            <small>
              {t.exchange}
              {t.provider_id === 'upstox' ? ' / Upstox' : ''} ·{' '}
              {error ? 'STALE · connection lost' : t.state.toUpperCase()} ·{' '}
              {exchangeTime(t.exchange_timestamp, t.exchange_timestamp_precision)}
            </small>
          </span>
        ))}
        {!items.length && (
          <span className="ticker-empty">
            NSE / BSE · — · {signedIn ? 'Loading stored quotes' : 'Sign in to view market snapshots'}
          </span>
        )}
      </div>
    </div>
  );
}
