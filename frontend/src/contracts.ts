// Mirrors the versioned FastAPI response; backend OpenAPI is the wire authority.
export interface Point {
  period_key: string;
  period_label: string;
  period_start: string;
  period_end: string;
  value: string | null;
  estimate_status: 'unspecified';
  provider_status: string;
  footnote: string;
  retrieved_at: string | null;
  dataset_updated_on: string | null;
  retained: boolean;
}
export interface Series {
  id: 'gdp_india' | 'gdp_world';
  label: string;
  unit: 'percent';
  reporting_basis: 'fiscal_year_apr_mar' | 'calendar_year_aggregate';
  points: Point[];
  source: {
    id: 'world_bank_wdi';
    url: string;
    published_at: string | null;
    dataset_updated_on: string | null;
    retrieved_at: string | null;
  };
}
export interface Panel {
  schema_version: '1';
  id: 'gdp';
  state: 'ready' | 'stale' | 'empty' | 'unavailable';
  collection: {
    last_attempt_at: string | null;
    last_success_at: string | null;
    last_error_kind: string | null;
    in_progress: boolean;
  };
  series: Series[];
  summaries: {
    series_id: string;
    current_period_key: string | null;
    comparison_period_key: string | null;
    change: { kind: 'percentage_points'; value: string | null };
  }[];
  notes: string[];
}
export interface SessionInfo {
  csrf_token: string;
  session_expires_at: string;
  user: { id: string; username: string };
}
export interface Tokens extends SessionInfo {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  access_expires_at: string;
}

export const pointAt = (series: Series, key: string | null) =>
  series.points.find((p) => p.period_key === key);
export function metric(value: string | null | undefined, suffix = '%'): string {
  if (value == null || !/^-?\d+(\.\d+)?$/.test(value)) return '—';
  // Exact decimal half-expand rounding; binary floats are reserved for chart coordinates.
  const negative = value.startsWith('-');
  const [whole, fraction = ''] = (negative ? value.slice(1) : value).split('.');
  const digits = fraction.padEnd(3, '0');
  let hundredths = BigInt(whole) * 100n + BigInt(digits.slice(0, 2));
  if (digits[2] >= '5') hundredths += 1n;
  const integer = new Intl.NumberFormat('en-IN').format(hundredths / 100n);
  return `${negative && hundredths !== 0n ? '-' : ''}${integer}.${String(hundredths % 100n).padStart(2, '0')}${suffix}`;
}
export const plotValue = (point: Point | undefined) => (point?.value == null ? null : Number(point.value));
export function ist(value: string | null): string {
  return value
    ? new Intl.DateTimeFormat('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Kolkata',
      }).format(new Date(value)) + ' IST'
    : '—';
}

export type PanelId = 'gdp' | 'debt' | 'trade' | 'gst' | 'inflation' | 'expenditure';
export function exchangeTime(value: string | null, precision: TickerItem['exchange_timestamp_precision']) {
  if (!value) return '—';
  return (
    new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...(precision === 'millisecond' ? ({ second: '2-digit', fractionalSecondDigits: 3 } as const) : {}),
      timeZone: 'Asia/Kolkata',
    }).format(new Date(value)) + ' IST'
  );
}
export type Unit = 'inr_crore' | 'usd_billion' | 'percent';
export type PeriodKind =
  | 'month'
  | 'fiscal_year'
  | 'fiscal_year_to_date'
  | 'calendar_year'
  | 'policy_validity';
