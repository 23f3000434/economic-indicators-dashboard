import { describe, expect, it } from 'vitest';
import { metric, plotValue, pointAt, type Series } from './contracts';

describe('canonical selectors', () => {
  it('preserves null gaps and valid zero, with one formatter for all presentations', () => {
    expect(metric(null)).toBe('—');
    expect(metric('0')).toBe('0.00%');
    expect(metric('7.56666179284244')).toBe('7.57%');
    expect(metric('0.46738286107726', ' pp')).toBe('0.47 pp');
    expect(plotValue(undefined)).toBeNull();
    const series = {
      points: [
        { period_key: '2024', value: null },
        { period_key: '2025', value: '0' },
      ],
    } as Series;
    expect(plotValue(pointAt(series, '2024'))).toBeNull();
    expect(plotValue(pointAt(series, '2025'))).toBe(0);
    expect(pointAt(series, '2023')).toBeUndefined();
  });
  it('rounds decimal strings without losing precision at a display boundary', () => {
    expect(metric('7.12499999999999999999')).toBe('7.12%');
    expect(metric('7.12500000000000000000')).toBe('7.13%');
    expect(metric('-7.125')).toBe('-7.13%');
    expect(metric('-0.0001')).toBe('0.00%');
    expect(metric('NaN')).toBe('—');
  });
});

// Display boundaries do not repeat economic arithmetic from the API.
import {
  amount,
  change,
  policyFor,
  resolve,
  scaledDecimal,
  summaryFor,
  type IndicatorPanel,
} from './contracts';
import { periodKeys, sliceSeries, type ViewSeries } from './presentation';

describe('multi-provider display contracts', () => {
  it('formats currency conversions, signed balances, zero and percentage points exactly', () => {
    expect(scaledDecimal('2077958', 5)).toBe('20.77958');
    expect(amount('2077958', 'inr_crore')).toBe('₹20.78 L cr');
    expect(amount('100499.999999999999', 'inr_crore')).toBe('₹1.00 L cr');
    expect(amount('100500', 'inr_crore')).toBe('₹1.01 L cr');
    expect(amount('-240.18', 'usd_billion', true)).toBe('$-240.18 B');
    expect(amount('12.5', 'usd_billion', true)).toBe('$+12.50 B');
    expect(amount('0', 'usd_billion', true)).toBe('$0.00 B');
    expect(amount(null, 'inr_crore')).toBe('—');
    expect(change('0.71', 'percentage_points')).toBe('+0.71 pp');
    expect(change('-0.2', 'relative_percent')).toBe('-0.20%');
    expect(change(null, 'relative_percent')).toBe('—');
  });
  it('resolves API summaries to the original canonical object without recalculation', () => {
    const point = { series_id: 'trade_exports', period: { key: 'FY2025-26' }, value: '437.06' };
    const summary = {
      current: { series_id: 'trade_exports', period_key: 'FY2025-26' },
      comparison: null,
      period_kind: 'fiscal_year',
      value: '99.12345',
      kind: 'relative_percent',
    };
    const panel = {
      series: [{ id: 'trade_exports', points: [point] }],
      summaries: [summary],
    } as unknown as IndicatorPanel;
    expect(summaryFor(panel, 'trade_exports', 'fiscal_year')).toBe(summary);
    expect(resolve(panel, summary.current)).toBe(point);
    expect(resolve(panel, null)).toBeUndefined();
    expect(summaryFor(panel, 'trade_exports', 'month')).toBeUndefined();
  });
  it('applies policy only inside its dated window and honours active status for current policy', () => {
    const validity = {
      key: '2026-04-01/2031-03-31',
      kind: 'policy_validity',
      label: 'valid',
      start: '2026-04-01',
      end: '2031-03-31',
    } as const;
    const policy = { validity, active: false };
    const panel = { policies: [policy] } as unknown as IndicatorPanel;
    expect(policyFor(panel)).toBeUndefined();
    expect(
      policyFor(panel, { ...validity, kind: 'month', start: '2026-03-01', end: '2026-03-31' }),
    ).toBeUndefined();
    expect(policyFor(panel, { ...validity, kind: 'month', start: '2026-04-01', end: '2026-04-30' })).toBe(
      policy,
    );
    expect(
      policyFor(panel, { ...validity, kind: 'month', start: '2031-04-01', end: '2031-04-30' }),
    ).toBeUndefined();
  });
  it('keeps nulls and selected periods consistent across visible series', () => {
    const first = { key: '2026-01', start: '2026-01-01', end: '2026-01-31', value: '0' };
    const middle = { key: '2026-02', start: '2026-02-01', end: '2026-02-28', value: null };
    const last = { key: '2026-03', start: '2026-03-01', end: '2026-03-31', value: '5' };
    const series = [
      { id: 'cpi', points: [first, middle, last] },
      { id: 'target', points: [first, last] },
    ] as ViewSeries[];
    expect(periodKeys(series)).toEqual(['2026-01', '2026-02', '2026-03']);
    const selected = sliceSeries(series, 2);
    expect(periodKeys(selected)).toEqual(['2026-02', '2026-03']);
    expect(selected[0].points[0].value).toBeNull();
    expect(selected[1].points).toEqual([last]);
  });
});
