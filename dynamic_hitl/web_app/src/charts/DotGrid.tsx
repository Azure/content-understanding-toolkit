import { useMemo } from 'react';

export interface DotSegment {
  key: string;
  label: string;
  color: string;
  count: number;
}

const COLUMNS = 62;
const ROWS = 23;
const CELL = 10;
const RADIUS = 3.5;

/**
 * A waffle of every extracted field value in the dataset. Each dot stands for
 * the same number of values, so the coloured areas read as true proportions.
 */
export function DotGrid({ segments }: { segments: DotSegment[] }) {
  const total = segments.reduce((sum, segment) => sum + segment.count, 0);
  const dots = COLUMNS * ROWS;

  const fills = useMemo(() => {
    const result: string[] = new Array(dots);
    let cursor = 0;
    segments.forEach((segment, index) => {
      const last = index === segments.length - 1;
      const end = last ? dots : cursor + Math.round((segment.count / total) * dots);
      for (let i = cursor; i < Math.min(end, dots); i += 1) result[i] = segment.color;
      cursor = end;
    });
    for (let i = 0; i < dots; i += 1) if (!result[i]) result[i] = segments[segments.length - 1].color;
    return result;
  }, [segments, total, dots]);

  const perDot = Math.round(total / dots);

  return (
    <figure style={{ margin: 0 }}>
      <svg
        className="chart"
        viewBox={`0 0 ${COLUMNS * CELL} ${ROWS * CELL}`}
        role="img"
        aria-label={segments.map((s) => `${s.label}: ${s.count}`).join(', ')}
      >
        {fills.map((fill, index) => {
          const column = index % COLUMNS;
          const row = Math.floor(index / COLUMNS);
          return (
            <circle
              key={index}
              cx={column * CELL + CELL / 2}
              cy={row * CELL + CELL / 2}
              r={RADIUS}
              fill={fill}
              style={{
                transition: 'fill 420ms cubic-bezier(0.2, 0.7, 0.2, 1)',
                transitionDelay: `${index * 0.22}ms`,
              }}
            />
          );
        })}
      </svg>
      <figcaption className="metric__note" style={{ marginTop: 10 }}>
        Each dot ≈ {perDot} extracted field values.
      </figcaption>
    </figure>
  );
}
