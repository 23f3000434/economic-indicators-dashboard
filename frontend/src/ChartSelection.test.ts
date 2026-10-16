import { describe, expect, test } from 'vitest';
import { tooltipPosition } from './ChartSelection';

describe('viewport tooltip placement', () => {
  const viewport = { left: 0, top: 0, width: 1214, height: 2159 };
  test('opens alongside the selected period with room to read', () => {
    expect(tooltipPosition({ x: 200, y: 300 }, { width: 300, height: 140 }, viewport)).toEqual({
      left: 212,
      top: 312,
    });
  });
  test('flips left and above at the viewport edges', () => {
    expect(tooltipPosition({ x: 1200, y: 2140 }, { width: 300, height: 140 }, viewport)).toEqual({
      left: 888,
      top: 1988,
    });
  });
  test('clamps both axes inside a small scrolled visual viewport', () => {
    expect(
      tooltipPosition(
        { x: 160, y: 110 },
        { width: 304, height: 150 },
        { left: 10, top: 20, width: 320, height: 190 },
      ),
    ).toEqual({ left: 18, top: 28 });
  });
});
