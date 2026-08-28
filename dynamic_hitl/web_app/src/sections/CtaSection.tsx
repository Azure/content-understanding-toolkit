import { meta } from '../lib/payload';

export function CtaSection() {
  return (
    <section className="section" style={{ borderTop: 0, paddingTop: 16 }}>
      <div className="wrap">
        <div className="cta">
          <h2>Now run it on your own documents.</h2>
          <p>
            The same code that produced every chart on this page ships next door as a notebook. It
            needs one table — your extracted values, their confidence scores, and whether each one
            was right.
          </p>
          <div className="cta__steps">
            <div className="cta__step">
              <b>1 · Install</b>
              <code>pip install -r calibration_lab/requirements.txt</code>
            </div>
            <div className="cta__step">
              <b>2 · Open</b>
              <code>calibration_lab/run_calibration.ipynb</code>
            </div>
            <div className="cta__step">
              <b>3 · Swap in your data</b>
              <code>lab.load_canonical_file("my_data.parquet")</code>
            </div>
          </div>
        </div>

        <div className="footer">
          <span>
            Data: {meta.datasetName} · {meta.sourceDataset} · {meta.license}
          </span>
          <span>
            Analyzer {meta.analyzer} · {meta.completionModel} · API {meta.apiVersion}
          </span>
        </div>
      </div>
    </section>
  );
}
