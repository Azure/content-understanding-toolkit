import { Card, Metric, Legend, Section } from '../components/ui';
import { DotGrid } from '../charts/DotGrid';
import { meta } from '../lib/payload';
import { count, percent } from '../lib/format';
import { colors } from '../lib/theme';

export function CostSection() {
  const total = meta.observations.train;
  const mistakes = meta.trainMistakes;

  return (
    <Section
      id="cost"
      step="01 · The cost"
      title="Right now, a person checks every single value."
      lede="Some of those values are wrong. You just don't know which ones — so you pay to look at all of them."
    >
      <Card flush>
        <DotGrid
          segments={[
            { key: 'wrong', label: 'Wrong', color: colors.mistake, count: mistakes },
            { key: 'right', label: 'Correct', color: colors.reviewed, count: total - mistakes },
          ]}
        />
        <div style={{ padding: '4px 6px 12px' }}>
          <Legend
            items={[
              { label: `${count(mistakes)} values are wrong`, color: colors.mistake },
              { label: `${count(total - mistakes)} are correct — and still reviewed`, color: colors.reviewed },
            ]}
          />
        </div>
      </Card>

      <div className="grid-3">
        <Metric hero label="Values extracted" value={count(total)} note="from 800 training receipts" />
        <Metric
          hero
          label="Actually wrong"
          value={percent(mistakes / total, 1)}
          color={colors.mistake}
          note={`${count(mistakes)} mis-extractions`}
        />
        <Metric hero label="Sent to a human" value="100%" note="the baseline everyone starts from" />
      </div>
    </Section>
  );
}
