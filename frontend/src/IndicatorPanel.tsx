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
import { Details } from './Details';
import { Kpi, Legend, ObservationTable, PanelHeading, PanelSkin } from './PanelParts';
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
      : id.startsWith('cpi') || id.startsWith('inflation') || id.startsWith('debt')
        ? 'percent'
        : 'inr_crore',
    points: [],
    ...extra,
  };
}
const specs = {
  debt: [spec('debt_india', 'India', 'area', 'cyan'), spec('debt_us', 'US', 'line', 'amber')],
  trade: [
    spec('trade_imports', 'Imports', 'bar', 'cyan'),
    spec('trade_exports', 'Exports', 'bar', 'amber'),
    spec('trade_balance', 'Trade Balance', 'line', 'green', { signed: true }),
  ],
  expenditure: [
    spec('expenditure_capital', 'Capital Expenditure', 'bar', 'amber', { stack: 'actual' }),
    spec('expenditure_revenue', 'Revenue Expenditure', 'bar', 'cyan', { stack: 'actual' }),
    spec('expenditure_total', 'Total Expenditure', 'line', 'muted', { plot: false }),
  ],
  gst: [
    spec('gst_fy_total', 'Gross GST', 'bar', 'cyan'),
    spec('gst_fy_average', 'Monthly Average', 'line', 'amber'),
  ],
};
const sourceLabels = {
  debt: 'IMF WEO via World Bank',
  trade: 'Commerce / PIB',
  gst: 'GSTN · excl. compensation cess',
  inflation: 'MoSPI / Gazette',
  expenditure: 'CGA · actuals, Apr–Mar',
};
export function IndicatorPanel({ panel }: { panel: Panel }) {
  const { id } = panel;
  const [grain, setGrain] = useState<PeriodKind>('fiscal_year');
  const [base, setBase] = useState('cpi_yoy_2024');
  const [count, setCount] = useState(12);
  const [hidden, setHidden] = useState(new Set<string>());
  const toggle = (sid: string) =>
    setHidden((old) => {
      const n = new Set(old);
      if (n.has(sid)) n.delete(sid);
      else n.add(sid);
      return n;
    });
  const isCpi = id === 'inflation',
    isDebt = id === 'debt';
  const periodKind = isCpi ? 'month' : grain;
  let series: ViewSeries[] =
    id === 'trade'
      ? specs.trade
      : id === 'expenditure'
        ? specs.expenditure
        : isDebt
          ? specs.debt
          : id === 'gst'
            ? grain === 'month'
              ? [spec('gst_gross_ex_cess', 'GST Collections', 'bar', 'cyan')]
              : grain === 'fiscal_year_to_date'
                ? [spec('gst_fytd_average', 'Monthly Average', 'bar', 'cyan')]
                : specs.gst
            : [spec(base, 'Inflation Rate', 'area', 'cyan')];
  series = series.map((s) => ({
    ...s,
    points: (panel.series.find((p) => p.id === s.id)?.points || [])
      .filter((p) => isDebt || p.period.kind === periodKind)
      .map((p) => ({ ...displayPoint(p), ...(isDebt ? { axisKey: p.period.start.slice(0, 4) } : {}) })),
  }));
  const latestCpi = resolve(panel, summaryFor(panel, base, 'month')?.current);
  const policy = latestCpi ? policyFor(panel, latestCpi.period) : undefined;
  if (isCpi) {
    const target = spec('inflation_target', 'RBI Target', 'line', 'amber', { dashed: true });
    target.points = (panel.series.find((p) => p.id === base)?.points || [])
      .filter((p) => p.period.kind === 'month')
      .map((p) => {
        const applicable = policyFor(panel, p.period),
          observation = resolve(panel, applicable?.target);
        return {
          ...displayPoint(p),
          value: observation?.value ?? null,
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
  const selected = sliceSeries(series, isCpi || grain === 'month' ? count : panel.report_years),
    visible = selected.filter((s) => !hidden.has(s.id));
  const cardIds =
    id === 'trade'
      ? ['trade_exports', 'trade_imports']
      : id === 'expenditure'
        ? ['expenditure_total', 'expenditure_capital']
        : isDebt
          ? ['debt_india', 'debt_us']
          : id === 'gst'
            ? grain === 'fiscal_year'
              ? ['gst_fy_total', 'gst_fy_average']
              : grain === 'month'
                ? ['gst_gross_ex_cess']
                : ['gst_fytd_average']
            : [base];
  const summary = (sid: string) =>
    summaryFor(panel, sid, isDebt && sid === 'debt_us' ? 'calendar_year' : periodKind);
  const notices = panel.collection.filter((c) => c.last_error_kind);
  const selectedPoints = selected.flatMap((s) => s.points).filter((p) => p.value !== null);
  const latestPublication =
    selectedPoints
      .map((p) => p.published)
      .filter(Boolean)
      .sort()
      .at(-1) || null;
  const sources = [...new Set(selectedPoints.map((p) => p.source).filter((u): u is string => !!u))];
  const vintage = panel.series
    .flatMap((s) => s.points)
    .map((p) => p.definition.vintage_date)
    .filter(Boolean)
    .sort()
    .at(-1);
  const periodNote = isCpi
    ? `${base.endsWith('2024') ? '2024' : '2012'}=100 base · All-India combined headline CPI year-on-year %. Changes in pp; no bridge across bases.`
    : isDebt
      ? 'General-government gross debt / GDP. India April–March FY versus US calendar year. WEO vintage and actual/estimate classification retained; country institutional coverage/accounting differences remain.'
      : id === 'gst'
        ? 'Gross GST before refunds, excluding compensation cess. Averages use published months; full FY requires 12.'
        : id === 'trade'
          ? 'Merchandise only, USD billion. Balance = exports − imports; negative values are deficits. Comparisons use matching windows.'
          : 'April–March actual expenditure, unaudited/provisional. Revenue + capital = total; BE/RE excluded.';
  return (
    <section className={`panel ${id}-panel`} aria-labelledby={`${id}-title`}>
      <PanelSkin id={id} />
      <PanelHeading id={id} state={panel.state} loading={false} />
      <div className="panel-content">
        <div className={`panel-notice ${notices.length ? 'warning' : ''}`} role="status">
          {notices.length
            ? notices
                .map(
                  (c) =>
                    `${c.group_id.replaceAll('_', ' ')} · retained data · ${c.last_error_kind?.replaceAll('_', ' ')}`,
                )
                .join('; ')
            : panel.state === 'empty'
              ? 'No stored observations.'
              : panel.state === 'unavailable'
                ? 'Source unavailable; retries independently.'
                : ''}
        </div>
        <div className="kpis">
          {cardIds.map((sid) => {
            const s = series.find((s) => s.id === sid)!;
            const sum = summary(sid),
              current = resolve(panel, sum?.current),
              prior = resolve(panel, sum?.comparison);
            return (
              <Kpi
                key={sid}
                label={
                  isDebt
                    ? sid === 'debt_india'
                      ? 'India'
                      : 'US'
                    : id === 'gst' && sid === 'gst_fy_total'
                      ? 'GST Collections'
                      : s.label
                }
                point={current ? displayPoint(current) : undefined}
                series={s}
                delta={change(sum?.value, sum?.kind || 'none')}
                comparison={
                  prior ? `Compared with ${prior.period.label}` : 'Comparable prior observation unavailable'
                }
                image={
                  isDebt
                    ? sid === 'debt_india'
                      ? 'india'
                      : 'us'
                    : id === 'trade'
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
              label="RBI Target"
              series={spec('inflation_target', 'RBI Target', 'line', 'amber')}
              point={
                resolve(panel, policy?.target) ? displayPoint(resolve(panel, policy!.target)!) : undefined
              }
              image="target"
            >
              <span className="kpi-extra">
                {policy
                  ? `${amount(resolve(panel, policy.lower)?.value, 'percent')}–${amount(resolve(panel, policy.upper)?.value, 'percent')} tolerance`
                  : 'No verified policy for period'}
              </span>
            </Kpi>
          )}
          {id === 'gst' && grain !== 'fiscal_year' && (
            <Kpi
              label={grain === 'month' ? 'Same month, prior year' : 'Prior matched window'}
              series={{ ...series[0], id: 'gst_comparison', color: 'amber' }}
              point={
                resolve(panel, summary(series[0].id)?.comparison)
                  ? displayPoint(resolve(panel, summary(series[0].id)?.comparison)!)
                  : undefined
              }
              image="gst-average"
            />
          )}
        </div>
        <Legend
          series={id === 'expenditure' ? [selected[1], selected[0], selected[2]] : selected}
          hidden={hidden}
          toggle={toggle}
        />
        <CanonicalChart id={id} series={visible} />
        <div className="source-note">
          {id === 'expenditure' && grain !== 'fiscal_year' ? 'CGA · actuals, FY to date' : sourceLabels[id]}
          {!isCpi && !isDebt
            ? ` · ${grain === 'fiscal_year' ? 'Completed FYs' : grain === 'fiscal_year_to_date' ? 'Matched FY to date' : 'Monthly'}`
            : ''}
          {isCpi ? ` · base ${base.endsWith('2024') ? '2024' : '2012'}` : ''} ·{' '}
          {isDebt
            ? `vintage ${vintage || '—'} · India FY / US CY`
            : latestPublication
              ? `released ${published(latestPublication)}`
              : 'publication not supplied'}
        </div>
        <Details label={`${id} reporting and data`}>
          <div className="chart-controls">
            <span>
              {series[0]?.unit === 'percent'
                ? '%'
                : series[0]?.unit === 'usd_billion'
                  ? 'USD billion'
                  : '₹ lakh crore'}
            </span>
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
              !isDebt && (
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
              )
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
          <p className="period-note">{periodNote}</p>
          {id === 'trade' && (
            <p>
              Selected balance:{' '}
              <b data-testid="card-trade_balance">
                {amount(
                  resolve(panel, summaryFor(panel, 'trade_balance', periodKind)?.current)?.value,
                  'usd_billion',
                  true,
                )}
              </b>
            </p>
          )}
          <ObservationTable id={id} series={visible} />
          <div className="provenance">
            <p>
              Latest publication in selection: {published(latestPublication)}.{' '}
              {isDebt ? `Dataset vintage ${vintage}.` : ''} Collection time is not observation freshness.
            </p>
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
                  ? 'Verified policy is currently in force; applied only to months inside validity.'
                  : 'No verified policy is currently in force; historical validity is never extended.'}
              </p>
            )}
            <ul>
              {sources.map((url) => (
                <li key={url}>
                  <a href={url} target="_blank" rel="noreferrer">
                    Original publication ↗ {new URL(url).hostname}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </Details>
      </div>
    </section>
  );
}