export interface Period {
  key: string;
  label: string;
  kind: PeriodKind;
  start: string;
  end: string;
}
export interface Reference {
  series_id: string;
  period_key: string;
}
export interface Measurement {
  series_id: string;
  period: Period;
  value: string | null;
  definition: {
    group: 'expenditure' | 'gst' | 'trade' | 'inflation' | 'inflation_policy' | 'debt';
    provider: 'cga' | 'gstn' | 'commerce' | 'mospi' | 'gazette' | 'imf' | 'world_bank_data360';
    unit: Unit;
    methodology: string;
    status: 'actual' | 'unspecified' | 'provisional' | 'final' | 'estimate';
    published_at: string | null;
    publication_note: string;
    vintage_date: string | null;
    source_status: string | null;
    supporting_sources: { role: 'metadata' | 'methodology'; url: string; response_sha256: string }[];
    inputs: Reference[];
  };
  source_url: string | null;
  retrieved_at: string | null;
  response_sha256: string | null;
  footnote: string;
  retained: boolean;
}
export interface IndicatorSeries {
  id: string;
  label: string;
  unit: Unit;
  points: Measurement[];
}
export interface IndicatorSummary {
  current: Reference;
  comparison: Reference | null;
  kind: 'relative_percent' | 'percentage_points' | 'none';
  value: string | null;
  period_kind: Exclude<PeriodKind, 'policy_validity'>;
}
type Collection = Panel['collection'];
export interface GroupCollection extends Collection {
  group_id: string;
  provider_id: string;
  next_request_not_before: string | null;
  interval_seconds: number;
}
export interface InflationPolicy {
  validity: Period;
  target: Reference;
  lower: Reference;
  upper: Reference;
  active: boolean;
}
export interface IndicatorPanel {
  schema_version: '1';
  id: Exclude<PanelId, 'gdp'>;
  state: Panel['state'];
  availability: 'implemented' | 'blocked' | 'unverified';
  collection: GroupCollection[];
  series: IndicatorSeries[];
  summaries: IndicatorSummary[];
  notes: string[];
  coverage: string[];
  policies: InflationPolicy[];
  freshness_assessment: 'unknown';
  report_years: number;
}
export interface TickerItem {
  id: 'sensex' | 'nifty_bank' | 'nifty_it';
  label: string;
  exchange: 'NSE' | 'BSE';
  provider_id: 'nse' | 'upstox';
  state: 'live' | 'snapshot' | 'delayed' | 'closed' | 'stale' | 'unavailable';
  availability: 'implemented';
  unit: 'index_points';
  value: string | null;
  previous_close: string | null;
  previous_close_basis: 'published_previous_close' | 'last_price_minus_net_change' | null;
  change_points: string | null;
  change_percent: string | null;
  exchange_timestamp: string | null;
  exchange_timestamp_precision: 'minute' | 'millisecond' | null;
  provider_timestamp: string | null;
  retrieved_at: string | null;
  source_url: string | null;
  response_sha256: string | null;
  market_state: 'open' | 'closed' | 'closing' | 'preopen' | 'unknown';
  market_status_at: string | null;
  market_status_checked_at: string | null;
  market_status_source_url: string | null;
  market_status_sha256: string | null;
  market_session_close_at: string | null;
  market_timings_source_url: string | null;
  market_timings_sha256: string | null;
  retained: boolean;
  error_kind: string | null;
}
export interface TickerSnapshot {
  schema_version: '1';
  generated_at: string;
  ticker: TickerItem[];
  collection_groups: GroupCollection[];
}
export interface Dashboard {
  schema_version: '1';
  generated_at: string;
  panels: (Panel | IndicatorPanel)[];
  ticker: TickerItem[];
  collection_groups: GroupCollection[];
}

export function resolve(panel: IndicatorPanel | null, reference: Reference | null | undefined) {
  if (!reference) return undefined;
  return panel?.series
    .find((s) => s.id === reference.series_id)
    ?.points.find((p) => p.period.key === reference.period_key);
}
export const summaryFor = (panel: IndicatorPanel | null, series: string, kind: PeriodKind) =>
  panel?.summaries.find((s) => s.current.series_id === series && s.period_kind === kind);

// Display conversion only. Economic calculations and comparisons belong to FastAPI.
export function scaledDecimal(value: string | null | undefined, decimalPlaces: number): string | null {
  if (value == null || !/^-?\d+(\.\d+)?$/.test(value)) return null;
  const sign = value.startsWith('-') ? '-' : '';
  const [whole, fraction = ''] = value.replace(/^-/, '').split('.');
  const digits = whole.padStart(decimalPlaces + 1, '0');
  return `${sign}${digits.slice(0, -decimalPlaces)}.${digits.slice(-decimalPlaces)}${fraction}`;
}
export function amount(value: string | null | undefined, unit: Unit, signed = false): string {
  const formatted = unit === 'inr_crore' ? metric(scaledDecimal(value, 5), '') : metric(value, '');
  if (formatted === '—') return formatted;
  const plus = signed && value != null && !value.startsWith('-') && /[1-9]/.test(value) ? '+' : '';
  return `${unit === 'inr_crore' ? '₹' : unit === 'usd_billion' ? '$' : ''}${plus}${formatted}${unit === 'inr_crore' ? ' L cr' : unit === 'usd_billion' ? ' B' : '%'}`;
}
export function change(value: string | null | undefined, kind: IndicatorSummary['kind']) {
  if (kind === 'none') return '—';
  const formatted = metric(value, kind === 'percentage_points' ? ' pp' : '%');
  return `${value != null && !value.startsWith('-') && /[1-9]/.test(value) && formatted !== '—' ? '+' : ''}${formatted}`;
}
export function published(value: string | null) {
  if (!value) return 'not supplied';
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(value));
}
export function policyFor(panel: IndicatorPanel | null, period?: Period) {
  return panel?.policies.find((p) =>
    period ? p.validity.start <= period.start && period.end <= p.validity.end : p.active,
  );
}
