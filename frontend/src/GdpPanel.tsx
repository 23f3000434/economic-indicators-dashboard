import { useState } from 'react';
import { CanonicalChart } from './CanonicalChart';
import { change, ist, pointAt, type Panel } from './contracts';
import { Kpi, Legend, ObservationTable, PanelHeading } from './PanelParts';
import { gdpPoint, sliceSeries, type ViewSeries } from './presentation';

export function GdpPanel({ panel, loading }: { panel: Panel | null; loading: boolean }) {
  const [count, setCount] = useState(5);
  const [hidden, setHidden] = useState(new Set<string>());
  const toggle = (id: string) =>
    setHidden((old) => {
      const next = new Set(old);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const series: ViewSeries[] = (panel?.series || []).map((s, i) => ({
    id: s.id,
    label: s.label,
    unit: s.unit,
    color: i === 0 ? 'cyan' : 'amber',
    kind: 'bar',
    points: s.points.map((p) => gdpPoint(p, s)),
  }));
  const selected = sliceSeries(series, count);
  const visible = selected.filter((s) => !hidden.has(s.id));
  return (
    <section className="panel gdp-panel" aria-labelledby="gdp-title" aria-busy={loading}>
      <PanelHeading id="gdp" state={panel?.state} loading={loading} />
      <div className="panel-content">
        <div className="panel-notice" role="status">
          {panel?.state === 'stale'
            ? `Retained data · ${panel.collection.last_error_kind?.replaceAll('_', ' ') || 'collection needs attention'}.`
            : panel?.state === 'unavailable'
              ? 'Source unavailable; collection retries independently.'
              : loading
                ? 'Loading stored observations…'
                : 'Real annual growth · rates and changes use distinct units.'}
        </div>
        <div className="kpis">
          {series.map((s) => {
            const summary = panel?.summaries.find((p) => p.series_id === s.id);
            const point = s.points.find((p) => p.key === summary?.current_period_key);
            const sourceSeries = panel?.series.find((p) => p.id === s.id);
            const prior = sourceSeries && pointAt(sourceSeries, summary?.comparison_period_key || null);
            return (
              <Kpi
                key={s.id}
                label={s.label}
                series={s}
                point={point}
                delta={change(summary?.change.value, 'percentage_points')}
                comparison={`Change from ${prior?.period_label || 'previous year'} in percentage points`}
                image={s.id === 'gdp_india' ? 'india' : 'world'}
              />
            );
          })}
        </div>
        <div className="chart-controls">
          <span>Annual growth · %</span>
          <label>
            Window{' '}
            <select
              aria-label="GDP history window"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            >
              <option value={3}>Last 3 years</option>
              <option value={5}>Last 5 years</option>
              <option value={50}>All available years</option>
            </select>
          </label>
        </div>
        <Legend series={selected} hidden={hidden} toggle={toggle} />
        <CanonicalChart id="gdp" series={visible} />
        <p className="period-note">
          <b>FY</b> India: Apr–Mar · <b>CY</b> World: Jan–Dec aggregate.
          <br />
          Year ticks represent different windows; changes are in pp.
        </p>
        <ObservationTable
          id="GDP"
          rowHeading="Source year"
          rowLabel={(key) => key}
          series={visible.map((s) => ({ ...s, label: `${s.label} · ${s.id === 'gdp_india' ? 'FY' : 'CY'}` }))}
        />
        <div className="source-note">
          Source:{' '}
          <a
            href={panel?.series[0]?.source.url || 'https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG'}
            target="_blank"
            rel="noreferrer"
          >
            World Bank · WDI ↗
          </a>
          <br />
          Last collection: {ist(panel?.collection.last_success_at || null)}
        </div>
        <details className="provenance">
          <summary>Reporting & freshness details</summary>
          <p>
            Observation publication not supplied. Dataset update:{' '}
            {panel?.series[0]?.source.dataset_updated_on || '—'} (dataset level). Release freshness unknown.
            Last attempt {ist(panel?.collection.last_attempt_at || null)}.{' '}
            {panel?.collection.in_progress
              ? 'Collection in progress.'
              : 'Collection is independent of this page.'}
          </p>
          {panel?.notes.map((note) => (
            <p key={note}>{note}</p>
          ))}
        </details>
      </div>
    </section>
  );
}
