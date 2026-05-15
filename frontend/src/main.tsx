import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import type { Root } from "react-dom/client";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BadgeCheck,
  Box,
  Building2,
  Check,
  ChevronRight,
  CircleDashed,
  Columns3,
  Download,
  Eye,
  FileText,
  FolderOpen,
  Gauge,
  Grid3X3,
  Layers3,
  Loader2,
  LogOut,
  Map,
  PanelLeft,
  RefreshCw,
  Ruler,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  UploadCloud,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  ApiError,
  checkStatus,
  deleteProject,
  getProject,
  getProjects,
  getStoredApiBase,
  getStoredToken,
  getAnalysis,
  getVisualization,
  health,
  login,
  setStoredApiBase,
  setStoredToken,
  signup,
  startExtraction,
  trimTrailingSlash,
} from "./api";
import type { AnalysisData, AnalysisItem, ExtractionData, ProjectSummary, VisualizationData, VisualOverlayItem } from "./types";
import "./styles.css";

type AuthMode = "login" | "signup";
type LoadState = "idle" | "loading" | "success" | "error";
type ViewTab = "visualizer" | "analysis" | "systems" | "raw";

const SYSTEMS = [
  { key: "roof_system", label: "Roof", icon: Layers3 },
  { key: "floor_system", label: "Floor", icon: Grid3X3 },
  { key: "wall", label: "Walls", icon: Columns3 },
  { key: "shear_wall", label: "Lateral", icon: ShieldCheck },
  { key: "post", label: "Posts", icon: Box },
  { key: "footing", label: "Foundation", icon: Building2 },
] as const;

const demoExtraction: ExtractionData = {
  roof_system: {
    ridge_beams: [{ zone: "Main Ridge", size: "(3) 2x12", clear_span_ft: 28 }],
    roof_rafters: [{ zone: "North Roof Slope", size: "2x8", clear_span_ft: 14, spacing_in: 16 }],
    ceiling_joists: [],
    hip_valley_rafters: [{ zone: "West Valley", size: "2x10", clear_span_ft: 16 }],
    roof_drop_beams: [],
    roof_flush_beams: [],
  },
  floor_system: {
    floor_joists: [{ zone: "Main Floor Joists", size: "2x10", clear_span_ft: 13.5, spacing_in: 16 }],
    floor_drop_beams: [{ zone: "Center Drop Beam", size: "(3) 2x12", clear_span_ft: 20 }],
    floor_flush_beams: [],
  },
  wall: {
    stud_walls: [
      { zone: "North Exterior Wall", stud_size: "2x6", wall_length_ft: 46, spacing_in: 16 },
      { zone: "South Exterior Wall", stud_size: "2x6", wall_length_ft: 46, spacing_in: 16 },
    ],
    headers: [{ zone: "Great Room Opening", opening_mark: "H1", header_size: "(2) 2x12", header_clear_span_ft: 8 }],
    top_plates: [],
    bottom_plates: [],
  },
  shear_wall: {
    braced_wall_lines: [{ bwl_id: "BWL-A", story_level: "Main", bwl_total_length_ft: 46 }],
    shear_walls: [{ sw_mark: "SW1", bwl_id: "BWL-A", story_level: "Main", stud_size: "2x6", pier_length_ft: 8 }],
    diaphragms: [],
  },
  footing: {
    continuous_strip_footings: [{ footing_mark: "F1", location_description: "Perimeter", length_ft: 46 }],
    pad_footings: [{ footing_mark: "P1", location_description: "Center post", width_in: 24, length_in: 24 }],
    grade_beams: [],
    slab_on_grade: [],
    holdown_anchors: [],
  },
  post: {
    standalone_posts: [{ post_mark: "P1", post_size: "6x6", location_description: "Center beam support", height_ft: 9 }],
  },
};

const demoVisualization: VisualizationData = {
  context: {
    drawing_scale: "1/4 in = 1 ft",
    north_arrow: "Up",
    plan_orientation_note: "North is up on the sheet.",
    dimensions: [
      { label: "Overall length", value_ft: 46, direction: "X" },
      { label: "Overall width", value_ft: 30, direction: "Y" },
      { label: "Ridge height", value_ft: 23, direction: "vertical" },
    ],
    levels: [
      { name: "Main", elevation_ft: 0, story_height_ft: 10 },
      { name: "Roof", elevation_ft: 10, story_height_ft: 13 },
    ],
    footprints: [
      {
        level: "Main",
        overall_length_ft: 46,
        overall_width_ft: 30,
        polygon: [
          { x_ft: 0, y_ft: 0 },
          { x_ft: 46, y_ft: 0 },
          { x_ft: 46, y_ft: 30 },
          { x_ft: 0, y_ft: 30 },
        ],
      },
    ],
    elevations: [{ view_name: "Front", eave_height_ft: 10, ridge_height_ft: 23, wall_height_ft: 10, roof_pitch: "6/12" }],
    ridge_lines: [{ label: "Main ridge", orientation: "E-W", start: { x_ft: 4, y_ft: 15 }, end: { x_ft: 42, y_ft: 15 }, height_ft: 23 }],
    roof_planes: [
      { label: "North roof plane", roof_type: "gable", pitch: "6/12", ridge_label: "Main ridge" },
      { label: "South roof plane", roof_type: "gable", pitch: "6/12", ridge_label: "Main ridge" },
    ],
    visual_summary: "Demo extraction preview",
  },
  overlays: [
    { item_type: "ridge_beam", system: "roof", label: "Main Ridge", size: "(3) 2x12", span_ft: 28 },
    { item_type: "floor_joist_run", system: "floor", label: "Main Floor Joists", size: "2x10", span_ft: 13.5, spacing_in: 16 },
    { item_type: "stud_wall", system: "wall", label: "North Exterior Wall", size: "2x6", span_ft: 46, spacing_in: 16 },
    { item_type: "shear_wall", system: "lateral", label: "SW1", size: "2x6", span_ft: 8 },
    { item_type: "post", system: "post", label: "P1", size: "6x6", span_ft: 9 },
    { item_type: "continuous_footing", system: "foundation", label: "F1", span_ft: 46 },
  ],
  source_systems: ["roof_system", "floor_system", "wall", "shear_wall", "post", "footing"],
};

