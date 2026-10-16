import { describe, expect, it } from 'vitest';
import { tickerStatus } from './Ticker';

describe('market status badge reflects real observations', () => {
  it.each(['live', 'snapshot', 'delayed', 'stale', 'closed', 'unavailable'] as const)(
    'labels uniform %s accurately',
    (state) => {
      expect(tickerStatus([{ value: state === 'unavailable' ? null : '100', state }], '')).toBe(
        state.toUpperCase(),
      );
    },
  );
  it('reports mixed states, retained connection failures and missing values', () => {
    expect(
      tickerStatus(
        [
          { value: '100', state: 'snapshot' },
          { value: '99', state: 'delayed' },
        ],
        '',
      ),
    ).toBe('MIXED');
    expect(tickerStatus([{ value: '100', state: 'live' }], 'offline')).toBe('STALE');
    expect(tickerStatus([{ value: null, state: 'live' }], '')).toBe('UNAVAILABLE');
    expect(tickerStatus([], '')).toBe('NO DATA');
  });
});
