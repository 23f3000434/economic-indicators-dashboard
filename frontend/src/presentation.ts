import { amount, type Measurement, type Point, type Series, type Unit } from './contracts';

export interface ViewPoint {
  key: string;
  axisKey?: string;
  label: string;
  start: string;
  end: string;
  value: string | null;
  retained: boolean;
  source: string | null;
  published: string | null;
  retrieved: string | null;
  status: string;
  methodology: string;
  note: string;
}
export interface ViewSeries {
  id: string;
  label: string;
  unit: Unit;
  color: 'cyan' | 'amber' | 'green' | 'muted';
  kind: 'bar' | 'line' | 'area';
  stack?: string;
  dashed?: boolean;
  signed?: boolean;
  plot?: boolean;
  points: ViewPoint[];
}
export const displayPoint = (p: Measurement): ViewPoint => ({
  key: p.period.key,
  label: p.period.label,
  start: p.period.start,
  end: p.period.end,
  value: p.value,
  retained: p.retained,
  source: p.source_url,
  published: p.definition.published_at,
  retrieved: p.retrieved_at,
  status: p.definition.status,
  methodology: p.definition.methodology,
  note: [p.footnote, p.definition.publication_note].filter(Boolean).join(' '),
});
export const gdpPoint = (p: Point, s: Series): ViewPoint => ({
  key: p.period_key,
  label: p.period_label,
  start: p.period_start,
  end: p.period_end,
  value: p.value,
  retained: p.retained,
  source: s.source.url,
  published: s.source.published_at,
  retrieved: p.retrieved_at,
  status: p.provider_status || p.estimate_status,
  methodology: s.reporting_basis,
  note: p.footnote,
});
export const valueOf = (p: ViewPoint | undefined, s: ViewSeries) => amount(p?.value, s.unit, s.signed);
export function periodKeys(series: ViewSeries[]) {
  const points = series.flatMap((s) => s.points);
  const unique = new Map(points.map((p) => [p.key, p]));
  return [...unique.values()]
    .sort((a, b) => a.end.localeCompare(b.end) || a.start.localeCompare(b.start))
    .map((p) => p.key);
}
export function sliceSeries(series: ViewSeries[], count: number) {
  const keys = new Set(plotKeys(series).slice(-count));
  return series.map((s) => ({ ...s, points: s.points.filter((p) => keys.has(p.axisKey || p.key)) }));
}
export function plotKeys(series: ViewSeries[]) {
  return [
    ...new Set(
      series
        .flatMap((s) => s.points)
        .sort((a, b) => a.end.localeCompare(b.end))
        .map((p) => p.axisKey || p.key),
    ),
  ];
}