const demoAnalysis: AnalysisData = {
  summary: {
    total_items: 9,
    passing: 8,
    failing: 1,
    errors: 0,
    overall: "FAIL",
  },
  systems: {},
  items: [
    {
      id: "ridge-beam-demo",
      source_system: "roof_system",
      source_collection: "ridge_beams",
      source_type: "ridge_beam",
      label: "Main Ridge",
      system: "Roof",
      application: "Beam",
      size: "(3) 2x12",
      status: "PASS",
      max_utilization: 72,
      checks: [
        { name: "Moment", actual: 5100, allowed: 7100, utilization: 72, status: "PASS", combo: "D+Lr" },
        { name: "Shear", actual: 840, allowed: 1900, utilization: 44, status: "PASS", combo: "D+Lr" },
      ],
    },
    {
      id: "floor-joist-demo",
      source_system: "floor_system",
      source_collection: "floor_joists",
      source_type: "floor_joist",
      label: "Main Floor Joists",
      system: "Floor",
      application: "Joist",
      size: "2x10",
      status: "PASS",
      max_utilization: 81,
      checks: [{ name: "Live Load Deflection", actual: 0.31, allowed: 0.38, utilization: 81, status: "PASS", combo: "Live Loads" }],
    },
    {
      id: "header-demo",
      source_system: "wall",
      source_collection: "headers",
      source_type: "header",
      label: "Great Room Opening",
      system: "Wall",
      application: "Header",
      size: "(2) 2x12",
      status: "FAIL",
      max_utilization: 118,
      checks: [{ name: "Moment", actual: 4200, allowed: 3550, utilization: 118, status: "FAIL", combo: "D+L" }],
    },
  ],
};

