import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { scaleLinear, scaleSqrt } from 'd3-scale';
import { colors, fieldColor } from '../lib/theme';
import { percent } from '../lib/format';
import type { CutoffPoint, FieldProfile } from '../lib/payload';
import { AxisTitle, XAxis, YGrid } from './axes';

const WIDTH = 900;
const HEIGHT = 430;
const MARGIN = { top: 26, right: 132, bottom: 52, left: 56 };
const LABEL_GAP = 15;
const SPRING = { type: 'spring', stiffness: 200, damping: 28 } as const;

/**
 * One global confidence cutoff, applied to every field at once. Each bubble is
 * a field: how much of it gets auto-approved, and how much of what slipped
 * through is wrong. The same number lands in a completely different place
 * depending on the field.
 */
export function CutoffScatter({
  fields,
  points,
  maxErrorRate,
}: {
  fields: FieldProfile[];
  points: Record<string, CutoffPoint>;
  maxErrorRate: number;
}) {
  const x = scaleLinear().domain([0, 1]).range([MARGIN.left, WIDTH - MARGIN.right]);
  const y = scaleLinear().domain([0, maxErrorRate]).range([HEIGHT - MARGIN.bottom, MARGIN.top]);
  const r = scaleSqrt().domain([0, 3000]).range([0, 32]);

  // Bubbles pile up wherever fields share a cutoff outcome, so labels are
  // pushed apart vertically and joined back to their bubble with a leader.
  const placed = useMemo(() => {
    const laid = fields
      .map((field) => {
        const point = points[field.field];
        const radius = Math.max(r(point.nAuto), 4);
        return {
          field,
          point,
          radius,
          cx: x(point.stpRate),
          cy: y(Math.min(point.errorRate ?? 0, maxErrorRate)),
        };
      })
      .sort((a, b) => a.cy - b.cy);

    let lowest = -Infinity;
    return laid.map((entry) => {
      const labelY = Math.max(entry.cy, lowest + LABEL_GAP);
      lowest = labelY;
      return { ...entry, labelY, labelX: entry.cx + entry.radius + 9 };
    });
  }, [fields, points, x, y, r, maxErrorRate]);

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Field risk under a single global cutoff">
      <YGrid
        scale={y}
        ticks={y.ticks(5)}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => percent(value)}
      />

      {placed.map((entry) => {
        const color = fieldColor(entry.field.field);
        const empty = entry.point.nAuto === 0;
        return (
          <g key={entry.field.field}>
            <motion.line
              animate={{
                x1: entry.cx + entry.radius + 2,
                y1: entry.cy,
                x2: entry.labelX - 4,
                y2: entry.labelY,
              }}
              transition={SPRING}
              stroke={color}
              strokeWidth={1}
              opacity={empty ? 0.25 : 0.5}
            />
            <motion.circle
              animate={{ cx: entry.cx, cy: entry.cy, r: entry.radius }}
              transition={SPRING}
              fill={color}
              opacity={empty ? 0.12 : 0.28}
            />
            <motion.circle
              animate={{ cx: entry.cx, cy: entry.cy, r: entry.radius }}
              transition={SPRING}
              fill="none"
              stroke={color}
              strokeWidth={2}
              opacity={empty ? 0.3 : 0.9}
            />
            <motion.text
              className="series-label"
              animate={{ x: entry.labelX, y: entry.labelY }}
              transition={SPRING}
              dy="0.32em"
              fill={color}
              opacity={empty ? 0.45 : 1}
            >
              {entry.field.label}
            </motion.text>
          </g>
        );
      })}

      <XAxis
        scale={x}
        ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
        y={HEIGHT - MARGIN.bottom}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => percent(value)}
      />
      <AxisTitle x={(MARGIN.left + WIDTH - MARGIN.right) / 2} y={HEIGHT - 8}>
        Share of the field auto-approved
      </AxisTitle>
      <AxisTitle x={16} y={(MARGIN.top + HEIGHT - MARGIN.bottom) / 2} rotate>
        Wrong values that slipped through
      </AxisTitle>
      <text x={WIDTH - MARGIN.right} y={MARGIN.top - 10} textAnchor="end" fill={colors.inkMuted}>
        bubble size = number of values auto-approved
      </text>
    </svg>
  );
}
