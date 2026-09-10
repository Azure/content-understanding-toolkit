import type { ScaleLinear } from 'd3-scale';

export interface Margin {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

/** Horizontal grid lines with percentage labels down the left edge. */
export function YGrid({
  scale,
  ticks,
  x0,
  x1,
  format,
}: {
  scale: ScaleLinear<number, number>;
  ticks: number[];
  x0: number;
  x1: number;
  format: (value: number) => string;
}) {
  return (
    <g>
      {ticks.map((tick) => (
        <g key={tick} transform={`translate(0, ${scale(tick)})`}>
          <line className="grid-line" x1={x0} x2={x1} />
          <text x={x0 - 8} dy="0.32em" textAnchor="end">
            {format(tick)}
          </text>
        </g>
      ))}
    </g>
  );
}

/** Tick labels along the bottom edge, with an axis rule. */
export function XAxis({
  scale,
  ticks,
  y,
  x0,
  x1,
  format,
}: {
  scale: ScaleLinear<number, number>;
  ticks: number[];
  y: number;
  x0: number;
  x1: number;
  format: (value: number) => string;
}) {
  return (
    <g>
      <line className="axis-line" x1={x0} x2={x1} y1={y} y2={y} />
      {ticks.map((tick) => (
        <text key={tick} x={scale(tick)} y={y + 18} textAnchor="middle">
          {format(tick)}
        </text>
      ))}
    </g>
  );
}

export function AxisTitle({
  x,
  y,
  children,
  anchor = 'middle',
  rotate,
}: {
  x: number;
  y: number;
  children: string;
  anchor?: 'start' | 'middle' | 'end';
  rotate?: boolean;
}) {
  return (
    <text
      className="axis-title"
      x={x}
      y={y}
      textAnchor={anchor}
      transform={rotate ? `rotate(-90 ${x} ${y})` : undefined}
    >
      {children}
    </text>
  );
}
