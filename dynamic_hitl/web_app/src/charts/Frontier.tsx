import { motion } from 'framer-motion';
import { scaleLinear } from 'd3-scale';
import { line, curveMonotoneX } from 'd3-shape';
import { colors } from '../lib/theme';
import { percent } from '../lib/format';
import type { FrontierPoint, MeasuredPortfolioPoint } from '../lib/payload';
import { AxisTitle, XAxis, YGrid } from './axes';

const WIDTH = 460;
const HEIGHT = 400;
const MARGIN = { top: 22, right: 22, bottom: 54, left: 52 };
const SPRING = { type: 'spring', stiffness: 240, damping: 30 } as const;

/**
 * Both approaches on the same unseen documents and the same axes. Automating
 * more always catches less, so the better approach is simply the higher line.
 */
export function Frontier({
  policy,
  naive,
  target,
}: {
  policy: MeasuredPortfolioPoint[];
  naive: FrontierPoint[];
  target: number;
}) {
  const lowest = Math.min(...policy.map((point) => point.autoApproveRate));
  const highest = Math.max(...policy.map((point) => point.autoApproveRate));
  const domain: [number, number] = [Math.max(lowest - 0.04, 0), Math.min(highest + 0.04, 1)];

  const x = scaleLinear().domain(domain).range([MARGIN.left, WIDTH - MARGIN.right]);
  const y = scaleLinear().domain([0.4, 1]).range([HEIGHT - MARGIN.bottom, MARGIN.top]);

  const visibleNaive = naive.filter(
    (point) => point.stpRate >= domain[0] - 0.02 && point.stpRate <= domain[1] + 0.02,
  );

  const policyPath =
    line<MeasuredPortfolioPoint>()
      .x((point) => x(point.autoApproveRate))
      .y((point) => y(Math.max(point.catch, 0.4)))
      .curve(curveMonotoneX)([...policy].sort((a, b) => a.autoApproveRate - b.autoApproveRate)) ?? '';

  const naivePath =
    line<FrontierPoint>()
      .x((point) => x(point.stpRate))
      .y((point) => y(Math.max(point.catch, 0.4)))
      .curve(curveMonotoneX)([...visibleNaive].sort((a, b) => a.stpRate - b.stpRate)) ?? '';

  const current = policy.find((point) => Math.abs(point.target - target) < 1e-9) ?? policy[0];

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Per-field policy compared with a single global cutoff">
      <YGrid
        scale={y}
        ticks={[0.4, 0.6, 0.8, 1]}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => percent(value)}
      />
      <path d={naivePath} fill="none" stroke={colors.reviewedDeep} strokeWidth={3} strokeDasharray="6 4" />
      <path d={policyPath} fill="none" stroke={colors.filledSaved} strokeWidth={3.5} />

      <motion.circle
        animate={{ cx: x(current.autoApproveRate), cy: y(Math.max(current.catch, 0.4)) }}
        transition={SPRING}
        r={6}
        fill="#ffffff"
        stroke={colors.filledSaved}
        strokeWidth={3.5}
      />

      <XAxis
        scale={x}
        ticks={x.ticks(4)}
        y={HEIGHT - MARGIN.bottom}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => percent(value)}
      />
      <AxisTitle x={(MARGIN.left + WIDTH - MARGIN.right) / 2} y={HEIGHT - 8}>
        Share auto-approved
      </AxisTitle>
      <AxisTitle x={14} y={(MARGIN.top + HEIGHT - MARGIN.bottom) / 2} rotate>
        Mistakes review still caught
      </AxisTitle>
    </svg>
  );
}