function App() {
  const [apiBase, setApiBase] = useState(getStoredApiBase());
  const [token, setToken] = useState(getStoredToken());
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authState, setAuthState] = useState<LoadState>("idle");
  const [status, setStatus] = useState("Ready");
  const [backendState, setBackendState] = useState<"online" | "offline" | "checking">("checking");
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectsState, setProjectsState] = useState<LoadState>("idle");
  const [activeProject, setActiveProject] = useState<ProjectSummary | null>(null);
  const [extraction, setExtraction] = useState<ExtractionData | null>(null);
  const [visualization, setVisualization] = useState<VisualizationData | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [analysisState, setAnalysisState] = useState<LoadState>("idle");
  const [selectedTab, setSelectedTab] = useState<ViewTab>("visualizer");
  const [selectedSystem, setSelectedSystem] = useState<string>("roof_system");
  const [uploadState, setUploadState] = useState<LoadState>("idle");
  const [taskMessage, setTaskMessage] = useState("");
  const [search, setSearch] = useState("");

  const isAuthenticated = Boolean(token);

  const normalizedApiBase = useMemo(() => trimTrailingSlash(apiBase), [apiBase]);

  useEffect(() => {
    let cancelled = false;
    setBackendState("checking");
    health(normalizedApiBase)
      .then(() => {
        if (!cancelled) setBackendState("online");
      })
      .catch(() => {
        if (!cancelled) setBackendState("offline");
      });
    return () => {
      cancelled = true;
    };
  }, [normalizedApiBase]);

  const loadProjects = useCallback(async () => {
    if (!token) return;
    setProjectsState("loading");
    try {
      const data = await getProjects(normalizedApiBase, token);
      setProjects(data);
      setProjectsState("success");
    } catch (error) {
      setProjectsState("error");
      setStatus(getErrorMessage(error));
    }
  }, [normalizedApiBase, token]);

  useEffect(() => {
    if (token) {
      void loadProjects();
    }
  }, [loadProjects, token]);

  const counts = useMemo(() => getExtractionCounts(extraction), [extraction]);
  const filteredProjects = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter((project) => `${project.filename} ${project.id}`.toLowerCase().includes(q));
  }, [projects, search]);

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") || "");
    const password = String(form.get("password") || "");
    const name = String(form.get("name") || "");

    setAuthState("loading");
    setStatus(authMode === "signup" ? "Creating account" : "Signing in");

    try {
      if (authMode === "signup") {
        await signup(normalizedApiBase, { name, email, password });
      }
      const nextToken = await login(normalizedApiBase, { email, password });
      setStoredToken(nextToken);
      setToken(nextToken);
      setStoredApiBase(normalizedApiBase);
      setApiBase(normalizedApiBase);
      setAuthState("success");
      setStatus("Signed in");
    } catch (error) {
      setAuthState("error");
      setStatus(getErrorMessage(error));
    }
  }

  async function openProject(project: ProjectSummary) {
    setActiveProject(project);
    setStatus(`Opening ${project.filename}`);
    try {
      setAnalysisState("loading");
      const [projectData, visualData, analysisData] = await Promise.all([
        getProject(normalizedApiBase, token, project.id),
        getVisualization(normalizedApiBase, token, project.id),
        getAnalysis(normalizedApiBase, token, project.id),
      ]);
      setExtraction(projectData);
      setVisualization(visualData || projectData.visualization || null);
      setAnalysis(analysisData);
      setAnalysisState("success");
      setSelectedTab("visualizer");
      setStatus("Project loaded");
      scrollToWorkspaceTop();
    } catch (error) {
      setAnalysisState("error");
      setStatus(getErrorMessage(error));
    }
  }

  async function handleDeleteProject(project: ProjectSummary) {
    setStatus(`Deleting ${project.filename}`);
    try {
      await deleteProject(normalizedApiBase, token, project.id);
      if (activeProject?.id === project.id) {
        setActiveProject(null);
        setExtraction(null);
        setVisualization(null);
        setAnalysis(null);
      }
      await loadProjects();
      setStatus("Project deleted");
    } catch (error) {
      setStatus(getErrorMessage(error));
    }
  }

  async function handleUpload(file: File) {
    setUploadState("loading");
    setTaskMessage("Starting extraction");
    setStatus(`Uploading ${file.name}`);
    try {
      const started = await startExtraction(normalizedApiBase, token, file);
      if (!started.task_id) {
        throw new ApiError("Extraction started without a task id", 500);
      }
      setTaskMessage(`Task ${started.task_id} running`);
      const result = await pollTask(started.task_id, normalizedApiBase, setTaskMessage);
      if (result.status === "SUCCESS" && result.data && typeof result.data !== "string") {
        const nextData = result.data;
        setExtraction(nextData);
        setVisualization(nextData.visualization || null);
        if (started.project_id || result.project_id) {
          const projectId = started.project_id || result.project_id || "";
          setActiveProject({ id: projectId, filename: file.name });
          setAnalysisState("loading");
          try {
            const analysisData = await getAnalysis(normalizedApiBase, token, projectId);
            setAnalysis(analysisData);
            setAnalysisState("success");
          } catch (analysisError) {
            setAnalysis(null);
            setAnalysisState("error");
            setStatus(`Extraction complete; analysis failed: ${getErrorMessage(analysisError)}`);
          }
        } else {
          setAnalysis(null);
          setAnalysisState("idle");
        }
        setSelectedTab("visualizer");
        setUploadState("success");
        setStatus("Extraction complete");
        scrollToWorkspaceTop();
        await loadProjects();
      } else {
        setUploadState("error");
        setStatus(typeof result.data === "string" ? result.data : "Extraction failed");
      }
    } catch (error) {
      setUploadState("error");
      setStatus(getErrorMessage(error));
    }
  }

  function signOut() {
    setStoredToken("");
    setToken("");
    setProjects([]);
    setExtraction(null);
    setVisualization(null);
    setAnalysis(null);
    setActiveProject(null);
    setStatus("Signed out");
  }

  function loadDemo() {
    setExtraction(demoExtraction);
    setVisualization(demoVisualization);
    setAnalysis(demoAnalysis);
    setAnalysisState("success");
    setActiveProject({ id: "demo", filename: "Demo extraction" });
    setSelectedTab("visualizer");
    setStatus("Demo loaded");
    scrollToWorkspaceTop();
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Workspace">
        <Brand />
        <div className="connection-panel">
          <label htmlFor="api-base">API base</label>
          <div className="api-row">
            <input
              id="api-base"
              value={apiBase}
              onChange={(event) => setApiBase(event.target.value)}
              onBlur={() => {
                const next = trimTrailingSlash(apiBase);
                setApiBase(next);
                setStoredApiBase(next);
              }}
            />
            <StatusDot state={backendState} />
          </div>
        </div>

        {isAuthenticated ? (
          <ProjectRail
            projects={filteredProjects}
            activeProject={activeProject}
            state={projectsState}
            search={search}
            onSearch={setSearch}
            onRefresh={loadProjects}
            onOpen={openProject}
            onDelete={handleDeleteProject}
          />
        ) : (
          <AuthPanel mode={authMode} state={authState} onMode={setAuthMode} onSubmit={handleAuth} />
        )}

        <div className="sidebar-footer">
          {isAuthenticated ? (
            <button className="ghost-button" onClick={signOut}>
              <LogOut size={16} />
              Sign out
            </button>
          ) : (
            <button className="ghost-button" onClick={loadDemo}>
              <Eye size={16} />
              Demo
            </button>
          )}
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Extraction review</p>
            <h1>{activeProject?.filename || "Structure Analysis Agent"}</h1>
          </div>
          <div className="status-pill" data-state={uploadState}>
            {uploadState === "loading" ? <Loader2 className="spin" size={16} /> : <Activity size={16} />}
            <span>{taskMessage || status}</span>
          </div>
        </header>

        <section className="command-strip">
          <UploadPanel disabled={!isAuthenticated} state={uploadState} onUpload={handleUpload} />
          <Metric label="Roof" value={counts.roof_system} icon={Layers3} />
          <Metric label="Wall" value={counts.wall} icon={Columns3} />
          <Metric label="Checks" value={analysis?.summary.total_items || 0} icon={BadgeCheck} />
          <Metric label="Issues" value={(analysis?.summary.failing || 0) + (analysis?.summary.errors || 0)} icon={AlertCircle} />
        </section>

        <nav className="view-tabs" aria-label="Project views">
          <button className={selectedTab === "visualizer" ? "active" : ""} onClick={() => setSelectedTab("visualizer")}>
            <Map size={16} />
            Visualizer
          </button>
          <button className={selectedTab === "analysis" ? "active" : ""} onClick={() => setSelectedTab("analysis")}>
            <BadgeCheck size={16} />
            Analysis
          </button>
          <button className={selectedTab === "systems" ? "active" : ""} onClick={() => setSelectedTab("systems")}>
            <FolderOpen size={16} />
            Systems
          </button>
          <button className={selectedTab === "raw" ? "active" : ""} onClick={() => setSelectedTab("raw")}>
            <FileText size={16} />
            JSON
          </button>
        </nav>

        {selectedTab === "visualizer" && (
          <VisualizerPanel visualization={visualization} extraction={extraction} onLoadDemo={loadDemo} />
        )}

        {selectedTab === "analysis" && (
          <AnalysisPanel analysis={analysis} state={analysisState} activeProject={activeProject} />
        )}

        {selectedTab === "systems" && (
          <SystemsPanel
            extraction={extraction}
            selectedSystem={selectedSystem}
            onSelectedSystem={setSelectedSystem}
          />
        )}

        {selectedTab === "raw" && <RawPanel extraction={extraction} visualization={visualization} analysis={analysis} />}
      </section>
    </main>
  );
}

