import { useState } from 'react';
import { CanonicalChart } from './CanonicalChart';
import { change, ist, pointAt, type Panel } from './contracts';
import { Details } from './Details';
import { Kpi, Legend, ObservationTable, PanelHeading, PanelSkin } from './PanelParts';
import { gdpPoint, sliceSeries, type ViewSeries } from './presentation';

export function GdpPanel({ panel, loading }: { panel: Panel | null; loading: boolean }) {
  const [count, setCount] = useState(5);
  const [hidden, setHidden] = useState(new Set<string>());
  const toggle = (id: string) =>
    setHidden((old) => {
      const n = new Set(old);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  const series: ViewSeries[] = (panel?.series || []).map((s, i) => ({
    id: s.id,
    label: i === 0 ? 'India' : 'World',
    unit: s.unit,
    color: i === 0 ? 'cyan' : 'amber',
    kind: 'bar',
    points: s.points.map((p) => gdpPoint(p, s)),
  }));
  const selected = sliceSeries(series, count),
    visible = selected.filter((s) => !hidden.has(s.id));
  return (
    <section className="panel gdp-panel" aria-labelledby="gdp-title" aria-busy={loading}>
      <PanelSkin id="gdp" />
      <PanelHeading id="gdp" state={panel?.state} loading={loading} />
      <div className="panel-content">
        <div className={`panel-notice ${panel?.state === 'stale' ? 'warning' : ''}`} role="status">
          {panel?.state === 'stale'
            ? `Retained data · ${panel.collection.last_error_kind?.replaceAll('_', ' ') || 'collection needs attention'}`
            : panel?.state === 'unavailable'
              ? 'Source unavailable; retrying independently.'
              : loading
                ? 'Loading stored observations…'
                : ''}
        </div>
        <div className="kpis">
          {series.map((s) => {
            const summary = panel?.summaries.find((p) => p.series_id === s.id);
            const point = s.points.find((p) => p.key === summary?.current_period_key);
            const source = panel?.series.find((p) => p.id === s.id);
            const prior = source && pointAt(source, summary?.comparison_period_key || null);
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
        <Legend series={selected} hidden={hidden} toggle={toggle} />
        <CanonicalChart id="gdp" series={visible} />
        <div className="source-note">
          World Bank WDI · India FY / World CY · updated {panel?.series[0]?.source.dataset_updated_on || '—'}
        </div>
        <Details label="GDP reporting and data">
          <div className="chart-controls">
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
          <p>
            India: April–March fiscal years. World: January–December calendar aggregate. Year ticks identify
            the source year; these windows differ. Annual real growth in %, changes in percentage points.
          </p>
          <ObservationTable
            id="GDP"
            rowHeading="Source year"
            rowLabel={(key) => key}
            series={visible.map((s) => ({
              ...s,
              label: `${s.label} · ${s.id === 'gdp_india' ? 'FY' : 'CY'}`,
            }))}
          />
          <div className="provenance">
            <p>
              Source:{' '}
              <a
                href={
                  panel?.series[0]?.source.url || 'https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG'
                }
                target="_blank"
                rel="noreferrer"
              >
                World Bank WDI ↗
              </a>
              . Dataset update: {panel?.series[0]?.source.dataset_updated_on || '—'}. Individual publication
              date not supplied; release freshness unknown.
            </p>
            <p>
              Last collection: {ist(panel?.collection.last_success_at || null)}. Last attempt:{' '}
              {ist(panel?.collection.last_attempt_at || null)}.
              {panel?.collection.in_progress ? ' Collection in progress.' : ''}
            </p>
            {panel?.notes.map((n) => (
              <p key={n}>{n}</p>
            ))}
          </div>
        </Details>
      </div>
    </section>
  );
}
