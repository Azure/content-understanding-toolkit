import { motion } from 'framer-motion';
import { colors } from '../lib/theme';

const WIDTH = 900;
const HEIGHT = 250;

const PREDICTORS = [
  { label: 'CU confidence', available: true },
  { label: 'Page / scan quality', available: false },
  { label: 'Vendor or template', available: false },
  { label: 'Cross-field checks', available: false },
  { label: 'Value length & format', available: false },
];

/**
 * Why the logistic form is worth keeping: it is the slot every additional
 * predictor of correctness plugs into. Today only one wire is connected.
 */
export function PredictorDiagram() {
  const rowHeight = 38;
  const top = (HEIGHT - PREDICTORS.length * rowHeight) / 2 + 12;
  const hubX = 540;
  const hubY = HEIGHT / 2;

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Predictors feeding a probability of correctness">
      {PREDICTORS.map((predictor, index) => {
        const y = top + index * rowHeight;
        const path = `M330,${y} C420,${y} 460,${hubY} ${hubX - 62},${hubY}`;
        return (
          <g key={predictor.label} opacity={predictor.available ? 1 : 0.42}>
            <rect
              x={64}
              y={y - 14}
              width={266}
              height={28}
              rx={14}
              fill={predictor.available ? 'rgba(0,120,212,0.1)' : '#ffffff'}
              stroke={predictor.available ? colors.blankSaved : colors.line}
              strokeWidth={1.4}
              strokeDasharray={predictor.available ? undefined : '5 4'}
            />
            <text
              x={197}
              y={y}
              dy="0.32em"
              textAnchor="middle"
              fill={predictor.available ? colors.blankSaved : colors.inkMuted}
              fontWeight={600}
              fontSize={12.5}
            >
              {predictor.label}
            </text>
            <path
              d={path}
              fill="none"
              stroke={predictor.available ? colors.blankSaved : colors.line}
              strokeWidth={1.6}
              strokeDasharray={predictor.available ? undefined : '5 4'}
              opacity={predictor.available ? 0.45 : 1}
            />
            {predictor.available ? (
              <motion.circle
                r={3.5}
                fill={colors.blankSaved}
                style={{ offsetPath: `path("${path}")` }}
                initial={{ offsetDistance: '0%' }}
                animate={{ offsetDistance: '100%', opacity: [0, 1, 1, 0] }}
                transition={{ duration: 2.2, repeat: Infinity, ease: 'linear' }}
              />
            ) : null}
          </g>
        );
      })}

      <rect x={hubX - 62} y={hubY - 30} width={150} height={60} rx={12} fill="#ffffff" stroke={colors.accent} strokeWidth={1.8} />
      <text x={hubX + 13} y={hubY - 6} textAnchor="middle" fill={colors.accent} fontWeight={700} fontSize={13}>
        Logistic model
      </text>
      <text x={hubX + 13} y={hubY + 13} textAnchor="middle" fill={colors.inkMuted} fontSize={11.5}>
        one score, many inputs
      </text>

      <path d={`M${hubX + 88},${hubY} L${hubX + 146},${hubY}`} fill="none" stroke={colors.accent} strokeWidth={1.8} opacity={0.5} />
      <rect x={hubX + 146} y={hubY - 30} width={172} height={60} rx={12} fill="rgba(16,124,16,0.08)" stroke={colors.filledSaved} strokeWidth={1.8} />
      <text x={hubX + 232} y={hubY - 6} textAnchor="middle" fill={colors.filledSaved} fontWeight={700} fontSize={13}>
        P(correct)
      </text>
      <text x={hubX + 232} y={hubY + 13} textAnchor="middle" fill={colors.inkMuted} fontSize={11.5}>
        thresholded by your dial
      </text>
    </svg>
  );
}