function Brand() {
  return (
    <div className="brand">
      <div className="brand-mark">
        <Building2 size={21} />
      </div>
      <div>
        <strong>Strata</strong>
        <span>Structure AI</span>
      </div>
    </div>
  );
}

function StatusDot({ state }: { state: "online" | "offline" | "checking" }) {
  return (
    <span className="status-dot" data-state={state} title={`Backend ${state}`}>
      {state === "online" ? <Check size={14} /> : state === "offline" ? <AlertCircle size={14} /> : <CircleDashed size={14} />}
    </span>
  );
}

function AuthPanel({
  mode,
  state,
  onMode,
  onSubmit,
}: {
  mode: AuthMode;
  state: LoadState;
  onMode: (mode: AuthMode) => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <section className="auth-panel">
      <div className="segmented">
        <button className={mode === "login" ? "active" : ""} onClick={() => onMode("login")}>
          Login
        </button>
        <button className={mode === "signup" ? "active" : ""} onClick={() => onMode("signup")}>
          Signup
        </button>
      </div>
      <form onSubmit={onSubmit}>
        {mode === "signup" && (
          <label>
            Name
            <input name="name" autoComplete="name" required />
          </label>
        )}
        <label>
          Email
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input name="password" type="password" autoComplete={mode === "signup" ? "new-password" : "current-password"} required />
        </label>
        <button className="primary-button" disabled={state === "loading"}>
          {state === "loading" ? <Loader2 className="spin" size={16} /> : <ArrowRight size={16} />}
          Continue
        </button>
      </form>
    </section>
  );
}

