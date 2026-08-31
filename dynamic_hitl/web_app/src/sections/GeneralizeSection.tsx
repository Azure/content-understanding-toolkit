import { useMemo } from 'react';
import { Card, Legend, Metric, Section } from '../components/ui';
import { DialTracking } from '../charts/DialTracking';
import { Frontier } from '../charts/Frontier';
import { engines, fields, meta, payload, targetIndex, type EngineName } from '../lib/payload';
import { percent } from '../lib/format';
import { colors } from '../lib/theme';

export function GeneralizeSection({ target, engine }: { target: number; engine: EngineName }) {
  const index = targetIndex(target);
  const measured = engines[engine].measured;
  const point = measured.portfolio[index];

  // Fields with a handful of auto-approved values swing wildly, so they do not
  // get to claim the headline.
  const worst = useMemo(() => {
    let top: { label: string; rate: number } | null = null;
    for (const field of fields) {
      const entry = measured.perField[field.field]?.[index];
      if (!entry || entry.stpErrorRate === null || entry.nAuto < 10) continue;
      if (!top || entry.stpErrorRate > top.rate) top = { label: field.label, rate: entry.stpErrorRate };
    }
    return top;
  }, [measured, index]);

  return (
    <Section
      id="generalize"
      step="05 · Does it hold up?"
      title={`Frozen policy, ${meta.documents.test} receipts it had never seen.`}
      lede="Every cutoff above was chosen from training receipts only. These are the results on documents that were never involved in choosing them."
    >
      <div className="grid-3">
        <Metric hero label="Auto-approved" value={percent(point.autoApproveRate, 1)} />
        <Metric
          hero
          label="Mistakes caught"
          value={percent(point.catch, 1)}
          color={colors.filledSaved}
        />
        <Metric
          hero
          label="Wrong, and waved through"
          value={percent(point.stpErrorRate, 1)}
          color={colors.mistake}
        />
      </div>

      <div className="grid-2">
        <Card
          title="Does the dial behave like a dial?"
          sub="Ask for more coverage, get more coverage — on documents the policy never touched. The green line is the one the target governs; it sits just under the diagonal because each cutoff is the most aggressive one that cleared the target on the training split."
        >
          <DialTracking portfolio={measured.portfolio} target={target} />
          <Legend
            items={[
              { label: 'Everything together', color: colors.amber, line: true },
              { label: 'Only fields given a cutoff', color: colors.filledSaved, line: true },
              { label: 'Exactly what you asked for', color: colors.inkMuted, line: true },
            ]}
          />
          {worst ? (
            <p className="metric__note" style={{ marginTop: 10 }}>
              What the dial does not set is how wrong the auto-approved values are:{' '}
              {percent(point.stpErrorRate, 1)} of them are mistakes overall, but{' '}
              <b>{worst.label}</b> alone runs at {percent(worst.rate, 1)}. Read that per field
              before you ship a target.
            </p>
          ) : null}
        </Card>

        <Card
          title="Better than one cutoff for everything?"
          sub="Same unseen receipts, same axes, so the higher line wins. The gap is mostly the blank track: a single cutoff has to price a blank and a filled-in value with the same number, and cannot."
        >
          <Frontier policy={measured.portfolio} naive={payload.naiveFrontier} target={target} />
          <Legend
            items={[
              { label: 'Per-field policy', color: colors.filledSaved, line: true },
              { label: 'One global cutoff', color: colors.reviewedDeep, line: true },
            ]}
          />
          <p className="metric__note" style={{ marginTop: 10 }}>
            Give the single cutoff that same blank track and the two lines nearly meet. Separating
            blanks from filled-in values is what buys the automation here; the per-field cutoffs
            mostly decide <em>which</em> fields are allowed to have one.
          </p>
        </Card>
      </div>
    </Section>
  );
}
