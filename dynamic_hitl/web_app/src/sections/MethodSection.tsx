import { useMemo, useState } from 'react';
import { Card, Legend, Pills, Section, Slider } from '../components/ui';
import { FlowDiagram } from '../charts/FlowDiagram';
import { SignalGates, type GateRow } from '../charts/SignalGates';
import { ConfidenceOverlap } from '../charts/ConfidenceOverlap';
import { fields, meta, payload } from '../lib/payload';
import { count, decimal, percent } from '../lib/format';
import { colors } from '../lib/theme';

export function MethodSection({ target }: { target: number }) {
  const [selected, setSelected] = useState(fields[0].field);
  const field = fields.find((entry) => entry.field === selected) ?? fields[0];

  const { documentCounts, perField } = payload.signalVsVolume;
  const [volumeIndex, setVolumeIndex] = useState(documentCounts.length - 1);
  const documents = documentCounts[volumeIndex];

  const rows: GateRow[] = useMemo(
    () =>
      fields.map((entry) => {
        const point = perField[entry.field][volumeIndex];
        return {
          field: entry.field,
          label: entry.label,
          filled: {
            point: point.auc,
            low: point.aucLow,
            high: point.aucHigh,
            passes: point.usable,
            format: (value: number) => decimal(value, 2),
          },
          blank: {
            point: point.blankPrecision,
            low: point.blankLow,
            high: point.blankHigh,
            passes: point.blankLow !== null && point.blankLow >= target,
            format: (value: number) => percent(value),
          },
        };
      }),
    [perField, volumeIndex, target],
  );

  // Fixed across the whole sweep so the axis does not jump as the slider moves.
  const filledDomain = useMemo<[number, number]>(() => {
    let low = 0.5;
    let high = 0.5;
    for (const series of Object.values(perField)) {
      for (const point of series) {
        if (point.aucLow === null || point.aucHigh === null) continue;
        low = Math.min(low, point.aucLow);
        high = Math.max(high, point.aucHigh);
      }
    }
    return [Math.floor(low * 20) / 20, Math.ceil(high * 20) / 20];
  }, [perField]);

  const filledCount = rows.filter((row) => row.filled.passes).length;
  const blankCount = rows.filter((row) => row.blank.passes).length;

  return (
    <Section
      id="method"
      step="03 · What to do instead"
      title="Test each field. Then route it."
      lede="Two tracks, because blank values and filled-in values carry completely different evidence."
    >
      <Card flush>
        <FlowDiagram />
      </Card>

      <Card
        title="Which fields have evidence worth trusting?"
        sub="Measured on training receipts only, with a 95% interval. The whole interval must clear that track's bar before the field earns an automatic decision — a filled-in value needs confidence that beats a coin flip, a blank needs to be genuinely blank as often as your coverage target demands."
      >
        <div style={{ padding: '8px 0 20px', maxWidth: 460 }}>
          <Slider
            label="Labeled documents measured"
            value={volumeIndex}
            min={0}
            max={documentCounts.length - 1}
            step={1}
            onChange={setVolumeIndex}
            format={() => count(documents)}
            scale={[
              `${documentCounts[0]} docs`,
              `${documentCounts[documentCounts.length - 1]} docs`,
            ]}
          />
        </div>
        <SignalGates
          rows={rows}
          filledGate={meta.minAucCiLower}
          filledDomain={filledDomain}
          blankGate={target}
          blankLabel={`${percent(target)} target`}
        />
        <p className="metric__note" style={{ marginTop: 10 }}>
          This is what labeled volume buys you: the measurement never changes, only how sure you
          can be of it. At {count(documents)} documents,{' '}
          <b>{filledCount} of {fields.length} fields</b> clear the bar on filled-in values and{' '}
          <b>{blankCount} of {fields.length}</b> clear it on blanks — at the low end the intervals
          are so wide that nothing qualifies, and the sparse fields cannot be measured at all. Thin
          data never makes the policy riskier; it just leaves more fields in full review until the
          evidence arrives.
        </p>
      </Card>

      <Card
        title="Why the bar is set that low"
        sub="Confidence scores for correct values and for mistakes sit almost on top of one another."
      >
        <Pills
          options={fields.map((entry) => ({ value: entry.field, label: entry.label }))}
          value={selected}
          onChange={setSelected}
        />
        <div style={{ marginTop: 12 }}>
          <ConfidenceOverlap distribution={payload.confidenceDistribution} field={selected} />
        </div>
        <Legend
          items={[
            { label: 'Correct values', color: colors.filledSaved },
            { label: 'Mistakes', color: colors.mistake },
          ]}
        />
        <p className="metric__note" style={{ marginTop: 12 }}>
          {field.label}: confidence ranks a correct value above a wrong one{' '}
          <b>{percent(field.auc, 1)}</b> of the time (interval {decimal(field.aucLow, 2)}–
          {decimal(field.aucHigh, 2)}).{' '}
          {field.confidenceIsUsable
            ? 'Weak, but real — enough to earn a cutoff.'
            : 'Not distinguishable from chance, so every value goes to review.'}
        </p>
      </Card>

      <div className="callout">
        <b>Blank values get their own test.</b> {percent(meta.blankShare)} of everything Content
        Understanding returned was blank, all carrying the same placeholder confidence — no cutoff
        can sort them. So the blank-values panel above asks a different question entirely: not
        whether confidence ranks a blank, but how often a blank turns out to be genuinely blank.
        Each field's blanks get one on/off switch, and it only flips when the whole interval clears
        your coverage target.
      </div>
    </Section>
  );
}
