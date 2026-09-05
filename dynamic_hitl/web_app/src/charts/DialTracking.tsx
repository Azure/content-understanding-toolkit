import { motion } from 'framer-motion';
import { scaleLinear } from 'd3-scale';
import { line, curveMonotoneX } from 'd3-shape';
import { colors } from '../lib/theme';
import { percent } from '../lib/format';
import type { MeasuredPortfolioPoint } from '../lib/payload';
import { AxisTitle, XAxis, YGrid } from './axes';

const WIDTH = 460;
const HEIGHT = 400;
const MARGIN = { top: 22, right: 22, bottom: 54, left: 52 };
const SPRING = { type: 'spring', stiffness: 240, damping: 30 } as const;

/**
 * What you asked for against what the frozen policy actually delivered on
 * documents it never saw. Points near the diagonal mean the dial is honest.
 */
export function DialTracking({
  portfolio,
  target,
}: {
  portfolio: MeasuredPortfolioPoint[];
  target: number;
}) {
  const x = scaleLinear().domain([0.5, 0.99]).range([MARGIN.left, WIDTH - MARGIN.right]);
  const y = scaleLinear().domain([0.4, 1]).range([HEIGHT - MARGIN.bottom, MARGIN.top]);

  const build = (key: 'catch' | 'calibratedCatch') =>
    line<MeasuredPortfolioPoint>()
      .defined((point) => point[key] !== null)
      .x((point) => x(point.target))
      .y((point) => y(Math.max(point[key] ?? 0, 0.4)))
      .curve(curveMonotoneX)(portfolio) ?? '';

  const current = portfolio.find((point) => Math.abs(point.target - target) < 1e-9) ?? portfolio[0];

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Requested versus delivered error coverage on unseen documents">
      <YGrid
        scale={y}
        ticks={[0.4, 0.6, 0.8, 1]}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => percent(value)}
      />
      <line
        x1={x(0.5)}
        y1={y(0.5)}
        x2={x(0.99)}
        y2={y(0.99)}
        stroke={colors.inkMuted}
        strokeWidth={1.5}
        strokeDasharray="5 5"
        opacity={0.6}
      />
      <text x={x(0.78)} y={y(0.74)} fill={colors.inkMuted} transform={`rotate(-34 ${x(0.78)} ${y(0.74)})`}>
        exactly what you asked for
      </text>

      <path d={build('calibratedCatch')} fill="none" stroke={colors.filledSaved} strokeWidth={2.5} opacity={0.9} />
      <path d={build('catch')} fill="none" stroke={colors.amber} strokeWidth={3.5} />

      <motion.circle
        animate={{ cx: x(current.target), cy: y(Math.max(current.calibratedCatch ?? 0.4, 0.4)) }}
        transition={SPRING}
        r={5}
        fill="#ffffff"
        stroke={colors.filledSaved}
        strokeWidth={3}
      />
      <motion.circle
        animate={{ cx: x(current.target), cy: y(current.catch) }}
        transition={SPRING}
        r={6}
        fill="#ffffff"
        stroke={colors.amber}
        strokeWidth={3.5}
      />

      <XAxis
        scale={x}
        ticks={[0.5, 0.7, 0.9]}
        y={HEIGHT - MARGIN.bottom}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => percent(value)}
      />
      <AxisTitle x={(MARGIN.left + WIDTH - MARGIN.right) / 2} y={HEIGHT - 8}>
        Mistakes you asked review to catch
      </AxisTitle>
      <AxisTitle x={14} y={(MARGIN.top + HEIGHT - MARGIN.bottom) / 2} rotate>
        Mistakes it actually caught
      </AxisTitle>
    </svg>
  );
}
