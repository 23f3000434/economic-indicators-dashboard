import { Component, useEffect, useState, type ReactNode } from 'react';
import { ist, published, type PanelId } from './contracts';
import { periodKeys, valueOf, type ViewPoint, type ViewSeries } from './presentation';
import { layout } from './layout';
import { artwork } from './artwork';

export const titles: Record<PanelId, [string, string, string]> = {
  gdp: ['01', 'GDP Growth - India vs World', '(YOY%)'],
  debt: ['02', 'Debt to GDP Ratio', 'India & US · general government'],
  trade: ['03', 'Imports, Exports & Trade Balance', 'Merchandise only · USD billion'],
  gst: ['04', 'GST Tax Collection', '(₹)'],
  inflation: ['05', 'Inflation', '(IND)'],
  expenditure: ['06', 'Government Expenditure', 'Union Government · actuals'],
};
export function PanelSkin({ id }: { id: PanelId }) {
  return (
    <picture>
      <source media="(max-width:760px)" srcSet={layout[id].mobileSrc || undefined} />
      <img
        src={layout[id].src}
        srcSet={layout[id].srcSet}
        className="panel-skin"
        alt=""
        aria-hidden="true"
        loading="lazy"
        decoding="async"
      />
    </picture>
  );
}
function MobileArt({ name }: { name: string }) {
  const [mobile, setMobile] = useState(() => matchMedia('(max-width:760px)').matches);
  useEffect(() => {
    const q = matchMedia('(max-width:760px)');
    const change = () => setMobile(q.matches);
    q.addEventListener('change', change);
    return () => q.removeEventListener('change', change);
  }, []);
  const source =
    (
      { exports: 'trade', imports: 'trade', total: 'expenditure', capital: 'expenditure' } as Record<
        string,
        string
      >
    )[name] || name;
  return mobile && artwork[source] ? (
    <span className={`card-art ${name}`} aria-hidden="true">
      <img {...artwork[source]} alt="" loading="lazy" decoding="async" />
    </span>
  ) : null;
}
export function PanelHeading({ id, state, loading }: { id: PanelId; state?: string; loading: boolean }) {
  const [, title] = titles[id];
  return (
    <div className="panel-heading">
      <div>
        <h2 id={`${id}-title`}>
          {title}
          {['gdp', 'gst', 'inflation'].includes(id) && (
            <span className="heading-suffix"> {titles[id][2]}</span>
          )}
          {id === 'debt' && <span className="heading-suffix"> (IND)</span>}
        </h2>
      </div>
      <span className={`status ${loading ? 'loading' : state || 'empty'}`}>
        {loading ? 'Loading' : state === 'ready' ? 'Stored data' : state || 'Offline'}
      </span>
    </div>
  );
}
export function PanelLoading({ id }: { id: PanelId }) {
  return (
    <section className={`panel ${id}-panel`} aria-labelledby={`${id}-title`} aria-busy="true">
      <PanelSkin id={id} />
      <PanelHeading id={id} loading />
      <div className="panel-content skeleton-layout" role="status">
        <div className="kpis">
          <div className="kpi skeleton" />
          <div className="kpi skeleton" />
        </div>
        <div className="chart-skeleton skeleton">Loading stored observations…</div>
      </div>
    </section>
  );
}
export function ReadNotice({
  error,
  retained,
  retry,
}: {
  error: string;
  retained: boolean;
  retry: () => void;
}) {
  return error ? (
    <div className="notice error" role="alert">
      {retained ? 'Connection lost. Showing the last loaded data. ' : ''}
      {error}
      <button onClick={retry}>Retry connection</button>
    </div>
  ) : null;
}
export function Kpi({
  label,
  point,
  series,
  delta,
  comparison,
  image,
  children,
}: {
  label: string;
  point?: ViewPoint;
  series: ViewSeries;
  delta?: string;
  comparison?: string;
  image?: string;
  children?: ReactNode;
}) {
  return (
    <article className={`kpi ${series.color} ${image || ''}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" data-testid={`card-${series.id}`}>
        {(() => {
          const text = valueOf(point, series);
          const parts = text.match(/^(.*?)( L cr| B)$/);
          return parts ? (
            <>
              {parts[1]}
              <span className="kpi-unit">{parts[2]}</span>
            </>
          ) : (
            text
          );
        })()}
      </div>
      <div className="kpi-foot">
        {image && <MobileArt name={image} />}
        <span className="card-period" title={point?.label}>
          {point?.label || 'Reporting period —'}
          {point?.status === 'estimate' ? ' · est.' : ''}
        </span>
        {delta && (
          <span
            className={`change ${delta.startsWith('-') ? 'negative' : ''}`}
            title={comparison}
            aria-label={`${delta}. ${comparison || 'Comparison unavailable'}`}
          >
            <span aria-hidden="true">{delta.startsWith('-') ? '▼ ' : delta.startsWith('+') ? '▲ ' : ''}</span>
            {delta}
          </span>
        )}
      </div>
      {children}
      <span className="kpi-retained">
        {point?.retained ? 'Retained observation' : point?.status === 'provisional' ? 'Provisional' : ''}
      </span>
    </article>
  );
}
export function Legend({
  series,
  hidden,
  toggle,
}: {
  series: ViewSeries[];
  hidden: Set<string>;
  toggle: (id: string) => void;
}) {
  const plotted = series.filter((s) => s.plot !== false);
  return (
    <div className="legend" role="group" aria-label="Visible series in chart and table">
      {plotted.map((s) => (
        <button
          key={s.id}
          aria-pressed={!hidden.has(s.id)}
          onClick={() => toggle(s.id)}
          disabled={!hidden.has(s.id) && plotted.filter((p) => !hidden.has(p.id)).length === 1}
        >
          <i className={`dot ${s.color} ${s.kind === 'line' ? 'line-marker' : ''}`} />
          {s.label}
        </button>
      ))}
    </div>
  );
}
export function PointDetails({ p, series }: { p?: ViewPoint; series: ViewSeries }) {
  return (
    <div>
      <span className={`dot ${series.color}`} />
      {series.label}
      <b>{valueOf(p, series)}</b>
      <small>
        {p?.label || 'Missing observation'} · {p?.start} → {p?.end}
        {p?.retained ? ' · retained' : ''}
      </small>
      <small>
        {p?.status || 'Unspecified'} · {p?.methodology.replaceAll('_', ' ')}
      </small>
      <small>
        Published {published(p?.published || null)} · Retrieved {ist(p?.retrieved || null)}
        {p?.source ? ` · ${new URL(p.source).hostname}` : ''}
      </small>
      {p?.note && <small>{p.note}</small>}
    </div>
  );
}
export function ObservationTable({
  id,
  series,
  keys = periodKeys(series),
  rowHeading = 'Reporting period',
  rowLabel,
}: {
  id: string;
  series: ViewSeries[];
  keys?: string[];
  rowHeading?: string;
  rowLabel?: (key: string) => string;
}) {
  return (
    <div className="observations" tabIndex={0} role="region" aria-label={`${id} observations table`}>
      <table>
        <caption className="sr-only">
          Canonical {id} values; same units and selection as the chart. Missing observations are dashes;
          retained observations are marked.
        </caption>
        <thead>
          <tr>
            <th scope="col">{rowHeading}</th>
            {series.map((s) => (
              <th scope="col" key={s.id}>
                {s.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...keys].reverse().map((key) => (
            <tr key={key}>
              <th scope="row">
                {rowLabel
                  ? rowLabel(key)
                  : series.flatMap((s) => s.points).find((p) => p.key === key)?.label || key}
              </th>
              {series.map((s) => {
                const p = s.points.find((p) => p.key === key);
                const meta = `${p?.label || key}, ${p?.start || '—'} to ${p?.end || '—'}. ${p?.status || 'Unspecified'}. ${p?.methodology.replaceAll('_', ' ') || ''}. Published ${published(p?.published || null)}. Retrieved ${ist(p?.retrieved || null)}.${p?.retained ? ' Retained observation.' : ''}`;
                return (
                  <td
                    key={s.id}
                    data-testid={`table-${s.id}-${key}`}
                    title={meta}
                    aria-label={`${valueOf(p, s)}. ${meta}`}
                  >
                    {valueOf(p, s)}
                    {p?.retained && <span aria-label="retained"> *</span>}
                  </td>
                );
              })}
            </tr>
          ))}
          {!keys.length && (
            <tr>
              <td colSpan={series.length + 1}>— No stored observations</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
export class RecoveryBoundary extends Component<
  { children: ReactNode; retry?: () => void; label?: string },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <section className="panel recovery" role="alert">
          <h2>{this.props.label || 'Dashboard'} could not open</h2>
          <p>
            A component or downloaded module failed. Retry the latest data, or reload to retrieve application
            files. Other panels can continue.
          </p>
          <button
            onClick={() => {
              this.setState({ failed: false });
              this.props.retry?.();
            }}
          >
            Retry panel
          </button>
          <button onClick={() => window.location.reload()}>Reload application</button>
        </section>
      );
    return this.props.children;
  }
}
