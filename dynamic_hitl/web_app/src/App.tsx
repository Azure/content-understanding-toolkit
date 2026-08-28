import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Slider } from './components/ui';
import { Hero } from './sections/Hero';
import { CostSection } from './sections/CostSection';
import { ShortcutSection } from './sections/ShortcutSection';
import { MethodSection } from './sections/MethodSection';
import { DialSection } from './sections/DialSection';
import { GeneralizeSection } from './sections/GeneralizeSection';
import { GrowSection } from './sections/GrowSection';
import { CtaSection } from './sections/CtaSection';
import { engines, meta, targetIndex, type EngineName } from './lib/payload';
import { percent } from './lib/format';
import { colors } from './lib/theme';

const DEFAULT_TARGET = 0.8;

export default function App() {
  const [target, setTarget] = useState(DEFAULT_TARGET);
  const [engine, setEngine] = useState<EngineName>('raw_confidence');
  const dialVisible = useDialVisibility();

  const index = targetIndex(target);
  const expected = engines[engine].expected.portfolio[index];
  const measured = engines[engine].measured.portfolio[index];

  return (
    <div className="page">
      <Hero />
      <CostSection />
      <ShortcutSection />
      <MethodSection target={target} />
      <DialSection target={target} engine={engine} />
      <GeneralizeSection target={target} engine={engine} />
      <GrowSection target={target} engine={engine} onEngineChange={setEngine} />
      <CtaSection />

      <AnimatePresence>
        {dialVisible ? (
          <motion.div
            className="dial-bar"
            initial={{ y: 100 }}
            animate={{ y: 0 }}
            exit={{ y: 100 }}
            transition={{ type: 'spring', stiffness: 320, damping: 34 }}
          >
            <div className="wrap dial-bar__inner">
              <Slider
                label="Mistakes human review must catch"
                value={Math.round(target * 100)}
                min={Math.round(meta.targets[0] * 100)}
                max={Math.round(meta.targets[meta.targets.length - 1] * 100)}
                step={1}
                onChange={(value) => setTarget(value / 100)}
                format={(value) => `${value}%`}
                scale={['automate more', 'catch more']}
              />
              <div className="dial-bar__stat">
                <div className="metric__label">Review avoided</div>
                <div className="metric__value">{percent(expected.totalSaved, 1)}</div>
              </div>
              <div className="dial-bar__stat">
                <div className="metric__label">Caught, unseen data</div>
                <div className="metric__value" style={{ color: colors.filledSaved }}>
                  {percent(measured.catch, 1)}
                </div>
              </div>
              <div className="dial-bar__stat">
                <div className="metric__label">Slipped through</div>
                <div className="metric__value" style={{ color: colors.mistake }}>
                  {percent(measured.stpErrorRate, 1)}
                </div>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

/** The dial bar is only useful while the sections it drives are on screen. */
function useDialVisibility(): boolean {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const update = () => {
      const start = document.getElementById('dial');
      const end = document.getElementById('grow');
      if (!start || !end) return;
      const top = start.getBoundingClientRect().top;
      const bottom = end.getBoundingClientRect().bottom;
      setVisible(top < window.innerHeight * 0.65 && bottom > window.innerHeight * 0.5);
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, []);

  return visible;
}
