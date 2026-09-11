import { motion } from 'framer-motion';
import { colors } from '../lib/theme';
import { percent } from '../lib/format';
import type { ExpectedFieldPoint, FieldProfile } from '../lib/payload';

const WIDTH = 900;
const ROW = 34;
const LABEL_WIDTH = 148;
const RIGHT = 74;
const TOP = 22;

const SPRING = { type: 'spring', stiffness: 240, damping: 30 } as const;

/**
 * One stacked bar per field, showing where that field's values end up. Fields
 * whose confidence failed the signal gate can only save on their blank values.
 */
export function FieldBars({
  fields,
  points,
  cutoffs,
}: {
  fields: FieldProfile[];
  points: Record<string, ExpectedFieldPoint>;
  cutoffs: Record<string, { cutoff: number | null; blankAutoApproved: boolean }>;
}) {
  const height = TOP + fields.length * ROW + 26;
  const barWidth = WIDTH - LABEL_WIDTH - RIGHT;

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label="Per-field routing composition">
      {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
        <g key={tick}>
          <line
            className="grid-line"
            x1={LABEL_WIDTH + tick * barWidth}
            x2={LABEL_WIDTH + tick * barWidth}
            y1={TOP - 8}
            y2={TOP + fields.length * ROW - 6}
          />
          <text x={LABEL_WIDTH + tick * barWidth} y={TOP + fields.length * ROW + 12} textAnchor="middle">
            {percent(tick)}
          </text>
        </g>
      ))}

      {fields.map((field, index) => {
        const point = points[field.field];
        const total = point.nTotal;
        const segments = [
          { key: 'blank', value: point.blankSaved, color: colors.blankSaved },
          { key: 'filled', value: point.filledSaved, color: colors.filledSaved },
          { key: 'reviewed', value: point.reviewed, color: colors.reviewed },
        ];
        const y = TOP + index * ROW;
        let offset = 0;
        const cutoff = cutoffs[field.field];

        return (
          <g key={field.field}>
            <text x={LABEL_WIDTH - 12} y={y + 11} dy="0.32em" textAnchor="end" fill={colors.ink} fontWeight={600}>
              {field.label}
            </text>
            {segments.map((segment) => {
              const width = (segment.value / total) * barWidth;
              const x = LABEL_WIDTH + offset;
              offset += width;
              return (
                <motion.rect
                  key={segment.key}
                  y={y}
                  height={22}
                  rx={3}
                  fill={segment.color}
                  animate={{ x, width: Math.max(width, 0) }}
                  transition={SPRING}
                />
              );
            })}
            <text
              className="value-label"
              x={WIDTH - RIGHT + 10}
              y={y + 11}
              dy="0.32em"
              fill={colors.inkMuted}
            >
              {cutoff.cutoff === null ? 'no cutoff' : `≥ ${cutoff.cutoff.toFixed(2)}`}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
