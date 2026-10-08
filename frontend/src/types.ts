export interface Criterion {
  key: string;
  label: string;
  description: string;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  rubric: Criterion[];
  overlap: number;
  n_items: number;
  n_labels: number;
}

export interface Rater {
  id: number;
  name: string;
}

export interface Assignment {
  item_id: number;
  prompt: string;
  left: string;
  right: string;
  swapped: boolean;
  labeled: number;
  remaining: number;
}

export type Side = "left" | "right" | "tie";

export interface ItemStats {
  item_id: number;
  n_labels: number;
  counts: Record<"A" | "tie" | "B", number>;
  majority: string | null;
  agreement: number | null;
  mean_score: number | null;
  gold: string | null;
}

export interface RaterStats {
  rater: string;
  n_labels: number;
  agreement_with_others: number | null;
  gold_accuracy: number | null;
  n_gold: number;
  left_bias: number | null;
  tie_rate: number | null;
  median_seconds: number | null;
}

export interface ProjectStats {
  n_items: number;
  n_labels: number;
  n_raters: number;
  items_fully_labeled: number;
  percent_agreement: number | null;
  krippendorff_nominal: number | null;
  krippendorff_interval: number | null;
  fleiss_kappa: number | null;
  items: ItemStats[];
  raters: RaterStats[];
  pairwise_kappa: { rater_a: string; rater_b: string; n_shared: number; kappa: number | null }[];
}
