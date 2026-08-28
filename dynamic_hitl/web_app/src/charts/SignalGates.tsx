import { motion } from 'framer-motion';
import { scaleLinear, type ScaleLinear } from 'd3-scale';
import { colors } from '../lib/theme';
import { AxisTitle } from './axes';

const WIDTH = 940;
const ROW = 38;
const LABEL_WIDTH = 128;
const TOP = 74;
const PANELS = [
  { x0: 138, x1: 468 },
  { x0: 572, x1: 902 },
] as const;
const SPRING = { type: 'spring', stiffness: 200, damping: 28 } as const;

export interface GateRow {
  field: string;
  label: string;
  /** Filled-in track: how well confidence ranks correct values above wrong ones. */
  filled: Measurement;
  /** Blank track: how often a blank extraction was genuinely blank. */
  blank: Measurement;
}

export interface Measurement {
  point: number | null;
  low: number | null;
  high: number | null;
  passes: boolean;
  format: (value: number) => string;
}

/**
 * Both routing tracks, measured side by side on the same fields. Each row is a
 * field and each bar its 95% interval; a track only earns an automatic decision
 * for a field when the whole interval clears that track's bar. The two tracks
 * are judged on different quantities, so each panel carries its own axis.
 */
export function SignalGates({
  rows,
  filledGate,
  filledDomain,
  blankGate,
  blankLabel,
}: {
  rows: GateRow[];
  filledGate: number;
  filledDomain: [number, number];
  blankGate: number;
  blankLabel: string;
}) {
  const height = TOP + rows.length * ROW + 46;
  const bottom = TOP + rows.length * ROW - 12;
  const scales = [
    scaleLinear().domain(filledDomain).range([PANELS[0].x0, PANELS[0].x1]),
    scaleLinear().domain([0, 1]).range([PANELS[1].x0, PANELS[1].x1]),
  ];

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${WIDTH} ${height}`}
      role="img"
      aria-label="Per-field signal strength for the filled-in and blank tracks"
    >
      <Panel
        index={0}
        scale={scales[0]}
        bottom={bottom}
        title="Filled-in values"
        gate={filledGate}
        gateLabel="coin flip"
        axisTitle="Confidence ranks a correct value above a wrong one"
      />
      <Panel
        index={1}
        scale={scales[1]}
        bottom={bottom}
        title="Blank values"
        gate={blankGate}
        gateLabel={blankLabel}
        axisTitle="Blanks that were genuinely blank"
        format={(value) => `${Math.round(value * 100)}%`}
      />

      {rows.map((row, index) => {
        const y = TOP + index * ROW;
        return (
          <g key={row.field}>
            <text x={LABEL_WIDTH - 10} y={y} dy="0.32em" textAnchor="end" fill={colors.ink} fontWeight={600}>
              {row.label}
            </text>
            <Interval scale={scales[0]} panel={PANELS[0]} y={y} measurement={row.filled} />
            <Interval scale={scales[1]} panel={PANELS[1]} y={y} measurement={row.blank} />
          </g>
        );
      })}
    </svg>
  );
}

function Panel({
  index,
  scale,
  bottom,
  title,
  gate,
  gateLabel,
  axisTitle,
  format = (value) => value.toFixed(1),
}: {
  index: number;
  scale: ScaleLinear<number, number>;
  bottom: number;
  title: string;
  gate: number;
  gateLabel: string;
  axisTitle: string;
  format?: (value: number) => string;
}) {
  const panel = PANELS[index];
  const middle = (panel.x0 + panel.x1) / 2;
  return (
    <g>
      <text className="axis-title" x={middle} y={16} textAnchor="middle" fill={colors.ink}>
        {title}
      </text>
      {scale.ticks(5).map((tick) => (
        <g key={tick}>
          <line className="grid-line" x1={scale(tick)} x2={scale(tick)} y1={TOP - 12} y2={bottom} />
          <text x={scale(tick)} y={bottom + 20} textAnchor="middle">
            {format(tick)}
          </text>
        </g>
      ))}
      <line x1={scale(gate)} x2={scale(gate)} y1={TOP - 20} y2={bottom} stroke={colors.mistake} strokeWidth={2} />
      <text className="series-label" x={scale(gate)} y={TOP - 28} textAnchor="middle" fill={colors.mistake}>
        {gateLabel}
      </text>
      <AxisTitle x={middle} y={bottom + 44}>
        {axisTitle}
      </AxisTitle>
    </g>
  );
}

function Interval({
  scale,
  panel,
  y,
  measurement,
}: {
  scale: ScaleLinear<number, number>;
  panel: { x0: number; x1: number };
  y: number;
  measurement: Measurement;
}) {
  const { point, low, high, passes, format } = measurement;
  if (point === null || low === null || high === null) {
    return (
      <text
        className="value-label"
        x={panel.x0 + 12}
        y={y}
        dy="0.32em"
        fill={colors.inkMuted}
        opacity={0.7}
        stroke="#fff"
        strokeWidth={4}
        paintOrder="stroke"
      >
        Not enough datapoints
      </text>
    );
  }
  const tone = passes ? colors.filledSaved : colors.inkMuted;
  return (
    <>
      <motion.line
        initial={false}
        animate={{ x1: scale(low), x2: scale(high) }}
        transition={SPRING}
        y1={y}
        y2={y}
        stroke={tone}
        strokeWidth={7}
        strokeLinecap="round"
        opacity={passes ? 0.28 : 0.18}
      />
      <motion.circle initial={false} animate={{ cx: scale(point) }} transition={SPRING} cy={y} r={5.5} fill={tone} />
      <text className="value-label" x={panel.x1 + 10} y={y} dy="0.32em" fill={tone}>
        {format(point)}
      </text>
    </>
  );
}
