import raw from '../data/payload.json';

export type EngineName = 'raw_confidence' | 'logistic';
export type SplitName = 'train' | 'test';

export interface Meta {
  datasetName: string;
  sourceDataset: string;
  license: string;
  analyzer: string;
  completionModel: string;
  apiVersion: string;
  documents: Record<SplitName, number>;
  observations: Record<SplitName, number>;
  totalObservations: number;
  trainMistakes: number;
  testMistakes: number;
  blankShare: number;
  targets: number[];
  minAucCiLower: number;
  fieldOrder: string[];
}

export interface FieldProfile {
  field: string;
  label: string;
  nTotal: number;
  nBlank: number;
  nFilled: number;
  blankShare: number;
  accuracy: number;
  nMistakes: number;
  meanConfidence: number;
  auc: number | null;
  aucLow: number | null;
  aucHigh: number | null;
  confidenceIsUsable: boolean;
  blankPrecision: number | null;
  blankLow: number | null;
  blankHigh: number | null;
}

export interface ConfidenceDistribution {
  binEdges: number[];
  fields: { field: string; label: string; correct: number[]; incorrect: number[] }[];
}

export interface VolumePoint {
  auc: number | null;
  aucLow: number | null;
  aucHigh: number | null;
  usable: boolean;
  nFilled: number;
  blankPrecision: number | null;
  blankLow: number | null;
  blankHigh: number | null;
  nBlank: number;
}

export interface SignalVsVolume {
  documentCounts: number[];
  repeats: number;
  perField: Record<string, VolumePoint[]>;
}

export interface CutoffPoint {
  stpRate: number;
  errorRate: number | null;
  nAuto: number;
}

export interface GlobalCutoff {
  cutoffs: number[];
  perField: Record<string, CutoffPoint[]>;
  overall: { stpRate: number; errorRate: number | null; catch: number }[];
}

export interface FrontierPoint {
  threshold: number;
  stpRate: number;
  catch: number;
}

export interface ExpectedPortfolioPoint {
  target: number;
  blankSaved: number;
  filledSaved: number;
  reviewed: number;
  totalSaved: number;
  blankSavedCount: number;
  filledSavedCount: number;
  reviewedCount: number;
  calibratedFields: number;
  reviewedFields: number;
}

export interface ExpectedFieldPoint {
  blankSaved: number;
  filledSaved: number;
  reviewed: number;
  nTotal: number;
  automated: boolean;
}

export interface MeasuredPortfolioPoint {
  target: number;
  autoApproveRate: number;
  reviewRate: number;
  catch: number;
  calibratedCatch: number | null;
  stpErrorRate: number | null;
  mistakesSlipped: number;
  mistakesCaught: number;
  totalMistakes: number;
}

export interface MeasuredFieldPoint {
  autoApproveRate: number;
  catch: number | null;
  stpErrorRate: number | null;
}

export interface PolicyCutoff {
  cutoff: number | null;
  blankAutoApproved: boolean;
}

export interface Engine {
  expected: {
    portfolio: ExpectedPortfolioPoint[];
    perField: Record<string, ExpectedFieldPoint[]>;
  };
  measured: {
    portfolio: MeasuredPortfolioPoint[];
    perField: Record<string, MeasuredFieldPoint[]>;
  };
  cutoffs: Record<string, PolicyCutoff[]>;
}

export interface Payload {
  meta: Meta;
  fields: FieldProfile[];
  confidenceDistribution: ConfidenceDistribution;
  signalVsVolume: SignalVsVolume;
  globalCutoff: GlobalCutoff;
  naiveFrontier: FrontierPoint[];
  engines: Record<EngineName, Engine>;
}

export const payload = raw as Payload;

export const { meta, fields, engines } = payload;

/** Field keys in the order they should always be drawn. */
export const fieldKeys: string[] = fields.map((field) => field.field);

/** Index into every per-target array for a given coverage target. */
export function targetIndex(target: number): number {
  const index = meta.targets.findIndex((value) => Math.abs(value - target) < 1e-9);
  return index === -1 ? 0 : index;
}
