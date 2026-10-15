import { useState } from 'react';
import { CanonicalChart } from './CanonicalChart';
import {
  amount,
  change,
  ist,
  policyFor,
  published,
  resolve,
  summaryFor,
  type IndicatorPanel as Panel,
  type PeriodKind,
} from './contracts';
import { Kpi, Legend, ObservationTable, PanelHeading } from './PanelParts';
import { displayPoint, sliceSeries, type ViewSeries } from './presentation';

function spec(
  id: string,
  label: string,
  kind: ViewSeries['kind'],
  color: ViewSeries['color'],
  extra: Partial<ViewSeries> = {},
): ViewSeries {
  return {
    id,
    label,
    kind,
    color,
    unit: id.startsWith('trade')
      ? 'usd_billion'
      : id.startsWith('cpi') || id.startsWith('inflation')
        ? 'percent'
        : 'inr_crore',
    points: [],
    ...extra,
  };
}
const specs = {
  trade: [
    spec('trade_exports', 'Exports', 'bar', 'amber'),
    spec('trade_imports', 'Imports', 'bar', 'cyan'),
    spec('trade_balance', 'Balance', 'line', 'green', { signed: true }),
  ],
  expenditure: [
    spec('expenditure_revenue', 'Revenue actuals', 'bar', 'cyan', { stack: 'actual' }),
    spec('expenditure_capital', 'Capital actuals', 'bar', 'amber', { stack: 'actual' }),
    spec('expenditure_total', 'Total actuals', 'line', 'muted', { plot: false }),
  ],
  gst: [
    spec('gst_fy_total', 'Gross GST', 'bar', 'cyan'),
    spec('gst_fy_average', 'Monthly average', 'line', 'amber'),
  ],
};

