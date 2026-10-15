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
