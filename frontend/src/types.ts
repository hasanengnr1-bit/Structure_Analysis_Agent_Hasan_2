export type ApiEnvelope<T> = {
  status_code?: number;
  status?: string;
  data?: T;
  message?: string;
  task_id?: string;
  access_token?: string;
  token_type?: string;
};

export type ProjectSummary = {
  id: string;
  filename: string;
};

export type TaskStatus = {
  task_id: string;
  status: "PENDING" | "SUCCESS" | "ERROR" | string;
  data?: ExtractionData | string;
  project_id?: string;
  message?: string;
};

export type VisualPoint = {
  x_ft?: number | null;
  y_ft?: number | null;
  label?: string | null;
};

export type VisualFootprint = {
  level?: string;
  overall_length_ft?: number | null;
  overall_width_ft?: number | null;
  polygon?: VisualPoint[] | null;
  source_note?: string;
  uncertain_areas?: string[] | null;
};

export type VisualDimension = {
  label: string;
  value_ft?: number | null;
  direction?: "X" | "Y" | "vertical" | "diagonal" | "unknown";
  source_note?: string;
  uncertain?: boolean;
};

export type VisualRidgeLine = {
  label: string;
  level?: string | null;
  orientation?: "N-S" | "E-W" | "diagonal" | "unknown";
  start?: VisualPoint | null;
  end?: VisualPoint | null;
  height_ft?: number | null;
  source_note?: string;
  uncertain?: boolean;
};

export type VisualRoofPlane = {
  label: string;
  roof_type?: string;
  pitch?: string | null;
  boundary?: VisualPoint[] | null;
  ridge_label?: string | null;
  source_note?: string;
  uncertain_areas?: string[] | null;
};

export type VisualContext = {
  drawing_scale?: string | null;
  north_arrow?: string | null;
  plan_orientation_note?: string | null;
  dimensions?: VisualDimension[];
  levels?: Array<{
    name: string;
    elevation_ft?: number | null;
    story_height_ft?: number | null;
    source_note?: string;
  }>;
  footprints?: VisualFootprint[];
  elevations?: Array<{
    view_name: string;
    eave_height_ft?: number | null;
    ridge_height_ft?: number | null;
    wall_height_ft?: number | null;
    roof_pitch?: string | null;
    source_note?: string;
    uncertain_areas?: string[] | null;
  }>;
  ridge_lines?: VisualRidgeLine[];
  roof_planes?: VisualRoofPlane[];
  visual_summary?: string;
  uncertain_areas?: string[] | null;
};

export type VisualOverlayItem = {
  item_type: string;
  system: string;
  label: string;
  level?: string | null;
  size?: string | null;
  location_description?: string | null;
  span_ft?: number | null;
  spacing_in?: number | null;
  note?: string;
};

export type VisualizationData = {
  context?: VisualContext | null;
  overlays?: VisualOverlayItem[];
  source_systems?: string[];
  visualizer_note?: string;
};

export type ExtractionData = Record<string, unknown> & {
  roof_system?: Record<string, unknown>;
  floor_system?: Record<string, unknown>;
  footing?: Record<string, unknown>;
  post?: Record<string, unknown>;
  wall?: Record<string, unknown>;
  shear_wall?: Record<string, unknown>;
  visualization?: VisualizationData;
};

export type AnalysisCheck = {
  name: string;
  actual?: unknown;
  allowed?: unknown;
  utilization?: number | null;
  combo?: string | null;
  ldf?: string | number | null;
  status: "PASS" | "FAIL" | "ERROR" | string;
};

export type AnalysisItem = {
  id: string;
  source_system: string;
  source_collection: string;
  source_type: string;
  label: string;
  system: string;
  application: string;
  size?: string | null;
  plies?: number | null;
  status: "PASS" | "FAIL" | "ERROR" | string;
  max_utilization?: number | null;
  checks: AnalysisCheck[];
  error?: string | null;
  raw?: unknown;
};

export type AnalysisData = {
  summary: {
    total_items: number;
    passing: number;
    failing: number;
    errors: number;
    overall: "PASS" | "FAIL" | "ERROR" | string;
  };
  systems: Record<
    string,
    {
      total: number;
      passing: number;
      failing: number;
      errors: number;
      items: AnalysisItem[];
    }
  >;
  items: AnalysisItem[];
};
