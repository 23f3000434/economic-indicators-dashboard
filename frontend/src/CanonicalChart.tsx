import {
  Area,
  Bar,
  LabelList,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { metric, scaledDecimal } from './contracts';
import { PointDetails } from './PanelParts';
import { periodKeys, type ViewSeries } from './presentation';

const colors = { cyan: '#00c8f4', amber: '#ffc124', green: '#38dc68', muted: '#a7b3bf' };
export function CanonicalChart({ id, series }: { id: string; series: ViewSeries[] }) {
  const keys = periodKeys(series);
  const data = keys.map((key) => ({
    key,
    ...Object.fromEntries(
      series.map((s) => {
        const value = s.points.find((p) => p.key === key)?.value;
        return [s.id, value == null ? null : Number(value)]; // coordinates only
      }),
    ),
  }));
  const unit = series[0]?.unit;
  const label = (raw: string | null | undefined) =>
    metric(unit === 'inr_crore' ? scaledDecimal(raw, 5) : raw, unit === 'percent' ? '%' : '');
  return (
    <div className="chart-space" data-testid={`${id}-chart`}>
      {series.some((s) => s.points.some((p) => p.value !== null)) ? (
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <ComposedChart
            data={data}
            margin={{ top: 12, right: 6, bottom: 2, left: -5 }}
            barGap={5}
            aria-label={`${id} canonical observations chart`}
            accessibilityLayer
          >
            <defs>
              {(['cyan', 'amber', 'green'] as const).map((color) => (
                <linearGradient id={`${id}-${color}`} x1="0" y1="0" x2="0" y2="1" key={color}>
                  <stop offset="0%" stopColor={colors[color]} />
                  <stop
                    offset="100%"
                    stopColor={color === 'amber' ? '#bc8200' : color === 'cyan' ? '#006080' : '#126c24'}
                  />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid vertical={false} stroke="#404753" />
            <XAxis
              dataKey="key"
              tickFormatter={(key: string) =>
                key.startsWith('FY')
                  ? key.slice(2).split(':')[0]
                  : key.length === 7
                    ? new Date(key + '-01').toLocaleDateString('en-GB', {
                        month: 'short',
                        year: '2-digit',
                        timeZone: 'UTC',
                      })
                    : key
              }
              tick={{ fill: '#b7bcc6', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              minTickGap={16}
            />
            <YAxis
              width={58}
              tick={{ fill: '#b7bcc6', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(value: number) =>
                metric(
                  unit === 'inr_crore' ? scaledDecimal(String(value), 5) : String(value),
                  unit === 'percent' ? '%' : '',
                ).replace(/\.00(?=%|$)/, '')
              }
            />
            <ReferenceLine y={0} stroke="#7e8790" />
            <Tooltip
              cursor={{ fill: '#ffffff08' }}
              content={({ active, label }) =>
                active ? (
                  <div className="chart-tooltip">
                    <strong>{String(label)}</strong>
                    {series.map((s) => (
                      <PointDetails key={s.id} p={s.points.find((p) => p.key === String(label))} series={s} />
                    ))}
                  </div>
                ) : null
              }
            />
            {series
              .filter((s) => s.plot !== false)
              .map((s) =>
                s.kind === 'bar' ? (
                  <Bar
                    key={s.id}
                    dataKey={s.id}
                    name={s.label}
                    fill={`url(#${id}-${s.color})`}
                    radius={s.stack ? undefined : [3, 3, 0, 0]}
                    stackId={s.stack}
                    maxBarSize={32}
                    isAnimationActive={false}
                  >
                    <LabelList
                      content={(props) => {
                        const key = data[Number(props.index)]?.key;
                        const point = s.points.find((p) => p.key === key);
                        if (point?.value == null) return null;
                        const x = Number(props.x) + Number(props.width) / 2;
                        const y = s.stack
                          ? Number(props.y) + Number(props.height) / 2 + 3
                          : Number(point.value) < 0
                            ? Number(props.y) + Number(props.height) + 11
                            : Number(props.y) - 5;
                        return (
                          <text x={x} y={y} textAnchor="middle" fill="#e8eef5" fontSize={9}>
                            {label(point.value)}
                          </text>
                        );
                      }}
                    />
                  </Bar>
                ) : s.kind === 'area' ? (
                  <Area
                    key={s.id}
                    dataKey={s.id}
                    name={s.label}
                    stroke={colors[s.color]}
                    fill={`url(#${id}-${s.color})`}
                    fillOpacity={0.24}
                    strokeWidth={2}
                    type="linear"
                    dot={false}
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                ) : (
                  <Line
                    key={s.id}
                    dataKey={s.id}
                    name={s.label}
                    stroke={colors[s.color]}
                    strokeWidth={s.dashed ? 1.4 : 2}
                    strokeDasharray={s.dashed ? '5 4' : undefined}
                    dot={keys.length <= 12 && !s.dashed ? { r: 2, fill: colors[s.color] } : false}
                    type="linear"
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                ),
              )}
          </ComposedChart>
        </ResponsiveContainer>
      ) : (
        <div className="chart-empty">
          <span>—</span>No stored observations in this selection.
        </div>
      )}
      <span className="sr-only">
        {id} chart. Arrow keys inspect periods. The observations table provides the same values and source
        details.
      </span>
    </div>
  );
}
