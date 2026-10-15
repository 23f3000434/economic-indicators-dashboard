import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ist, metric, plotValue, pointAt, type Panel } from './contracts';

function Detail({ panel, year }: { panel: Panel; year: string }) {
  return (
    <div className="chart-tooltip">
      <strong>Reporting year {year}</strong>
      {panel.series.map((series) => {
        const point = pointAt(series, year);
        return (
          <div key={series.id}>
            <span className={`dot ${series.id}`} />
            {series.label} · {point?.period_label}
            <b>{metric(point?.value)}</b>
            <small>
              {point?.period_start} → {point?.period_end}
              {point?.retained ? ' · retained' : ''}
            </small>
          </div>
        );
      })}
    </div>
  );
}

export function GdpPanel({
  panel,
  error,
  loading,
  retry,
}: {
  panel: Panel | null;
  error: string;
  loading: boolean;
  retry: () => void;
}) {
  const chart =
    panel?.series[0]?.points.map((point) => ({
      year: point.period_key,
      ...Object.fromEntries(
        panel.series.map((series) => [series.id, plotValue(pointAt(series, point.period_key))]),
      ),
    })) || [];
  return (
    <section className="panel gdp-panel" aria-labelledby="gdp-title" aria-busy={loading}>
      <div className="panel-heading">
        <div>
          <span className="panel-number">01</span>
          <h2 id="gdp-title">
            GDP Growth <span>India vs World</span>
          </h2>
        </div>
        <span className={`status ${panel?.state || 'loading'}`}>
          {loading ? 'Loading' : panel?.state === 'ready' ? 'Stored data' : panel?.state || 'Offline'}
        </span>
      </div>
      <div className="gdp-content">
        {error && (
          <div role="alert" className="notice error">
            {panel ? 'Connection lost. Showing the last loaded data. ' : ''}
            {error}
            <button onClick={retry}>Retry connection</button>
          </div>
        )}
        {panel?.state === 'stale' && (
          <div role="status" className="notice warning">
            Retained data ·{' '}
            {panel.collection.last_error_kind?.replaceAll('_', ' ') || 'collection needs attention'}. Last
            successful collection: {ist(panel.collection.last_success_at)}.
          </div>
        )}
        <div className="kpis">
          {(panel?.series || [null, null]).map((series, index) => {
            const summary = panel?.summaries.find((s) => s.series_id === series?.id);
            const current = series && summary ? pointAt(series, summary.current_period_key) : null;
            const comparison = series && summary ? pointAt(series, summary.comparison_period_key) : null;
            const change = summary?.change.value;
            return (
              <article className={`kpi ${index === 0 ? 'india' : 'world'}`} key={series?.id || index}>
                <div className="kpi-label">
                  <span aria-hidden="true">{index === 0 ? '🇮🇳' : '◎'}</span>
                  {series?.label || (index === 0 ? 'India' : 'World')}
                  <small>Annual real growth</small>
                </div>
                <div className="kpi-value" data-testid={`card-${series?.id || index}`}>
                  {loading && !panel ? <span className="skeleton value-skeleton" /> : metric(current?.value)}
                </div>
                <div className="kpi-foot">
                  <span>{current?.period_label || 'Reporting period —'}</span>
                  <span
                    className={`change ${change != null && Number(change) < 0 ? 'negative' : ''}`}
                    title={`Change from ${comparison?.period_label || 'previous year'}`}
                    aria-label={`Change from ${comparison?.period_label || 'previous year'}: ${metric(change, ' percentage points')}`}
                  >
                    {change != null && Number(change) > 0 ? '+' : ''}
                    {metric(change, ' pp')}
                  </span>
                </div>
              </article>
            );
          })}
        </div>
        <div className="chart-caption">
          <span>
            ANNUAL GROWTH <b>%</b>
          </span>
          <div>
            <span className="dot gdp_india" />
            India <span className="dot gdp_world" />
            World
          </div>
        </div>
        <div className="chart-space" data-testid="gdp-chart">
          {loading && !panel ? (
            <div className="chart-skeleton skeleton">
              <span>Loading stored observations…</span>
            </div>
          ) : panel && chart.length ? (
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <BarChart data={chart} margin={{ top: 10, right: 4, bottom: 0, left: -20 }} barGap={5}>
                <defs>
                  <linearGradient id="india-bar" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#39d6ff" />
                    <stop offset="100%" stopColor="#14749d" />
                  </linearGradient>
                  <linearGradient id="world-bar" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f9c66d" />
                    <stop offset="100%" stopColor="#ad742c" />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#334055" strokeDasharray="3 5" />
                <XAxis
                  dataKey="year"
                  tick={{ fill: '#b0bdcf', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#91a3bb', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  unit="%"
                  width={48}
                />
                <ReferenceLine y={0} stroke="#718198" />
                <Tooltip
                  cursor={{ fill: '#ffffff06' }}
                  content={({ active, label }) =>
                    active ? <Detail panel={panel} year={String(label)} /> : null
                  }
                />
                <Bar
                  dataKey="gdp_india"
                  name="India"
                  fill="url(#india-bar)"
                  radius={[3, 3, 0, 0]}
                  maxBarSize={26}
                  isAnimationActive={false}
                />
                <Bar
                  dataKey="gdp_world"
                  name="World"
                  fill="url(#world-bar)"
                  radius={[3, 3, 0, 0]}
                  maxBarSize={26}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">
              <span>—</span>
              {panel?.state === 'unavailable'
                ? 'Source unavailable. Collection will retry independently.'
                : 'No stored observations yet. Collection runs independently.'}
            </div>
          )}
        </div>
        <p className="period-note">
          <span>FY</span> India: Apr–Mar <i /> <span>CY</span> World: Jan–Dec aggregate
          <br />
          <small>Year ticks identify different reporting windows. Δ compares rates in pp.</small>
        </p>
        <div className="observations" tabIndex={0} aria-label="GDP observations table">
          <table>
            <caption className="sr-only">
              Canonical GDP observations. Missing values are shown as a dash.
            </caption>
            <thead>
              <tr>
                <th scope="col">Source year</th>
                <th scope="col">India · FY</th>
                <th scope="col">World · CY</th>
              </tr>
            </thead>
            <tbody>
              {chart.map((row) => (
                <tr key={row.year}>
                  <th scope="row">{row.year}</th>
                  {panel?.series.map((series) => {
                    const point = pointAt(series, row.year);
                    return (
                      <td
                        key={series.id}
                        data-testid={`table-${series.id}-${row.year}`}
                        title={`${point?.period_label}: ${point?.period_start} to ${point?.period_end}. Retrieved ${ist(point?.retrieved_at || null)}${point?.retained ? '. Retained from earlier collection' : ''}`}
                      >
                        {metric(point?.value)}
                        {point?.retained && <span aria-label="retained"> *</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
              {!chart.length && (
                <tr>
                  <td colSpan={3}>—</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="source-note">
          <div>
            Source:{' '}
            <a href="https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG" target="_blank" rel="noreferrer">
              World Bank · WDI ↗
            </a>
            <span>NY.GDP.MKTP.KD.ZG</span>
          </div>
          <div>
            Collected <time>{ist(panel?.collection.last_success_at || null)}</time>
          </div>
        </div>
        <details className="provenance">
          <summary>Reporting & freshness details</summary>
          <p>
            Release freshness is unknown. Dataset update: {panel?.series[0]?.source.dataset_updated_on || '—'}{' '}
            (dataset level). Observation publication: not supplied. Last attempt:{' '}
            {ist(panel?.collection.last_attempt_at || null)}. Collection is{' '}
            {panel?.collection.in_progress ? 'in progress' : 'independent of this page'}.
          </p>
          <p>
            Provider observation status is unspecified when blank. Per-point provenance is available in the
            table tooltips and API.
          </p>
        </details>
      </div>
    </section>
  );
}
