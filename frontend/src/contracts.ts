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
