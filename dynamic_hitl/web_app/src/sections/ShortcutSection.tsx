import { useMemo, useState } from 'react';
import { Card, Metric, Section, Slider } from '../components/ui';
import { CutoffScatter } from '../charts/CutoffScatter';
import { fields, payload } from '../lib/payload';
import { percent } from '../lib/format';
import { colors } from '../lib/theme';

export function ShortcutSection() {
  const { cutoffs, perField, overall } = payload.globalCutoff;
  const [index, setIndex] = useState(() => {
    const found = cutoffs.findIndex((value) => value >= 0.7);
    return found === -1 ? 0 : found;
  });

  const points = useMemo(() => {
    const result: Record<string, (typeof perField)[string][number]> = {};
    for (const field of fields) result[field.field] = perField[field.field][index];
    return result;
  }, [perField, index]);

  // Fixed across the whole sweep so the axis does not jump as the cutoff moves.
  // A handful of auto-approved values swings wildly, so those do not set the scale.
  const maxErrorRate = useMemo(() => {
    let highest = 0;
    for (const series of Object.values(perField)) {
      for (const point of series) {
        if (point.errorRate !== null && point.nAuto >= 10) {
          highest = Math.max(highest, point.errorRate);
        }
      }
    }
    return Math.min(Math.ceil(highest * 10) / 10, 1);
  }, [perField]);

  const summary = overall[index];

  return (
    <Section
      id="shortcut"
      step="02 · The tempting shortcut"
      title="Pick one confidence cutoff. Apply it to everything."
      lede="Drag the cutoff and watch the eight fields scatter. The same number means something different in every one of them."
      tint
    >
      <Card flush>
        <div style={{ padding: '0 10px 18px', maxWidth: 460 }}>
          <Slider
            label="Auto-approve anything at or above this confidence"
            value={index}
            min={0}
            max={cutoffs.length - 1}
            step={1}
            onChange={setIndex}
            format={() => cutoffs[index].toFixed(2)}
            scale={['0.00', '1.00']}
          />
        </div>
        <CutoffScatter fields={fields} points={points} maxErrorRate={maxErrorRate} />
      </Card>

      <div className="grid-3">
        <Metric hero label="Auto-approved" value={percent(summary.stpRate)} note="across all fields at once" />
        <Metric
          hero
          label="Wrong, and waved through"
          value={percent(summary.errorRate, 1)}
          color={colors.mistake}
          note="of everything auto-approved"
        />
        <Metric hero label="Mistakes still caught" value={percent(summary.catch)} note="by whatever review is left" />
      </div>
    </Section>
  );
}
