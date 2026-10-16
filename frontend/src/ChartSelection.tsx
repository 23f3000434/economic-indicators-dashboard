import { useLayoutEffect, useRef, useState, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { usePlotArea, useXAxisScale, useYAxisScale } from 'recharts';
import { plotKeys, valueOf, type ViewSeries } from './presentation';

export interface ChartSelection {
  key: string;
  pinned: boolean;
  pointerY?: number;
}
export type ChartPicker = ((x: number, y: number) => string | undefined) | null;

export function tooltipPosition(
  anchor: { x: number; y: number },
  size: { width: number; height: number },
  viewport: { left: number; top: number; width: number; height: number },
) {
  const gap = 12,
    edge = 8;
  const right = viewport.left + viewport.width - edge;
  const bottom = viewport.top + viewport.height - edge;
  const x = anchor.x + gap + size.width <= right ? anchor.x + gap : anchor.x - gap - size.width;
  const y = anchor.y + gap + size.height <= bottom ? anchor.y + gap : anchor.y - gap - size.height;
  return {
    left: Math.max(viewport.left + edge, Math.min(x, right - size.width)),
    top: Math.max(viewport.top + edge, Math.min(y, bottom - size.height)),
  };
}

function CompactTooltip({
  id,
  selection,
  series,
  anchor,
}: {
  id: string;
  selection: ChartSelection;
  series: ViewSeries[];
  anchor: RefObject<SVGLineElement | null>;
}) {
  const node = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);
  useLayoutEffect(() => {
    const place = () => {
      if (!node.current || !anchor.current) return;
      const r = anchor.current.getBoundingClientRect();
      const size = node.current.getBoundingClientRect();
      const v = window.visualViewport;
      setPosition(
        tooltipPosition({ x: r.left, y: selection.pointerY ?? r.top + r.height / 3 }, size, {
          left: v?.offsetLeft || 0,
          top: v?.offsetTop || 0,
          width: v?.width || innerWidth,
          height: v?.height || innerHeight,
        }),
      );
    };
    place();
    const observer = new ResizeObserver(place);
    if (node.current) observer.observe(node.current);
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    window.visualViewport?.addEventListener('resize', place);
    window.visualViewport?.addEventListener('scroll', place);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
      window.visualViewport?.removeEventListener('resize', place);
      window.visualViewport?.removeEventListener('scroll', place);
    };
  }, [anchor, selection, series]);
  const rows = series.map((s) => ({ s, p: s.points.find((p) => (p.axisKey || p.key) === selection.key) }));
  const periods = [...new Set(rows.map(({ p }) => p?.label).filter(Boolean))];
  return createPortal(
    <div
      ref={node}
      id={`${id}-chart-tooltip`}
      role="tooltip"
      aria-live="polite"
      className="chart-tooltip"
      data-chart={id}
      data-period={selection.key}
      data-pinned={selection.pinned}
      style={{ ...position, visibility: position ? 'visible' : 'hidden' }}
    >
      <strong>{periods.join(' · ') || selection.key}</strong>
      {rows.map(({ s, p }) => {
        const status =
          p?.value == null
            ? 'Missing'
            : p.retained
              ? 'Retained · stale'
              : ['actual', 'provisional', 'estimate', 'final'].includes(p.status)
                ? p.status
                : '';
        return (
          <div className="tooltip-row" key={s.id} data-series={s.id} data-period-key={p?.key}>
            <span>
              <i className={`dot ${s.color}`} />
              {s.label}
            </span>
            <b>{valueOf(p, s)}</b>
            {status && <small>{status}</small>}
          </div>
        );
      })}
    </div>,
    document.body,
  );
}

export function ChartSelectionLayer({
  id,
  selection,
  series,
  colors,
  host,
  picker,
}: {
  id: string;
  selection: ChartSelection | null;
  series: ViewSeries[];
  colors: Record<ViewSeries['color'], string>;
  host: RefObject<HTMLDivElement | null>;
  picker: RefObject<ChartPicker>;
}) {
  const plot = usePlotArea(),
    xScale = useXAxisScale(),
    yScale = useYAxisScale();
  const anchor = useRef<SVGLineElement>(null);
  useLayoutEffect(() => {
    const centres = plotKeys(series)
      .map((key) => ({ key, x: xScale?.(key, { position: 'middle' }) }))
      .filter((p): p is { key: string; x: number } => p.x != null);
    picker.current = (clientX, clientY) => {
      const svg = host.current?.querySelector<SVGSVGElement>('.recharts-surface');
      if (!svg || !plot || !centres.length) return;
      const r = svg.getBoundingClientRect(),
        view = svg.viewBox.baseVal;
      const x = ((clientX - r.left) * view.width) / r.width;
      const y = ((clientY - r.top) * view.height) / r.height;
      if (x < plot.x || x > plot.x + plot.width || y < plot.y || y > plot.y + plot.height) return;
      return centres.reduce((nearest, p) => (Math.abs(p.x - x) < Math.abs(nearest.x - x) ? p : nearest)).key;
    };
    return () => {
      picker.current = null;
    };
  }, [host, picker, plot, xScale, series]);
  if (!selection || !plot || !xScale || !yScale) return null;
  const x = xScale(selection.key, { position: 'middle' });
  if (x == null) return null;
  const points = series
    .filter((s) => s.plot !== false)
    .map((s) => {
      const p = s.points.find((p) => (p.axisKey || p.key) === selection.key);
      return { s, y: p?.value == null ? undefined : yScale(Number(p.value)) };
    });
  const y = points.find((p) => p.y != null)?.y;
  return (
    <>
      <g className="chart-selection" pointerEvents="none" aria-hidden="true">
        <line ref={anchor} className="chart-crosshair" x1={x} x2={x} y1={plot.y} y2={plot.y + plot.height} />
        {y != null && <line className="chart-crosshair" x1={plot.x} x2={plot.x + plot.width} y1={y} y2={y} />}
        {points
          .filter(({ s, y }) => s.kind !== 'bar' && y != null)
          .map(({ s, y }) => (
            <circle
              key={s.id}
              className="chart-active-point"
              data-series={s.id}
              cx={x}
              cy={y}
              r={6}
              fill={colors[s.color]}
              stroke="#fff"
              strokeWidth={2}
            />
          ))}
      </g>
      <CompactTooltip id={id} selection={selection} series={series} anchor={anchor} />
    </>
  );
}