export function IndicatorPanel({ panel }: { panel: Panel }) {
  const { id } = panel;
  const [grain, setGrain] = useState<PeriodKind>('fiscal_year');
  const [base, setBase] = useState('cpi_yoy_2024');
  const [count, setCount] = useState(12);
  const [hidden, setHidden] = useState(new Set<string>());
  const toggle = (id: string) =>
    setHidden((old) => {
      const next = new Set(old);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const isCpi = id === 'inflation';
  const periodKind = isCpi ? 'month' : grain;
  let series: ViewSeries[] =
    id === 'trade'
      ? specs.trade
      : id === 'expenditure'
        ? specs.expenditure
        : id === 'gst'
          ? grain === 'month'
            ? [spec('gst_gross_ex_cess', 'Gross GST', 'bar', 'cyan')]
            : grain === 'fiscal_year_to_date'
              ? [spec('gst_fytd_average', 'Published-month average', 'bar', 'cyan')]
              : specs.gst
          : isCpi
            ? [spec(base, base.endsWith('2024') ? 'CPI · base 2024' : 'CPI · base 2012', 'area', 'cyan')]
            : [];
  series = series.map((s) => ({
    ...s,
    points: (panel.series.find((p) => p.id === s.id)?.points || [])
      .filter((p) => p.period.kind === periodKind)
      .map(displayPoint),
  }));
  const cpiSummary = summaryFor(panel, base, 'month');
  const latestCpi = resolve(panel, cpiSummary?.current);
  const policy = latestCpi ? policyFor(panel, latestCpi.period) : undefined;
  if (isCpi) {
    const target = spec('inflation_target', 'Verified target', 'line', 'amber', { dashed: true });
    target.points = (panel.series.find((p) => p.id === base)?.points || [])
      .filter((p) => p.period.kind === 'month')
      .map((p) => {
        const applicable = policyFor(panel, p.period);
        const observation = resolve(panel, applicable?.target);
        // Repeated display coordinates reference the dated policy value; no monthly economic observations are invented.
        return {
          ...displayPoint(p),
          value: observation?.value || null,
          retained: observation?.retained || false,
          source: observation?.source_url || null,
          retrieved: observation?.retrieved_at || null,
          published: observation?.definition.published_at || null,
          status: observation?.definition.status || 'unspecified',
          methodology: observation?.definition.methodology || 'No verified policy for this period',
          note: applicable
            ? `Policy validity: ${applicable.validity.start} to ${applicable.validity.end}.`
            : 'No verified policy for this period.',
        };
      });
    series.push(target);
  }
  const selected = sliceSeries(series, isCpi || grain === 'month' ? count : panel.report_years);
  const visible = selected.filter((s) => !hidden.has(s.id));
  const cardIds =
    id === 'trade'
      ? ['trade_exports', 'trade_imports']
      : id === 'expenditure'
        ? ['expenditure_total', 'expenditure_capital']
        : id === 'gst'
          ? grain === 'fiscal_year'
            ? ['gst_fy_total', 'gst_fy_average']
            : grain === 'month'
              ? ['gst_gross_ex_cess']
              : ['gst_fytd_average']
          : isCpi
            ? [base]
            : [];
  const notices = panel.collection.filter((c) => c.last_error_kind);
  const publications = selected
    .flatMap((s) => s.points)
    .filter((p) => p.value !== null && p.published)
    .map((p) => p.published!)
    .sort();
  const latestPublication = publications.at(-1) || null;
  const sources = [
    ...new Set(
      selected
        .flatMap((s) => s.points)
        .filter((p) => p.value !== null && p.source)
        .map((p) => p.source!),
    ),
  ];
  const unitLabel =
    series[0]?.unit === 'percent' ? '%' : series[0]?.unit === 'usd_billion' ? 'USD billion' : '₹ lakh crore';
  const periodNote = isCpi
    ? `${base.endsWith('2024') ? '2024' : '2012'}=100 base · year-on-year rate. Monthly change is in pp. No bridge across bases.`
    : id === 'gst'
      ? 'Gross before refunds, excluding compensation cess. Averages use published months; full FY requires 12.'
      : id === 'trade'
        ? 'Merchandise only. Balance = exports − imports; deficits are negative. Comparisons use matching windows.'
        : 'April–March actual expenditure, unaudited/provisional. Revenue + capital = total; BE/RE excluded.';
  return (
    <section className={`panel ${id}-panel`} aria-labelledby={`${id}-title`}>
      <PanelHeading id={id} state={panel.state} loading={false} />
      <div className="panel-content">
        {id === 'debt' ? (
          <>
            <div className="panel-notice warning" role="status">
              Comparable source unavailable · access blocked
            </div>
            <div className="kpis">
              {['India', 'US'].map((name) => (
                <Kpi
                  key={name}
                  label={name}
                  series={spec(`debt_${name.toLowerCase()}`, name, 'line', 'cyan', { unit: 'percent' })}
                  image={name.toLowerCase()}
                />
              ))}
            </div>
            <div className="unavailable-chart">
              <span>—</span>
              <h3>Comparable government debt is unavailable</h3>
              <p>General-government gross debt / GDP · annual %</p>
              <p>
                IMF requests were rejected; the FRED alternative timed out.
                <br />
                No verified observations or comparison are supplied.
              </p>
            </div>
            <p className="period-note">
              Reporting basis, source vintage and estimate status await verification. No daily debt curve is
              inferred.
            </p>
            <details className="provenance">
              <summary>Source access & definition</summary>
              {panel.notes.map((n) => (
                <p key={n}>{n}</p>
              ))}
              {panel.coverage.map((n) => (
                <p key={n}>{n}</p>
              ))}
            </details>
          </>
        ) : (
          <>
            <div className={`panel-notice ${notices.length ? 'warning' : ''}`} role="status">
              {notices.length
                ? notices
                    .map(
                      (c) =>
                        `${c.group_id.replaceAll('_', ' ')} · retained data · ${c.last_error_kind?.replaceAll('_', ' ')}`,
                    )
                    .join('; ')
                : panel.state === 'empty'
                  ? 'No stored observations; collection runs independently.'
                  : 'Stored observations · release freshness is unknown.'}
            </div>
            <div className="kpis">
              {cardIds.map((sid) => {
                const s = series.find((s) => s.id === sid)!;
                const summary = summaryFor(panel, sid, periodKind);
                const current = resolve(panel, summary?.current);
                const prior = resolve(panel, summary?.comparison);
                return (
                  <Kpi
                    key={sid}
                    label={s.label}
                    point={current ? displayPoint(current) : undefined}
                    series={s}
                    delta={change(summary?.value, summary?.kind || 'none')}
                    comparison={
                      prior
                        ? `Compared with ${prior.period.label}`
                        : 'Comparable prior observation unavailable'
                    }
                    image={
                      id === 'trade'
                        ? sid === 'trade_exports'
                          ? 'exports'
                          : 'imports'
                        : id === 'gst'
                          ? sid.includes('average')
                            ? 'gst-average'
                            : 'gst'
                          : id === 'expenditure'
                            ? sid === 'expenditure_total'
                              ? 'total'
                              : 'capital'
                            : 'inflation'
                    }
                  />
                );
              })}
              {isCpi && (
                <Kpi
                  label="Target for latest CPI month"
                  series={spec('inflation_target', 'Policy target', 'line', 'amber')}
                  point={
                    resolve(panel, policy?.target) ? displayPoint(resolve(panel, policy!.target)!) : undefined
                  }
                  image="target"
                >
                  <span className="kpi-extra">
                    {policy
                      ? `${amount(resolve(panel, policy.lower)?.value, 'percent')} – ${amount(resolve(panel, policy.upper)?.value, 'percent')} tolerance`
                      : 'No verified policy for this period'}
                  </span>
                </Kpi>
              )}
              {id === 'gst' && grain !== 'fiscal_year' && (
                <Kpi
                  label={grain === 'month' ? 'Same month, prior year' : 'Prior matched window'}
                  series={{ ...series[0], id: 'gst_comparison', color: 'amber' }}
                  point={
                    resolve(panel, summaryFor(panel, series[0].id, periodKind)?.comparison)
                      ? displayPoint(resolve(panel, summaryFor(panel, series[0].id, periodKind)?.comparison)!)
                      : undefined
                  }
                  image="gst-average"
                />
              )}
            </div>
            <div className="chart-controls">
              <span>{unitLabel}</span>
              {isCpi ? (
                <label>
                  Methodology{' '}
                  <select
                    aria-label="CPI methodology"
                    value={base}
                    onChange={(e) => {
                      setBase(e.target.value);
                      setHidden(new Set());
                    }}
                  >
                    <option value="cpi_yoy_2024">Base 2024=100</option>
                    <option value="cpi_yoy_2012">Base 2012=100</option>
                  </select>
                </label>
              ) : (
                <label>
                  Period{' '}
                  <select
                    aria-label={`${id} reporting period`}
                    value={grain}
                    onChange={(e) => {
                      setGrain(e.target.value as PeriodKind);
                      setHidden(new Set());
                    }}
                  >
                    <option value="fiscal_year">Completed fiscal years</option>
                    <option value="fiscal_year_to_date">Matching FY to date</option>
                    {id !== 'expenditure' && <option value="month">Monthly</option>}
                  </select>
                </label>
              )}
              {(isCpi || grain === 'month') && (
                <label>
                  Window{' '}
                  <select
                    aria-label={`${id} history window`}
                    value={count}
                    onChange={(e) => setCount(Number(e.target.value))}
                  >
                    <option value={12}>12 months</option>
                    <option value={24}>24 months</option>
                    <option value={600}>All stored</option>
                  </select>
                </label>
              )}
            </div>
            <Legend series={selected} hidden={hidden} toggle={toggle} />
            <CanonicalChart id={id} series={visible} />
            <p className="period-note">
              {periodNote}
              {id === 'trade' && (
                <span className="balance-summary">
                  Selected balance:{' '}
                  <b data-testid="card-trade_balance">
                    {amount(
                      resolve(panel, summaryFor(panel, 'trade_balance', periodKind)?.current)?.value,
                      'usd_billion',
                      true,
                    )}
                  </b>
                </span>
              )}
            </p>
            <ObservationTable id={id} series={visible} />
            <div className="source-note">
              Sources:{' '}
              {panel.collection.map((c, i) => (
                <span key={c.group_id}>
                  {i ? ' · ' : ''}
                  {c.provider_id.toUpperCase()}
                </span>
              ))}{' '}
              · Latest publication in selection: {published(latestPublication)}
              <br />
              {panel.collection.map((c, i) => (
                <span key={c.group_id}>
                  {i ? ' · ' : ''}
                  {c.group_id.replaceAll('_', ' ')} collected {ist(c.last_success_at)}
                </span>
              ))}
            </div>
            <details className="provenance">
              <summary>Sources, reporting & freshness</summary>
              {panel.notes.map((n) => (
                <p key={n}>{n}</p>
              ))}
              {panel.coverage.map((n) => (
                <p key={n}>{n}</p>
              ))}
              {panel.collection.map((c) => (
                <p key={c.group_id}>
                  {c.group_id.replaceAll('_', ' ')}: last attempt {ist(c.last_attempt_at)}; last success{' '}
                  {ist(c.last_success_at)}.{c.in_progress ? ' Collection in progress.' : ''}
                  {c.next_request_not_before
                    ? ` Provider cooldown until ${ist(c.next_request_not_before)}.`
                    : ''}
                </p>
              ))}
              {isCpi && (
                <p>
                  {panel.policies.some((p) => p.active)
                    ? 'A verified policy is currently in force; the chart applies it only to months inside its validity.'
                    : 'No verified policy is currently in force; historical validity is not extended.'}
                </p>
              )}
              <ul>
                {sources.map((url) => (
                  <li key={url}>
                    <a href={url} target="_blank" rel="noreferrer">
                      Original publication ↗ <span className="source-host">{new URL(url).hostname}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </details>
          </>
        )}
      </div>
    </section>
  );
}
