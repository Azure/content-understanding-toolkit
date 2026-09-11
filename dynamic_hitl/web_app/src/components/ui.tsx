import { useId, type ReactNode } from 'react';
import { motion } from 'framer-motion';

export function Section({
  id,
  step,
  title,
  lede,
  tint,
  children,
}: {
  id: string;
  step: string;
  title: string;
  lede?: ReactNode;
  tint?: boolean;
  children: ReactNode;
}) {
  return (
    <section id={id} className={`section${tint ? ' section--tint' : ''}`}>
      <div className="wrap">
        <header className="section__head">
          <div className="section__step">{step}</div>
          <h2 className="section__title">{title}</h2>
          {lede ? <p className="section__lede">{lede}</p> : null}
        </header>
        <div className="stack">{children}</div>
      </div>
    </section>
  );
}

export function Card({
  title,
  sub,
  flush,
  children,
}: {
  title?: string;
  sub?: string;
  flush?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={`card${flush ? ' card--flush' : ''}`}>
      {title ? <div className="card__title">{title}</div> : null}
      {sub ? <div className="card__sub">{sub}</div> : null}
      {children}
    </div>
  );
}

export function Metric({
  label,
  value,
  note,
  color,
  hero,
  small,
}: {
  label: string;
  value: string;
  note?: string;
  color?: string;
  hero?: boolean;
  small?: boolean;
}) {
  return (
    <div className={`metric${hero ? ' metric--hero' : ''}`}>
      <div className="metric__label">{label}</div>
      <div
        className={`metric__value${small ? ' metric__value--sm' : ''}`}
        style={color ? { color } : undefined}
      >
        {color ? <span className="metric__swatch" style={{ background: color }} /> : null}
        {value}
      </div>
      {note ? <div className="metric__note">{note}</div> : null}
    </div>
  );
}

export interface LegendEntry {
  label: string;
  color: string;
  line?: boolean;
}

export function Legend({ items }: { items: LegendEntry[] }) {
  return (
    <div className="legend">
      {items.map((item) => (
        <span className="legend__item" key={item.label}>
          <span
            className={`legend__dot${item.line ? ' legend__dot--line' : ''}`}
            style={{ background: item.color }}
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}

export function Toggle<T extends string>({
  options,
  value,
  onChange,
  layoutId,
  label,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  layoutId: string;
  label: string;
}) {
  return (
    <div className="toggle" role="group" aria-label={label}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            data-active={active}
            onClick={() => onChange(option.value)}
          >
            {active ? (
              <motion.span
                className="toggle__pill"
                layoutId={layoutId}
                transition={{ type: 'spring', stiffness: 420, damping: 34 }}
              />
            ) : null}
            <span className="toggle__text">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export function Pills<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string; color?: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="pills">
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            className="pill"
            data-active={active}
            onClick={() => onChange(option.value)}
            style={active && option.color ? { background: option.color, borderColor: option.color } : undefined}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
  format,
  scale,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  format: (value: number) => string;
  scale?: [string, string];
}) {
  const id = useId();
  const fraction = (value - min) / (max - min);
  return (
    <div className="slider">
      <div className="slider__row">
        <label className="slider__label" htmlFor={id}>
          {label}
        </label>
        <span className="slider__value">{format(value)}</span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        style={{
          background: `linear-gradient(90deg, var(--blank-saved) ${fraction * 100}%, var(--grid) ${
            fraction * 100
          }%)`,
        }}
      />
      {scale ? (
        <div className="slider__scale">
          <span>{scale[0]}</span>
          <span>{scale[1]}</span>
        </div>
      ) : null}
    </div>
  );
}
