import { motion } from 'framer-motion';
import { colors } from '../lib/theme';

const WIDTH = 980;
const HEIGHT = 400;

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  sub?: string;
  tone: string;
  fill?: string;
}

const BOXES: Record<string, Box> = {
  source: { x: 8, y: 160, w: 152, h: 66, title: 'Extracted value', sub: 'value + confidence', tone: colors.ink },
  blank: { x: 236, y: 62, w: 186, h: 72, title: 'Blank track', sub: 'is a blank really blank?', tone: colors.blankSaved },
  gate: { x: 236, y: 254, w: 186, h: 72, title: 'Signal gate', sub: 'does confidence rank?', tone: colors.accent },
  cutoff: { x: 494, y: 296, w: 168, h: 62, title: 'Field cutoff', sub: 'set from your dial', tone: colors.filledSaved },
  auto: { x: 782, y: 118, w: 178, h: 74, title: 'Auto-approved', sub: 'no person involved', tone: colors.filledSaved, fill: 'rgba(16,124,16,0.08)' },
  review: { x: 782, y: 236, w: 178, h: 74, title: 'Human review', sub: 'a person checks it', tone: colors.reviewedDeep, fill: 'rgba(140,150,160,0.1)' },
};

interface Flow {
  id: string;
  d: string;
  color: string;
  label?: { text: string; x: number; y: number };
  dashed?: boolean;
  tokens: number;
}

const FLOWS: Flow[] = [
  {
    id: 'to-blank',
    d: 'M160,182 C200,182 200,98 236,98',
    color: colors.blankSaved,
    label: { text: 'blank', x: 198, y: 128 },
    tokens: 2,
  },
  {
    id: 'to-filled',
    d: 'M160,204 C200,204 200,290 236,290',
    color: colors.accent,
    label: { text: 'filled in', x: 198, y: 258 },
    tokens: 3,
  },
  {
    id: 'blank-auto',
    d: 'M422,88 C560,88 640,148 782,148',
    color: colors.blankSaved,
    label: { text: 'reliably blank', x: 600, y: 100 },
    tokens: 2,
  },
  {
    id: 'blank-review',
    d: 'M422,116 C560,116 640,256 782,256',
    color: colors.reviewedDeep,
    dashed: true,
    tokens: 1,
  },
  {
    id: 'gate-fail',
    d: 'M422,272 C560,272 640,282 782,282',
    color: colors.reviewedDeep,
    label: { text: 'no usable signal → review everything', x: 600, y: 264 },
    dashed: true,
    tokens: 2,
  },
  { id: 'gate-pass', d: 'M422,306 C452,306 464,327 494,327', color: colors.filledSaved, tokens: 2 },
  {
    id: 'cutoff-auto',
    d: 'M662,314 C712,314 720,172 782,172',
    color: colors.filledSaved,
    label: { text: 'above cutoff', x: 726, y: 232 },
    tokens: 2,
  },
  { id: 'cutoff-review', d: 'M662,340 C712,340 720,300 782,300', color: colors.reviewedDeep, dashed: true, tokens: 1 },
];

/** The routing decision, drawn once, with values flowing through it. */
export function FlowDiagram() {
  return (
    <svg
      className="chart"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label="Every extracted value takes one of two tracks: blank values are tested statistically, filled-in values must pass a signal gate before a confidence cutoff can auto-approve them."
    >
      {FLOWS.map((flow) => (
        <g key={flow.id}>
          <path
            d={flow.d}
            fill="none"
            stroke={flow.color}
            strokeWidth={2}
            opacity={0.34}
            strokeDasharray={flow.dashed ? '6 5' : undefined}
          />
          {flow.label ? (
            <text x={flow.label.x} y={flow.label.y} textAnchor="middle" fill={flow.color} fontWeight={600}>
              {flow.label.text}
            </text>
          ) : null}
          {Array.from({ length: flow.tokens }).map((_, index) => (
            <motion.circle
              key={index}
              r={4}
              fill={flow.color}
              style={{ offsetPath: `path("${flow.d}")`, offsetRotate: '0deg' }}
              initial={{ offsetDistance: '0%', opacity: 0 }}
              animate={{ offsetDistance: '100%', opacity: [0, 1, 1, 0] }}
              transition={{
                duration: 2.6,
                repeat: Infinity,
                ease: 'linear',
                delay: index * (2.6 / flow.tokens) + flow.id.length * 0.06,
              }}
            />
          ))}
        </g>
      ))}

      {Object.entries(BOXES).map(([key, box]) => (
        <g key={key}>
          <rect
            x={box.x}
            y={box.y}
            width={box.w}
            height={box.h}
            rx={10}
            fill={box.fill ?? '#ffffff'}
            stroke={box.tone}
            strokeWidth={1.6}
            opacity={0.95}
          />
          <text x={box.x + box.w / 2} y={box.y + (box.sub ? 27 : box.h / 2 + 4)} textAnchor="middle" fill={box.tone} fontWeight={700} fontSize={14}>
            {box.title}
          </text>
          {box.sub ? (
            <text x={box.x + box.w / 2} y={box.y + 47} textAnchor="middle" fill={colors.inkMuted} fontSize={11.5}>
              {box.sub}
            </text>
          ) : null}
        </g>
      ))}
    </svg>
  );
}
