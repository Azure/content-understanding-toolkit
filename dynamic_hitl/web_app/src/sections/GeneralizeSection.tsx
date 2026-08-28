import { Card, Legend, Metric, Section } from '../components/ui';
import { DialTracking } from '../charts/DialTracking';
import { Frontier } from '../charts/Frontier';
import { engines, meta, payload, targetIndex, type EngineName } from '../lib/payload';
import { count, percent } from '../lib/format';
import { colors } from '../lib/theme';

export function GeneralizeSection({ target, engine }: { target: number; engine: EngineName }) {
  const index = targetIndex(target);
  const measured = engines[engine].measured;
  const point = measured.portfolio[index];

  return (
    <Section
      id="generalize"
      step="05 · Does it hold up?"
      title={`Frozen policy, ${meta.documents.test} receipts it had never seen.`}
      lede="Every cutoff above was chosen from training receipts only. These are the results on documents that were never involved in choosing them."
    >
      <div className="grid-3">
        <Metric
          hero
          label="Auto-approved"
          value={percent(point.autoApproveRate, 1)}
          note={`of ${count(meta.observations.test)} unseen values`}
        />
        <Metric
          hero
          label="Mistakes caught"
          value={percent(point.catch, 1)}
          color={point.catch >= target ? colors.filledSaved : colors.amber}
          note={`you asked for ${percent(target)}`}
        />
        <Metric
          hero
          label="Wrong, and waved through"
          value={percent(point.stpErrorRate, 1)}
          color={colors.mistake}
          note={`${count(point.mistakesSlipped)} of ${count(point.totalMistakes)} mistakes`}
        />
      </div>

      <div className="grid-2">
        <Card
          title="Does the dial behave like a dial?"
          sub="Ask for more coverage, get more coverage — on documents the policy never touched."
        >
          <DialTracking portfolio={measured.portfolio} target={target} />
          <Legend
            items={[
              { label: 'Everything together', color: colors.amber, line: true },
              { label: 'Only fields given a cutoff', color: colors.filledSaved, line: true },
              { label: 'Exactly what you asked for', color: colors.inkMuted, line: true },
            ]}
          />
        </Card>

        <Card
          title="Better than one cutoff for everything?"
          sub="Same unseen receipts, same axes. Automating more always catches less, so the higher line wins."
        >
          <Frontier policy={measured.portfolio} naive={payload.naiveFrontier} target={target} />
          <Legend
            items={[
              { label: 'Per-field policy', color: colors.filledSaved, line: true },
              { label: 'One global cutoff', color: colors.reviewedDeep, line: true },
            ]}
          />
        </Card>
      </div>
    </Section>
  );
}
