/** Colours shared between the stylesheet and the hand-drawn SVG charts. */
export const colors = {
  blankSaved: '#0078d4',
  filledSaved: '#107c10',
  reviewed: '#c7cdd4',
  reviewedDeep: '#8a939c',
  mistake: '#d13438',
  accent: '#8661c5',
  amber: '#ca5010',
  ink: '#161616',
  inkMuted: '#5c6670',
  line: '#e3e6ea',
  grid: '#eef1f4',
  surface: '#f6f8fa',
} as const;

/** Distinct hues for the eight receipt fields. */
export const fieldColors: Record<string, string> = {
  'menu.name': '#0078d4',
  'menu.price': '#107c10',
  'menu.quantity': '#8661c5',
  subtotal_price: '#ca5010',
  tax_price: '#d13438',
  service_price: '#008272',
  other_adjustment: '#886ce4',
  total_price: '#005a9e',
};

export function fieldColor(field: string): string {
  return fieldColors[field] ?? colors.inkMuted;
}
