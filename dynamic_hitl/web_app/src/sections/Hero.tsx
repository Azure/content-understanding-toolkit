import { meta } from '../lib/payload';
import { count } from '../lib/format';

export function Hero() {
  return (
    <header className="hero">
      <div className="wrap">
        <div className="hero__brand">
          {/* Official mark geometry: four 10-unit squares on a 1-unit gutter. */}
          <svg className="hero__logo" viewBox="0 0 21 21" aria-hidden="true" focusable="false">
            <rect x="0" y="0" width="10" height="10" fill="#f25022" />
            <rect x="11" y="0" width="10" height="10" fill="#7fba00" />
            <rect x="0" y="11" width="10" height="10" fill="#00a4ef" />
            <rect x="11" y="11" width="10" height="10" fill="#ffb900" />
          </svg>
          Microsoft
          <span className="hero__divider" />
          Azure AI Content Understanding
        </div>

        <h1 className="hero__title">
          Stop reviewing <em>everything</em>.
        </h1>
        <p className="hero__lede">
          Content Understanding returns a confidence score with every extracted value. This is how
          to turn that score into a human-review policy you can defend — and what it saves.
        </p>

        <div className="hero__meta">
          <span className="chip">
            <b>{count(meta.documents.train + meta.documents.test)}</b> receipts
          </span>
          <span className="chip">
            <b>{count(meta.totalObservations)}</b> extracted values
          </span>
          <span className="chip">
            <b>{meta.fieldOrder.length}</b> fields
          </span>
          <span className="chip">measured Content Understanding output, not a simulation</span>
        </div>

        <div className="scroll-cue">Scroll to begin ↓</div>
      </div>
    </header>
  );
}
