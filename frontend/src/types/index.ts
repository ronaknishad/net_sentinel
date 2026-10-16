export interface Page<T> { items: T[]; total: number; page: number; page_size: number }

export interface ModelMeta {
  model_id: string; model_name: string; mode: string; dataset_name: string; is_synthetic: boolean
  trained_at: string; schema_version: string; classes: string[]; feature_names: string[]
}
export interface ModelStatus { loaded: boolean; message: string; metadata: ModelMeta | null }

export interface Analysis {
  id: number; name: string; source: string; dataset_id: number | null; model_id: string; model_name: string
  mode: string; is_synthetic: boolean; total_flows: number; normal_count: number; suspicious_count: number
  high_severity_count: number; rejected_count: number; warnings: string[]; created_at: string
}
export interface Timeline {
  available: boolean; reason?: string; bucket_size?: string
  buckets: { bucket: string; normal: number; suspicious: number }[]
}
export interface AnalysisSummary {
  analysis: Analysis; class_distribution: Record<string, number>
  severity_distribution: Record<string, number>; timeline: Timeline
}
export interface Overview {
  has_analysis: boolean; latest: AnalysisSummary | null; model: ModelMeta | null; model_loaded: boolean
  evaluation_available: boolean; open_alerts: number; analyses_total: number
}

export interface Flow {
  id: number; analysis_id: number; row_index: number; flow_ref: string; timestamp: string | null
  protocol: string | null; destination_port: number | null; packets: number | null; bytes: number | null
  predicted_class: string; is_suspicious: boolean; confidence: number | null; severity: string
  actual_label: string | null
}
export interface FlowDetail extends Flow {
  features: Record<string, number | null>
  model: { model_id: string; model_name: string; mode: string; is_synthetic: boolean }
  alert: { id: number; status: string; severity: string; created_at: string } | null
}

export type AlertStatus = 'new' | 'under_review' | 'resolved'
export interface AlertRow {
  id: number; analysis_id: number; flow_id: number; created_at: string; predicted_class: string
  severity: string; confidence: number | null; status: AlertStatus; flow_ref: string
  destination_port: number | null; protocol: string | null; packets: number | null; bytes: number | null
}
export interface AlertDetail extends AlertRow {
  features: Record<string, number | null>; note: string; model_name: string; model_id: string
  mode: string; is_synthetic: boolean; timestamp: string | null; actual_label: string | null
}
export interface AlertList extends Page<AlertRow> { status_counts: Record<AlertStatus, number>; note: string }

export interface Validation {
  rows: number; columns: number; label_column: string | null; mapped_features: Record<string, string>
  missing_features: string[]; unsupported_columns: { column: string; reason: string }[]
  missing_values: Record<string, number>; infinite_values: Record<string, number>
  non_numeric_values: Record<string, number>; duplicate_rows: number; missing_labels: number
  class_distribution: Record<string, number>; errors: string[]; warnings: string[]; is_valid: boolean
}
export interface Dataset {
  id: number; name: string; size_bytes: number; row_count: number; columns: string[]
  label_column: string | null; column_overrides: Record<string, string>; is_synthetic: boolean
  is_valid: boolean; validation: Validation; created_at: string
}
export interface TrainingRun {
  id: number; dataset_id: number; mode: string; status: 'running' | 'completed' | 'failed'
  started_at: string; finished_at: string | null; model_id: string | null; error: string | null
}

export interface ClassMetric {
  class: string; precision: number; recall: number; f1: number; support: number; false_positive_rate: number | null
}
export interface ModelMetrics {
  accuracy: number; headline: { precision: number; recall: number; f1: number }; averaging: string
  normal_flagged_rate: number | null; training_seconds: number; per_class: ClassMetric[]
  confusion_matrix: { labels: string[]; matrix: number[][] }
}
export interface Evaluation {
  model_id: string; selected_model: string; mode: string; dataset_name: string; is_synthetic: boolean
  provenance_note: string; trained_at: string; random_seed: number; classes: string[]
  split: { test_size: number; train_samples: number; test_samples: number; train_class_distribution: Record<string, number> }
  class_distribution: Record<string, number>; dropped_classes: Record<string, number>
  preprocessing: { rows_before: number; rows_after: number; dropped_duplicates: number; infinite_values_replaced: number }
  models: Record<string, ModelMetrics>
  model_comparison: { model: string; accuracy: number; precision: number; recall: number; f1: number; normal_flagged_rate: number | null; training_seconds: number }[]
  feature_importances: { feature: string; importance: number }[] | null
  probability_note: string
}

export interface SystemInfo {
  app: { name: string; version: string }
  model: { loaded: boolean; message: string; metadata: ModelMeta | null; evaluation_available: boolean }
  datasets: { directory: string; file_count: number; total_bytes: number }
  storage: { database_path: string; database_exists: boolean; database_bytes: number }
  input_schema: { version: string; features: { name: string; description: string; accepted_headers: string[] }[] }
  severity_policy: { severity: string; rule: string }[]
  live_capture: { configured: boolean; message: string }
}