function ProjectRail({
  projects,
  activeProject,
  state,
  search,
  onSearch,
  onRefresh,
  onOpen,
  onDelete,
}: {
  projects: ProjectSummary[];
  activeProject: ProjectSummary | null;
  state: LoadState;
  search: string;
  onSearch: (value: string) => void;
  onRefresh: () => void;
  onOpen: (project: ProjectSummary) => void;
  onDelete: (project: ProjectSummary) => void;
}) {
  return (
    <section className="project-rail">
      <div className="rail-heading">
        <span>Projects</span>
        <button className="icon-button" onClick={onRefresh} aria-label="Refresh projects">
          <RefreshCw size={15} className={state === "loading" ? "spin" : ""} />
        </button>
      </div>
      <label className="searchbox">
        <Search size={15} />
        <input value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search" />
      </label>
      <div className="project-list">
        {projects.length === 0 && <div className="empty-rail">No projects</div>}
        {projects.map((project) => (
          <article className={`project-card ${activeProject?.id === project.id ? "active" : ""}`} key={project.id}>
            <button onClick={() => onOpen(project)}>
              <FileText size={16} />
              <span>
                <strong>{project.filename}</strong>
                <small>#{project.id}</small>
              </span>
              <ChevronRight size={15} />
            </button>
            <button className="icon-button danger" onClick={() => onDelete(project)} aria-label={`Delete ${project.filename}`}>
              <Trash2 size={14} />
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function UploadPanel({ disabled, state, onUpload }: { disabled: boolean; state: LoadState; onUpload: (file: File) => void }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  function selectFile(file?: File) {
    if (!file || disabled) return;
    onUpload(file);
  }

  return (
    <section
      className={`upload-tool ${dragging ? "dragging" : ""} ${disabled ? "disabled" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        selectFile(event.dataTransfer.files[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => selectFile(event.target.files?.[0])}
      />
      <button className="upload-action" disabled={disabled || state === "loading"} onClick={() => inputRef.current?.click()}>
        {state === "loading" ? <Loader2 className="spin" size={22} /> : <UploadCloud size={22} />}
        <span>
          <strong>Plan PDF</strong>
          <small>{disabled ? "Login required" : "Upload"}</small>
        </span>
      </button>
    </section>
  );
}

function Metric({ label, value, icon: Icon }: { label: string; value: number; icon: LucideIcon }) {
  return (
    <div className="metric">
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function VisualizerPanel({
  visualization,
  extraction,
  onLoadDemo,
}: {
  visualization: VisualizationData | null;
  extraction: ExtractionData | null;
  onLoadDemo: () => void;
}) {
  const effectiveVisualization = visualization || extraction?.visualization || null;
  const overlays = effectiveVisualization?.overlays || [];
  const context = effectiveVisualization?.context || null;
  const dims = context?.dimensions || [];
  const footprint = context?.footprints?.[0];
  const elevations = context?.elevations || [];
  const hasData = Boolean(effectiveVisualization || extraction);

  if (!hasData) {
    return (
      <section className="empty-state">
        <div className="empty-orbit">
          <Sparkles size={24} />
        </div>
        <h2>No project loaded</h2>
        <p>Select a project, upload a plan, or open the demo workspace.</p>
        <button className="primary-button" onClick={onLoadDemo}>
          <Eye size={16} />
          Open demo
        </button>
      </section>
    );
  }

  return (
    <section className="visualizer-grid">
      <div className="visualizer-tool">
        <VisualizerSvg visualization={effectiveVisualization} />
      </div>
      <aside className="inspector">
        <div className="inspector-section">
          <p className="eyebrow">Geometry</p>
          <h2>{footprint?.level || "Plan"} envelope</h2>
          <dl className="detail-list">
            <div>
              <dt>Length</dt>
              <dd>{formatNumber(footprint?.overall_length_ft)} ft</dd>
            </div>
            <div>
              <dt>Width</dt>
              <dd>{formatNumber(footprint?.overall_width_ft)} ft</dd>
            </div>
            <div>
              <dt>Scale</dt>
              <dd>{context?.drawing_scale || "Not captured"}</dd>
            </div>
            <div>
              <dt>North</dt>
              <dd>{context?.north_arrow || "Not captured"}</dd>
            </div>
          </dl>
        </div>

        <div className="inspector-section">
          <p className="eyebrow">Dimensions</p>
          <div className="dimension-stack">
            {dims.slice(0, 6).map((dimension) => (
              <span key={`${dimension.label}-${dimension.direction}`}>
                <Ruler size={14} />
                {dimension.label}
                <strong>{formatNumber(dimension.value_ft)} ft</strong>
              </span>
            ))}
            {dims.length === 0 && <span className="muted-row">No dimensions captured</span>}
          </div>
        </div>

        <div className="inspector-section">
          <p className="eyebrow">Elevation</p>
          <div className="dimension-stack">
            {elevations.slice(0, 4).map((elevation) => (
              <span key={elevation.view_name}>
                <Gauge size={14} />
                {elevation.view_name}
                <strong>{formatNumber(elevation.ridge_height_ft || elevation.eave_height_ft)} ft</strong>
              </span>
            ))}
            {elevations.length === 0 && <span className="muted-row">No elevations captured</span>}
          </div>
        </div>

        <div className="inspector-section">
          <p className="eyebrow">Overlays</p>
          <OverlayList overlays={overlays} />
        </div>
      </aside>
    </section>
  );
}

function VisualizerSvg({ visualization }: { visualization: VisualizationData | null }) {
  const context = visualization?.context || null;
  const overlays = visualization?.overlays || [];
  const footprint = context?.footprints?.[0];
  const length = footprint?.overall_length_ft || pickDimension(context, "X") || 46;
  const width = footprint?.overall_width_ft || pickDimension(context, "Y") || 30;
  const planBox = { x: 54, y: 78, w: 650, h: 450 };
  const scale = Math.min(planBox.w / length, planBox.h / width);
  const drawW = length * scale;
  const drawH = width * scale;
  const offsetX = planBox.x + (planBox.w - drawW) / 2;
  const offsetY = planBox.y + (planBox.h - drawH) / 2;
  const polygon = footprint?.polygon?.length
    ? footprint.polygon
        .map((point) => `${offsetX + (point.x_ft || 0) * scale},${offsetY + drawH - (point.y_ft || 0) * scale}`)
        .join(" ")
    : `${offsetX},${offsetY} ${offsetX + drawW},${offsetY} ${offsetX + drawW},${offsetY + drawH} ${offsetX},${offsetY + drawH}`;
  const roofRidges = context?.ridge_lines || [];
  const elevation = context?.elevations?.[0];
  const eave = elevation?.eave_height_ft || 10;
  const ridge = elevation?.ridge_height_ft || Math.max(16, eave + width / 4);
  const elevationScale = Math.min(145 / Math.max(ridge, 1), 220 / Math.max(width, 1));
  const elevationBase = { x: 800, y: 260 };
  const elevationW = Math.min(230, width * elevationScale * 1.55);
  const eaveY = elevationBase.y - eave * elevationScale;
  const ridgeY = elevationBase.y - ridge * elevationScale;

  return (
    <svg className="visualizer-svg" viewBox="0 0 1120 620" role="img" aria-label="Extraction visualizer">
      <defs>
        <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
          <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#d9ddd3" strokeWidth="1" />
        </pattern>
        <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="16" stdDeviation="22" floodColor="#1d2421" floodOpacity="0.12" />
        </filter>
      </defs>

      <rect x="0" y="0" width="1120" height="620" rx="8" fill="#f7f8f5" />
      <rect x="38" y="48" width="700" height="520" rx="8" fill="#ffffff" stroke="#dfe4db" filter="url(#softShadow)" />
      <rect x="58" y="86" width="660" height="430" rx="6" fill="url(#grid)" stroke="#e4e8df" />
      <text x="58" y="65" className="svg-title">Plan extraction</text>
      <text x="648" y="65" className="svg-muted">{formatNumber(length)} x {formatNumber(width)} ft</text>

      <polygon points={polygon} fill="#eef3ec" stroke="#29322d" strokeWidth="3" />
      <polygon points={polygon} fill="none" stroke="#ffffff" strokeWidth="1" opacity="0.8" />

      <line x1={offsetX} y1={offsetY + drawH + 24} x2={offsetX + drawW} y2={offsetY + drawH + 24} stroke="#768174" strokeWidth="1.5" />
      <text x={offsetX + drawW / 2} y={offsetY + drawH + 47} textAnchor="middle" className="svg-label">{formatNumber(length)} ft</text>
      <line x1={offsetX - 24} y1={offsetY} x2={offsetX - 24} y2={offsetY + drawH} stroke="#768174" strokeWidth="1.5" />
      <text x={offsetX - 38} y={offsetY + drawH / 2} textAnchor="middle" transform={`rotate(-90 ${offsetX - 38} ${offsetY + drawH / 2})`} className="svg-label">
        {formatNumber(width)} ft
      </text>

      {roofRidges.map((ridgeLine, index) => {
        const start = ridgeLine.start || { x_ft: length * 0.12, y_ft: width / 2 };
        const end = ridgeLine.end || { x_ft: length * 0.88, y_ft: width / 2 };
        return (
          <g key={`${ridgeLine.label}-${index}`}>
            <line
              x1={offsetX + (start.x_ft || 0) * scale}
              y1={offsetY + drawH - (start.y_ft || 0) * scale}
              x2={offsetX + (end.x_ft || 0) * scale}
              y2={offsetY + drawH - (end.y_ft || 0) * scale}
              stroke="#b95f28"
              strokeWidth="4"
              strokeLinecap="round"
            />
            <text
              x={offsetX + ((start.x_ft || 0) + (end.x_ft || 0)) * scale / 2}
              y={offsetY + drawH - ((start.y_ft || 0) + (end.y_ft || 0)) * scale / 2 - 10}
              textAnchor="middle"
              className="svg-label"
            >
              {ridgeLine.label}
            </text>
          </g>
        );
      })}

      {overlays.slice(0, 18).map((overlay, index) => (
        <OverlayMark
          key={`${overlay.item_type}-${overlay.label}-${index}`}
          overlay={overlay}
          index={index}
          origin={{ x: offsetX, y: offsetY }}
          size={{ w: drawW, h: drawH }}
        />
      ))}

      <rect x="772" y="48" width="300" height="250" rx="8" fill="#ffffff" stroke="#dfe4db" filter="url(#softShadow)" />
      <text x="792" y="76" className="svg-title">Elevation</text>
      <line x1={elevationBase.x} y1={elevationBase.y} x2={elevationBase.x + elevationW} y2={elevationBase.y} stroke="#29322d" strokeWidth="3" />
      <line x1={elevationBase.x} y1={elevationBase.y} x2={elevationBase.x} y2={eaveY} stroke="#29322d" strokeWidth="3" />
      <line x1={elevationBase.x + elevationW} y1={elevationBase.y} x2={elevationBase.x + elevationW} y2={eaveY} stroke="#29322d" strokeWidth="3" />
      <polyline
        points={`${elevationBase.x},${eaveY} ${elevationBase.x + elevationW / 2},${ridgeY} ${elevationBase.x + elevationW},${eaveY}`}
        fill="none"
        stroke="#b95f28"
        strokeWidth="4"
        strokeLinejoin="round"
      />
      <text x={elevationBase.x + elevationW - 4} y={eaveY + 4} textAnchor="end" className="svg-muted">eave {formatNumber(eave)} ft</text>
      <text x={elevationBase.x + elevationW / 2} y={ridgeY - 12} textAnchor="middle" className="svg-label">ridge {formatNumber(ridge)} ft</text>
      <text x={elevationBase.x + elevationW / 2} y={elevationBase.y + 28} textAnchor="middle" className="svg-muted">
        {elevation?.roof_pitch || context?.roof_planes?.[0]?.pitch || "pitch n/a"}
      </text>

      <rect x="772" y="326" width="300" height="242" rx="8" fill="#ffffff" stroke="#dfe4db" filter="url(#softShadow)" />
      <text x="792" y="355" className="svg-title">Legend</text>
      {[
        ["roof", "#b95f28"],
        ["floor", "#287e9c"],
        ["wall", "#29322d"],
        ["lateral", "#b33b4a"],
        ["foundation", "#6f7770"],
        ["post", "#4e7a45"],
      ].map(([name, color], index) => (
        <g key={name} transform={`translate(792 ${385 + index * 27})`}>
          <rect x="0" y="-11" width="18" height="18" rx="4" fill={color} />
          <text x="28" y="3" className="svg-label">{name}</text>
        </g>
      ))}
    </svg>
  );
}

function OverlayMark({
  overlay,
  index,
  origin,
  size,
}: {
  overlay: VisualOverlayItem;
  index: number;
  origin: { x: number; y: number };
  size: { w: number; h: number };
}) {
  const color = colorForSystem(overlay.system);
  const row = index % 6;
  const col = Math.floor(index / 6);
  const x = origin.x + size.w * (0.16 + col * 0.2);
  const y = origin.y + size.h * (0.18 + row * 0.12);
  const isPoint = overlay.system === "post" || overlay.item_type.includes("footing") || overlay.item_type.includes("post");
  const isVertical = overlay.system === "wall" || overlay.system === "lateral";
  const lineLength = Math.max(38, Math.min(size.w * 0.32, (overlay.span_ft || 12) * 7));

  if (isPoint) {
    return (
      <g>
        <rect x={x - 7} y={y - 7} width="14" height="14" rx="3" fill={color} />
        <text x={x + 13} y={y + 4} className="svg-label">{overlay.label}</text>
      </g>
    );
  }

  return (
    <g>
      <line
        x1={x}
        y1={y}
        x2={isVertical ? x : x + lineLength}
        y2={isVertical ? y + lineLength : y}
        stroke={color}
        strokeWidth={overlay.system === "lateral" ? 5 : 3}
        strokeLinecap="round"
      />
      <text x={isVertical ? x + 10 : x + lineLength + 8} y={isVertical ? y + lineLength / 2 : y + 4} className="svg-label">
        {overlay.label}
      </text>
    </g>
  );
}

function OverlayList({ overlays }: { overlays: VisualOverlayItem[] }) {
  if (overlays.length === 0) return <div className="muted-row">No overlays available</div>;
  return (
    <div className="overlay-list">
      {overlays.slice(0, 12).map((overlay, index) => (
        <div className="overlay-row" key={`${overlay.item_type}-${overlay.label}-${index}`}>
          <span style={{ background: colorForSystem(overlay.system) }} />
          <div>
            <strong>{overlay.label}</strong>
            <small>
              {overlay.size || overlay.item_type}
              {overlay.span_ft ? ` · ${formatNumber(overlay.span_ft)} ft` : ""}
            </small>
          </div>
        </div>
      ))}
    </div>
  );
}

function AnalysisPanel({
  analysis,
  state,
  activeProject,
}: {
  analysis: AnalysisData | null;
  state: LoadState;
  activeProject: ProjectSummary | null;
}) {
  const items = analysis?.items || [];
  const sortedItems = [...items].sort((a, b) => statusRank(a.status) - statusRank(b.status));

  if (!activeProject) {
    return (
      <section className="empty-state compact">
        <BadgeCheck size={22} />
        <h2>No project selected</h2>
        <p>Open an extracted project to run structural analysis.</p>
      </section>
    );
  }

  if (state === "loading") {
    return (
      <section className="empty-state compact">
        <Loader2 className="spin" size={24} />
        <h2>Running structural analysis</h2>
      </section>
    );
  }

  if (!analysis) {
    return (
      <section className="empty-state compact">
        <AlertCircle size={22} />
        <h2>Analysis unavailable</h2>
        <p>The project extraction loaded, but calculation results were not returned.</p>
      </section>
    );
  }

  return (
    <section className="analysis-layout">
      <div className="analysis-summary">
        <AnalysisSummaryTile label="Overall" value={analysis.summary.overall} tone={analysis.summary.overall} />
        <AnalysisSummaryTile label="Passing" value={analysis.summary.passing} tone="PASS" />
        <AnalysisSummaryTile label="Failing" value={analysis.summary.failing} tone="FAIL" />
        <AnalysisSummaryTile label="Errors" value={analysis.summary.errors} tone="ERROR" />
      </div>

      <div className="analysis-list">
        {sortedItems.length === 0 && <div className="table-empty">No analyzable extracted members found</div>}
        {sortedItems.map((item) => (
          <AnalysisItemCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}

function AnalysisSummaryTile({ label, value, tone }: { label: string; value: string | number; tone: string }) {
  return (
    <div className="analysis-tile" data-tone={tone}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AnalysisItemCard({ item }: { item: AnalysisItem }) {
  const checks = item.checks || [];
  return (
    <article className="analysis-card" data-status={item.status}>
      <div className="analysis-card-head">
        <div>
          <span className="status-badge" data-status={item.status}>
            {item.status}
          </span>
          <h2>{item.label}</h2>
          <p>
            {item.system} · {item.application}
            {item.size ? ` · ${item.size}` : ""}
          </p>
        </div>
        <div className="utilization-gauge">
          <span>{item.max_utilization == null ? "-" : `${formatNumber(item.max_utilization)}%`}</span>
          <small>Max utilization</small>
        </div>
      </div>
      {item.error && <div className="analysis-error">{item.error}</div>}
      {checks.length > 0 && (
        <div className="check-grid">
          {checks.slice(0, 6).map((check) => (
            <div className="check-row" data-status={check.status} key={`${item.id}-${check.name}`}>
              <strong>{check.name}</strong>
              <span>{check.utilization == null ? "-" : `${formatNumber(check.utilization)}%`}</span>
              <small>{check.combo || check.status}</small>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

function SystemsPanel({
  extraction,
  selectedSystem,
  onSelectedSystem,
}: {
  extraction: ExtractionData | null;
  selectedSystem: string;
  onSelectedSystem: (system: string) => void;
}) {
  const items = useMemo(() => flattenSystemItems(extraction?.[selectedSystem]), [extraction, selectedSystem]);

  if (!extraction) {
    return (
      <section className="empty-state compact">
        <PanelLeft size={22} />
        <h2>No extraction selected</h2>
      </section>
    );
  }

  return (
    <section className="systems-layout">
      <nav className="system-list" aria-label="Extracted systems">
        {SYSTEMS.map(({ key, label, icon: Icon }) => (
          <button key={key} className={selectedSystem === key ? "active" : ""} onClick={() => onSelectedSystem(key)}>
            <Icon size={16} />
            <span>{label}</span>
            <strong>{countSystemItems(extraction[key])}</strong>
          </button>
        ))}
      </nav>
      <div className="system-table">
        <div className="table-head">
          <span>Label</span>
          <span>Size</span>
          <span>Span / length</span>
          <span>Note</span>
        </div>
        {items.length === 0 && <div className="table-empty">No items in this system</div>}
        {items.map((item, index) => (
          <div className="table-row" key={`${item.label}-${index}`}>
            <strong>{item.label}</strong>
            <span>{item.size || "-"}</span>
            <span>{item.span || "-"}</span>
            <span>{item.note || "-"}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function RawPanel({
  extraction,
  visualization,
  analysis,
}: {
  extraction: ExtractionData | null;
  visualization: VisualizationData | null;
  analysis: AnalysisData | null;
}) {
  const payload = extraction ? { ...extraction, visualization: visualization || extraction.visualization, analysis } : null;
  return (
    <section className="raw-panel">
      <div className="raw-actions">
        <span>{payload ? "Current extraction payload" : "No payload"}</span>
        <button
          className="ghost-button"
          disabled={!payload}
          onClick={() => {
            if (!payload) return;
            const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = "structure-extraction.json";
            link.click();
            URL.revokeObjectURL(url);
          }}
        >
          <Download size={16} />
          Export
        </button>
      </div>
      <pre>{payload ? JSON.stringify(payload, null, 2) : "{}"}</pre>
    </section>
  );
}

async function pollTask(
  taskId: string,
  apiBase: string,
  onMessage: (message: string) => void,
): Promise<Awaited<ReturnType<typeof checkStatus>>> {
  for (let attempt = 1; attempt <= 120; attempt += 1) {
    await delay(3000);
    const result = await checkStatus(apiBase, taskId);
    if (result.status === "SUCCESS" || result.status === "ERROR") return result;
    onMessage(result.message || `Processing · ${attempt}`);
  }
  throw new ApiError("Extraction timed out", 408);
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function scrollToWorkspaceTop() {
  window.requestAnimationFrame(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

function getExtractionCounts(extraction: ExtractionData | null) {
  return SYSTEMS.reduce<Record<string, number>>((acc, system) => {
    acc[system.key] = countSystemItems(extraction?.[system.key]);
    return acc;
  }, {});
}

function countSystemItems(system: unknown) {
  if (!system || typeof system !== "object") return 0;
  return Object.values(system as Record<string, unknown>).reduce<number>((total, value) => {
    if (Array.isArray(value)) return total + value.length;
    return total;
  }, 0);
}

function flattenSystemItems(system: unknown) {
  if (!system || typeof system !== "object") return [];
  const rows: Array<{ label: string; size: string; span: string; note: string }> = [];
  Object.entries(system as Record<string, unknown>).forEach(([group, value]) => {
    if (!Array.isArray(value)) return;
    value.forEach((raw, index) => {
      const item = raw as Record<string, unknown>;
      rows.push({
        label: String(item.zone || item.post_mark || item.footing_mark || item.sw_mark || item.bwl_id || item.opening_mark || `${group} ${index + 1}`),
        size: String(item.size || item.stud_size || item.header_size || item.post_size || ""),
        span: formatSpan(item),
        note: String(item.clear_span_note || item.wall_length_note || item.dimension_note || item.footing_note || item.sw_note || ""),
      });
    });
  });
  return rows;
}

function formatSpan(item: Record<string, unknown>) {
  const value = [
    item.clear_span_ft,
    item.wall_length_ft,
    item.length_ft,
    item.pier_length_ft,
    item.header_clear_span_ft,
    item.height_ft,
  ].find((candidate): candidate is number => typeof candidate === "number");
  return typeof value === "number" ? `${formatNumber(value)} ft` : "";
}

function formatNumber(value: unknown) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function statusRank(status: string) {
  if (status === "ERROR") return 0;
  if (status === "FAIL") return 1;
  return 2;
}

function pickDimension(context: VisualizationData["context"], direction: "X" | "Y") {
  return context?.dimensions?.find((dimension) => dimension.direction === direction)?.value_ft || null;
}

function colorForSystem(system: string) {
  const colors: Record<string, string> = {
    roof: "#b95f28",
    floor: "#287e9c",
    wall: "#29322d",
    lateral: "#b33b4a",
    foundation: "#6f7770",
    post: "#4e7a45",
  };
  return colors[system] || "#5a635d";
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

declare global {
  interface Window {
    __structureAgentRoot?: Root;
  }
}

const rootElement = document.getElementById("root")!;
const legacyRoot = (rootElement as HTMLElement & { _structureRoot?: Root })._structureRoot;
const root = window.__structureAgentRoot || legacyRoot || createRoot(rootElement);
window.__structureAgentRoot = root;
(rootElement as HTMLElement & { _structureRoot?: Root })._structureRoot = root;

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
