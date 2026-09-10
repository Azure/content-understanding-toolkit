import { useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import { area, curveMonotoneX } from 'd3-shape';
import { colors } from '../lib/theme';
import type { ConfidenceDistribution } from '../lib/payload';
import { AxisTitle, XAxis } from './axes';

const WIDTH = 900;
const HEIGHT = 260;
const MARGIN = { top: 24, right: 24, bottom: 46, left: 24 };

/**
 * Confidence distributions for one field, correct values against mistakes.
 * The overlap is the whole problem: a single cutoff cannot separate two curves
 * that sit on top of one another.
 */
export function ConfidenceOverlap({
  distribution,
  field,
}: {
  distribution: ConfidenceDistribution;
  field: string;
}) {
  const record = distribution.fields.find((entry) => entry.field === field) ?? distribution.fields[0];
  const centers = useMemo(
    () =>
      distribution.binEdges
        .slice(0, -1)
        .map((edge, index) => (edge + distribution.binEdges[index + 1]) / 2),
    [distribution.binEdges],
  );

  const normalize = (counts: number[]) => {
    const total = counts.reduce((sum, value) => sum + value, 0) || 1;
    return counts.map((value) => value / total);
  };

  const correct = normalize(record.correct);
  const incorrect = normalize(record.incorrect);
  const peak = Math.max(...correct, ...incorrect) || 1;

  const x = scaleLinear().domain([0, 1]).range([MARGIN.left, WIDTH - MARGIN.right]);
  const y = scaleLinear().domain([0, peak * 1.12]).range([HEIGHT - MARGIN.bottom, MARGIN.top]);

  const build = (values: number[]) =>
    area<number>()
      .x((_, index) => x(centers[index]))
      .y0(y(0))
      .y1((value) => y(value))
      .curve(curveMonotoneX)(values) ?? '';

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`Confidence distribution for ${record.label}`}>
      <path d={build(correct)} fill={colors.filledSaved} opacity={0.24} />
      <path
        d={build(correct)}
        fill="none"
        stroke={colors.filledSaved}
        strokeWidth={2.5}
        style={{ transition: 'd 260ms ease' }}
      />
      <path d={build(incorrect)} fill={colors.mistake} opacity={0.22} />
      <path d={build(incorrect)} fill="none" stroke={colors.mistake} strokeWidth={2.5} />

      <XAxis
        scale={x}
        ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
        y={HEIGHT - MARGIN.bottom}
        x0={MARGIN.left}
        x1={WIDTH - MARGIN.right}
        format={(value) => value.toFixed(1)}
      />
      <AxisTitle x={WIDTH / 2} y={HEIGHT - 6}>
        Content Understanding confidence score
      </AxisTitle>
    </svg>
  );
}
