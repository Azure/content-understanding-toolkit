import { useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import { area, curveMonotoneX } from 'd3-shape';
import { colors } from '../lib/theme';
import { percent } from '../lib/format';
import type { ExpectedPortfolioPoint } from '../lib/payload';
import { AxisTitle, XAxis, YGrid } from './axes';

const WIDTH = 900;
const HEIGHT = 400;
const MARGIN = { top: 18, right: 168, bottom: 46, left: 52 };

type Band = { key: 'blankSaved' | 'filledSaved' | 'reviewed'; label: string; color: string };

const BANDS: Band[] = [
  { key: 'blankSaved', label: 'Blank → auto-approved', color: colors.blankSaved },
  { key: 'filledSaved', label: 'Filled-in → auto-approved', color: colors.filledSaved },
  { key: 'reviewed', label: 'Still reviewed by a person', color: colors.reviewed },
];

/**
 * Stacked composition of the entire review workload across every coverage
 * target, with a marker at the one currently selected. The two coloured bands
 * are the savings; the grey band is what a person still has to look at.
 */
export function CompositionArea({
  portfolio,
  target,
}: {
  portfolio: ExpectedPortfolioPoint[];
  target: number;
}) {
  const x = scaleLinear()
    .domain([portfolio[0].target, portfolio[portfolio.length - 1].target])
    .range([MARGIN.left, WIDTH - MARGIN.right]);
  const y = scaleLinear().domain([0, 1]).range([HEIGHT - MARGIN.bottom, MARGIN.top]);

  const paths = useMemo(() => {
    const generator = area<ExpectedPortfolioPoint>()
      .x((point) => x(point.target))
      .curve(curveMonotoneX);
    return BANDS.map((band) => ({
      band,
      path:
        generator
          .y0((point) => y(cumulative(point, band.key, false)))
          .y1((point) => y(cumulative(point, band.key, true)))(portfolio) ?? '',
    }));
  }, [portfolio, x, y]);

  const current = portfolio.find((point) => Math.abs(point.target - target) < 1e-9) ?? portfolio[0];
  const markerX = x(current.target);

  const labelPositions = [
    { band: BANDS[0], value: current.blankSaved / 2 },
    { band: BANDS[1], value: current.blankSaved + current.filledSaved / 2 },
    { band: BANDS[2], value: current.blankSaved + current.filledSaved + current.reviewed / 2 },
  ];
  const labelValues = [current.blankSaved, current.filledSaved, current.reviewed];

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Review workload composition across coverage targets">
      <YGrid
        scale={y}
        ticks={[0, 0.25, 0.5, 0.75, 1]}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => percent(value)}
      />
      {paths.map(({ band, path }) => (
        <path key={band.key} d={path} fill={band.color} opacity={band.key === 'reviewed' ? 0.5 : 0.9} />
      ))}

      <line
        x1={markerX}
        x2={markerX}
        y1={MARGIN.top}
        y2={HEIGHT - MARGIN.bottom}
        stroke={colors.ink}
        strokeWidth={2}
        strokeDasharray="5 4"
        style={{ transition: 'all 220ms ease' }}
      />
      <circle cx={markerX} cy={MARGIN.top - 6} r={4} fill={colors.ink} style={{ transition: 'all 220ms ease' }} />

      {labelPositions.map(({ band, value }, index) => (
        <g key={band.key} style={{ transition: 'all 220ms ease' }}>
          <line
            x1={markerX}
            x2={WIDTH - MARGIN.right + 12}
            y1={y(value)}
            y2={y(value)}
            stroke={band.color}
            strokeWidth={1}
            opacity={0.45}
          />
          <text
            className="value-label"
            x={WIDTH - MARGIN.right + 18}
            y={y(value)}
            dy="-0.15em"
            fill={index === 2 ? colors.inkMuted : band.color}
          >
            {percent(labelValues[index])}
          </text>
          <text x={WIDTH - MARGIN.right + 18} y={y(value)} dy="1.05em" fill={colors.inkMuted}>
            {band.label}
          </text>
        </g>
      ))}

      <XAxis
        scale={x}
        ticks={[0.5, 0.6, 0.7, 0.8, 0.9, 0.99]}
        y={HEIGHT - MARGIN.bottom}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => percent(value)}
      />
      <AxisTitle x={(MARGIN.left + WIDTH - MARGIN.right) / 2} y={HEIGHT - 6}>
        Share of mistakes review must catch
      </AxisTitle>
      <AxisTitle x={14} y={(MARGIN.top + HEIGHT - MARGIN.bottom) / 2} rotate>
        Share of all field values
      </AxisTitle>
    </svg>
  );
}

function cumulative(point: ExpectedPortfolioPoint, key: Band['key'], inclusive: boolean): number {
  const order: Band['key'][] = ['blankSaved', 'filledSaved', 'reviewed'];
  const stop = order.indexOf(key) + (inclusive ? 1 : 0);
  return order.slice(0, stop).reduce((sum, name) => sum + point[name], 0);
}
