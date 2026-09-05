import { Card, Legend, Metric, Section } from '../components/ui';
import { DotGrid } from '../charts/DotGrid';
import { CompositionArea } from '../charts/CompositionArea';
import { FieldBars } from '../charts/FieldBars';
import { engines, fields, targetIndex, type EngineName } from '../lib/payload';
import { count, percent } from '../lib/format';
import { colors } from '../lib/theme';

const LEGEND = [
  { label: 'Blank → auto-approved', color: colors.blankSaved },
  { label: 'Filled-in → auto-approved', color: colors.filledSaved },
  { label: 'Still reviewed by a person', color: colors.reviewed },
];

export function DialSection({ target, engine }: { target: number; engine: EngineName }) {
  const index = targetIndex(target);
  const expected = engines[engine].expected;
  const point = expected.portfolio[index];
  const perField = Object.fromEntries(
    fields.map((field) => [field.field, expected.perField[field.field][index]]),
  );
  const cutoffs = Object.fromEntries(
    fields.map((field) => [field.field, engines[engine].cutoffs[field.field][index]]),
  );

  return (
    <Section
      id="dial"
      step="04 · Your one dial"
      title="Choose how much of the error review has to catch."
      lede="That single number sets every field's cutoff. Everything below moves with it — drag the dial at the bottom of the screen."
      tint
    >
      <div className="grid-3">
        <Metric
          hero
          label="Review avoided"
          value={percent(point.totalSaved, 1)}
          note={`${count(point.blankSavedCount + point.filledSavedCount)} values never reach a person`}
        />
        <Metric
          hero
          small
          label="From blank values"
          value={percent(point.blankSaved, 1)}
          color={colors.blankSaved}
          note={`${count(point.blankSavedCount)} values`}
        />
        <Metric
          hero
          small
          label="From filled-in values"
          value={percent(point.filledSaved, 1)}
          color={colors.filledSaved}
          note={`${count(point.filledSavedCount)} values · ${point.calibratedFields} of ${fields.length} fields earned a cutoff`}
        />
      </div>

      <Card flush>
        <DotGrid
          segments={[
            { key: 'blank', label: 'Blank → auto-approved', color: colors.blankSaved, count: point.blankSavedCount },
            { key: 'filled', label: 'Filled-in → auto-approved', color: colors.filledSaved, count: point.filledSavedCount },
            { key: 'reviewed', label: 'Still reviewed', color: colors.reviewed, count: point.reviewedCount },
          ]}
        />
        <div style={{ padding: '4px 6px 12px' }}>
          <Legend items={LEGEND} />
        </div>
      </Card>

      <Card
        title="Where the savings come from, across the whole range"
        sub="The blank track is a set of on/off switches; the filled-in track slides continuously with the dial."
      >
        <CompositionArea portfolio={expected.portfolio} target={target} />
      </Card>

      <Card
        title="The same picture, field by field"
        sub="Fields whose confidence failed the signal test can only save on their blanks."
      >
        <FieldBars fields={fields} points={perField} cutoffs={cutoffs} />
        <Legend items={LEGEND} />
      </Card>
    </Section>
  );
}
