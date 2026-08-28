import { Card, Section, Toggle } from '../components/ui';
import { PredictorDiagram } from '../charts/PredictorDiagram';
import { engines, targetIndex, type EngineName } from '../lib/payload';
import { percent, points } from '../lib/format';

const ROWS = [
  { label: 'Review avoided', pick: (index: number, engine: EngineName) => engines[engine].expected.portfolio[index].totalSaved },
  { label: 'Auto-approved on unseen receipts', pick: (index: number, engine: EngineName) => engines[engine].measured.portfolio[index].autoApproveRate },
  { label: 'Mistakes caught on unseen receipts', pick: (index: number, engine: EngineName) => engines[engine].measured.portfolio[index].catch },
  { label: 'Wrong values waved through', pick: (index: number, engine: EngineName) => engines[engine].measured.portfolio[index].stpErrorRate ?? 0 },
];

export function GrowSection({
  target,
  engine,
  onEngineChange,
}: {
  target: number;
  engine: EngineName;
  onEngineChange: (engine: EngineName) => void;
}) {
  const index = targetIndex(target);

  return (
    <Section
      id="grow"
      step="06 · Room to grow"
      title="You don't need a model yet. Keep the slot open for one."
      lede="Everything so far thresholded the confidence score directly. Switching to a fitted model changes nothing today — which is exactly the point."
      tint
    >
      <Card
        title="Same policy, two ways of writing the cutoff"
        sub="With confidence as the only input, both engines rank values identically. Flip the switch and watch nothing move."
      >
        <div style={{ marginBottom: 18 }}>
          <Toggle
            layoutId="engine-toggle"
            value={engine}
            onChange={onEngineChange}
            options={[
              { value: 'raw_confidence', label: 'Confidence cutoff' },
              { value: 'logistic', label: 'Fitted P(correct)' },
            ]}
          />
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>At a {percent(target)} coverage target</th>
              <th>Confidence</th>
              <th>P(correct)</th>
              <th>Difference</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => {
              const raw = row.pick(index, 'raw_confidence');
              const logistic = row.pick(index, 'logistic');
              const delta = logistic - raw;
              return (
                <tr key={row.label}>
                  <td>{row.label}</td>
                  <td>{percent(raw, 1)}</td>
                  <td>{percent(logistic, 1)}</td>
                  <td>
                    <span className={`tag ${Math.abs(delta) < 5e-5 ? 'tag--zero' : 'tag--warn'}`}>
                      {points(delta)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <Card
        title="So why keep the model form at all?"
        sub="Because a cutoff on confidence only accepts one input. A fitted score accepts as many as you can measure."
      >
        <PredictorDiagram />
        <p className="metric__note" style={{ marginTop: 8 }}>
          Start with the confidence cutoff — it is simpler to explain and to audit. Move to the
          fitted form the day you can measure a second signal about whether an extraction is right.
          Nothing else in the method changes.
        </p>
      </Card>
    </Section>
  );
}
