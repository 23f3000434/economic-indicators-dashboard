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
import { plotKeys, type ViewSeries } from './presentation';

export function CanonicalChart({ id, series }: { id: string; series: ViewSeries[] }) {
  const colors = {
    cyan: id === 'expenditure' ? '#0046B7' : '#0FB8E6',
    amber: id === 'gst' ? '#F4E15C' : '#FFB012',
    green: '#22D700',
    muted: '#a7b3bf',
  };
  const keys = plotKeys(series);
  const data = keys.map((key) => ({
    key,
    ...Object.fromEntries(
      series.map((s) => {
        const value = s.points.find((p) => (p.axisKey || p.key) === key)?.value;
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
            margin={{
              top: 10,
              right: id === 'trade' ? 1.61 : id === 'gst' ? 2.51 : id === 'expenditure' ? 0.61 : 1,
              bottom: 8,
              left: 0,
            }}
            barGap={5}
            aria-label={`${id} canonical observations chart`}
            accessibilityLayer
          >
            <defs>
              <linearGradient id={`${id}-reference-line`} x1="0" y1="0" x2="1" y2="0">
                <stop offset="6.73077%" stopColor="#191A1E" />
                <stop offset="46.6346%" stopColor="#0FCBFF" />
                <stop offset="92.7885%" stopColor="#191A1E" />
              </linearGradient>
              <linearGradient id={`${id}-debt-area`} x1="0" y1="0" x2="0" y2="1">
                <stop stopColor="#15657D" />
                <stop offset="1" stopColor="#15657D" stopOpacity={0} />
              </linearGradient>
              {(['cyan', 'amber', 'green'] as const).map((color) => (
                <linearGradient id={`${id}-${color}`} x1="0" y1="0" x2="0" y2="1" key={color}>
                  <stop offset="0%" stopColor={colors[color]} />
                  <stop
                    offset="100%"
                    stopColor={
                      color === 'amber'
                        ? '#844B08'
                        : color === 'cyan'
                          ? id === 'expenditure'
                            ? '#0FB8E6'
                            : '#061E44'
                          : '#126c24'
                    }
                  />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid
              vertical={id === 'debt' || id === 'inflation'}
              horizontal={id !== 'debt' && id !== 'inflation'}
              stroke={id === 'debt' || id === 'inflation' ? '#272727' : '#5B5B5B'}
            />
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
              tick={{
                fill: '#cccccc',
                fontSize: id === 'debt' || id === 'inflation' ? 18.73 : 16,
                fontWeight: id === 'debt' ? 400 : 600,
              }}
              axisLine={false}
              tickLine={false}
              minTickGap={16}
              height={30}
            />
            <YAxis
              tickCount={6}
              width={
                id === 'gdp'
                  ? 37
                  : id === 'trade'
                    ? 36.02
                    : id === 'gst'
                      ? 35.12
                      : id === 'expenditure'
                        ? 37.02
                        : id === 'debt'
                          ? 47.91
                          : 50
              }
              tick={{
                fill: '#cccccc',
                fontSize: id === 'debt' || id === 'inflation' ? 18.73 : 16,
                fontWeight: id === 'debt' ? 400 : 600,
              }}
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
                      <PointDetails
                        key={s.id}
                        p={s.points.find((p) => (p.axisKey || p.key) === String(label))}
                        series={s}
                      />
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
                    radius={s.stack ? undefined : 4}
                    stackId={s.stack}
                    maxBarSize={id === 'expenditure' ? 37 : id === 'gst' ? 34.78 : 25.4254}
                    isAnimationActive={false}
                  >
                    <LabelList
                      content={(props) => {
                        const key = data[Number(props.index)]?.key;
                        const point = s.points.find((p) => (p.axisKey || p.key) === key);
                        if (point?.value == null) return null;
                        const x = Number(props.x) + Number(props.width) / 2;
                        const y = s.stack
                          ? Number(props.y) + Number(props.height) / 2 + 3
                          : Number(point.value) < 0
                            ? Number(props.y) + Number(props.height) + 11
                            : Number(props.y) - 5;
                        return (
                          <text
                            x={x}
                            y={y}
                            textAnchor="middle"
                            fill="#cccccc"
                            fontSize={id === 'expenditure' ? 15 : 16}
                            fontWeight={600}
                          >
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
                    stroke={
                      id === 'debt'
                        ? '#0FCBFF'
                        : id === 'inflation'
                          ? `url(#${id}-reference-line)`
                          : colors[s.color]
                    }
                    fill={
                      id === 'inflation'
                        ? 'none'
                        : id === 'debt'
                          ? `url(#${id}-debt-area)`
                          : `url(#${id}-${s.color})`
                    }
                    fillOpacity={id === 'debt' ? 1 : 0.24}
                    strokeWidth={id === 'inflation' ? 3.51 : 2}
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
