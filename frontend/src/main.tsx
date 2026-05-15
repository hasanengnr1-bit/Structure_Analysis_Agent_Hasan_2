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
  CircleDashed,
  Columns3,
  Download,
  Eye,
  FileText,
  Gauge,
  Grid3X3,
  Layers3,
  Loader2,
  LogOut,
  PanelLeft,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";
import {
  ApiError,
  checkStatus,
  deleteProject,
  getAnalysis,
  getProject,
  getProjects,
  getStoredApiBase,
  getStoredToken,
  getVisualization,
  health,
  login,
  setStoredApiBase,
  setStoredToken,
  signup,
  startExtraction,
  trimTrailingSlash,
} from "./api";
import type { AnalysisData, AnalysisItem, ExtractionData, ProjectSummary, VisualizationData } from "./types";
import "./styles.css";

type AuthMode = "login" | "signup";
type LoadState = "idle" | "loading" | "success" | "error";
type StatusFilter = "all" | "PASS" | "FAIL" | "ERROR";

type MemberRecord = {
  id: string;
  systemKey: string;
  systemLabel: string;
  collectionKey: string;
  typeLabel: string;
  label: string;
  size: string;
  span: string;
  spacing: string;
  status: string;
  utilization: number | null;
  raw: Record<string, unknown>;
  analysis?: AnalysisItem;
};

const SYSTEM_CONFIG = [
  {
    key: "roof_system",
    label: "Roof",
    icon: Layers3,
    collections: [
      ["roof_rafters", "Rafter"],
      ["ceiling_joists", "Ceiling Joist"],
      ["ridge_beams", "Ridge Beam"],
      ["hip_valley_rafters", "Hip/Valley"],
      ["roof_drop_beams", "Drop Beam"],
      ["roof_flush_beams", "Flush Beam"],
    ],
  },
  {
    key: "floor_system",
    label: "Floor",
    icon: Grid3X3,
    collections: [
      ["floor_joists", "Floor Joist"],
      ["floor_drop_beams", "Drop Beam"],
      ["floor_flush_beams", "Flush Beam"],
    ],
  },
  {
    key: "wall",
    label: "Wall",
    icon: Columns3,
    collections: [
      ["stud_walls", "Stud Wall"],
      ["headers", "Header"],
      ["top_plates", "Top Plate"],
      ["bottom_plates", "Bottom Plate"],
    ],
  },
  {
    key: "shear_wall",
    label: "Lateral",
    icon: ShieldCheck,
    collections: [
      ["braced_wall_lines", "Braced Wall Line"],
      ["shear_walls", "Shear Wall"],
      ["diaphragms", "Diaphragm"],
    ],
  },
  {
    key: "post",
    label: "Post",
    icon: Box,
    collections: [["standalone_posts", "Post"]],
  },
  {
    key: "footing",
    label: "Foundation",
    icon: Building2,
    collections: [
      ["continuous_strip_footings", "Strip Footing"],
      ["pad_footings", "Pad Footing"],
      ["grade_beams", "Grade Beam"],
      ["slab_on_grade", "Slab"],
      ["holdown_anchors", "Holdown Anchor"],
    ],
  },
] as const;

const demoExtraction: ExtractionData = {
  roof_system: {
    ridge_beams: [
      {
        zone: "Main Ridge",
        size: "(3) 2x12",
        number_of_plies: 3,
        clear_span_ft: 28,
        tributary_width_ft: 14,
        roof_dead_load_psf: 15,
        roof_live_load_psf: 20,
        lumber_spec: { species: "DF-L", grade: "No.2", species_grade_note: "General notes" },
      },
    ],
    roof_rafters: [
      {
        zone: "North Roof Slope",
        size: "2x8",
        clear_span_ft: 14,
        spacing_in: 16,
        roof_pitch: "6/12",
        roof_dead_load_psf: 15,
      },
    ],
    ceiling_joists: [],
    hip_valley_rafters: [{ zone: "West Valley", member_type: "valley", size: "2x10", clear_span_ft: 16, roof_pitch: "6/12" }],
    roof_drop_beams: [],
    roof_flush_beams: [],
  },
  floor_system: {
    floor_joists: [{ zone: "Main Floor Joists", size: "2x10", clear_span_ft: 13.5, spacing_in: 16, dead_load_psf: 10, floor_live_load_psf: 40 }],
    floor_drop_beams: [{ zone: "Center Drop Beam", size: "(3) 2x12", number_of_plies: 3, clear_span_ft: 20, tributary_width_ft: 12 }],
    floor_flush_beams: [],
  },
  wall: {
    stud_walls: [
      { zone: "North Exterior Wall", wall_type: "exterior_bearing", stud_size: "2x6", stud_height_ft: 10, wall_length_ft: 46, spacing_in: 16 },
      { zone: "South Exterior Wall", wall_type: "exterior_bearing", stud_size: "2x6", stud_height_ft: 10, wall_length_ft: 46, spacing_in: 16 },
    ],
    headers: [{ zone: "Great Room Opening", opening_mark: "H1", opening_type: "pass_through", header_size: "(2) 2x12", number_of_plies: 2, header_clear_span_ft: 8 }],
    top_plates: [],
    bottom_plates: [],
  },
  shear_wall: {
    braced_wall_lines: [{ bwl_id: "BWL-A", story_level: "Main", bwl_total_length_ft: 46, total_braced_length_ft: 18 }],
    shear_walls: [{ sw_mark: "SW1", bwl_id: "BWL-A", story_level: "Main", stud_size: "2x6", pier_length_ft: 8, wall_height_ft: 10, sheathing_type: "WSP" }],
    diaphragms: [],
  },
  footing: {
    project_info: { soil_bearing_pressure_psf: 2000, concrete_fc_footings_psi: 2500 },
    continuous_strip_footings: [{ footing_mark: "F1", location_description: "Perimeter", supported_element: "Exterior wall", width_in: 18, depth_in: 10, length_ft: 46 }],
    pad_footings: [{ footing_mark: "P1", location_description: "Center post", supported_element: "Center beam", width_in: 24, length_in: 24, depth_in: 12, post_size: "6x6" }],
    grade_beams: [],
    slab_on_grade: [],
    holdown_anchors: [],
  },
  post: {
    standalone_posts: [{ post_mark: "P1", post_type: "solid", post_size: "6x6", location_description: "Center beam support", height_ft: 9, tributary_area_sf: 120 }],
  },
};

const demoVisualization: VisualizationData = {
  context: {
    drawing_scale: "1/4 in = 1 ft",
    north_arrow: "Up",
    dimensions: [
      { label: "Overall length", value_ft: 46, direction: "X" },
      { label: "Overall width", value_ft: 30, direction: "Y" },
      { label: "Ridge height", value_ft: 23, direction: "vertical" },
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
    elevations: [{ view_name: "Front", eave_height_ft: 10, ridge_height_ft: 23, roof_pitch: "6/12" }],
    ridge_lines: [{ label: "Main ridge", orientation: "E-W", start: { x_ft: 4, y_ft: 15 }, end: { x_ft: 42, y_ft: 15 }, height_ft: 23 }],
    roof_planes: [],
  },
  overlays: [],
  source_systems: ["roof_system", "floor_system", "wall", "shear_wall", "post", "footing"],
};

const demoAnalysis: AnalysisData = {
  summary: { total_items: 9, passing: 8, failing: 1, errors: 0, overall: "FAIL" },
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
  const [backendState, setBackendState] = useState<"online" | "offline" | "checking">("checking");
  const [status, setStatus] = useState("Ready");
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectsState, setProjectsState] = useState<LoadState>("idle");
  const [activeProject, setActiveProject] = useState<ProjectSummary | null>(null);
  const [extraction, setExtraction] = useState<ExtractionData | null>(null);
  const [visualization, setVisualization] = useState<VisualizationData | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [analysisState, setAnalysisState] = useState<LoadState>("idle");
  const [uploadState, setUploadState] = useState<LoadState>("idle");
  const [taskMessage, setTaskMessage] = useState("");
  const [projectSearch, setProjectSearch] = useState("");
  const [memberSearch, setMemberSearch] = useState("");
  const [activeSystem, setActiveSystem] = useState("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [selectedMemberId, setSelectedMemberId] = useState<string>("");

  const normalizedApiBase = useMemo(() => trimTrailingSlash(apiBase), [apiBase]);
  const members = useMemo(() => buildMemberRecords(extraction, analysis), [extraction, analysis]);
  const filteredMembers = useMemo(
    () => filterMembers(members, activeSystem, statusFilter, memberSearch),
    [members, activeSystem, statusFilter, memberSearch],
  );
  const selectedMember = members.find((member) => member.id === selectedMemberId) || filteredMembers[0] || members[0] || null;
  const projectMatches = useMemo(() => {
    const query = projectSearch.trim().toLowerCase();
    if (!query) return projects;
    return projects.filter((project) => `${project.filename} ${project.id}`.toLowerCase().includes(query));
  }, [projectSearch, projects]);

  useEffect(() => {
    let cancelled = false;
    setBackendState("checking");
    health(normalizedApiBase)
      .then(() => !cancelled && setBackendState("online"))
      .catch(() => !cancelled && setBackendState("offline"));
    return () => {
      cancelled = true;
    };
  }, [normalizedApiBase]);

  const loadProjects = useCallback(async () => {
    if (!token) return;
    setProjectsState("loading");
    try {
      setProjects(await getProjects(normalizedApiBase, token));
      setProjectsState("success");
    } catch (error) {
      setProjectsState("error");
      setStatus(getErrorMessage(error));
    }
  }, [normalizedApiBase, token]);

  useEffect(() => {
    if (token) void loadProjects();
  }, [loadProjects, token]);

  useEffect(() => {
    if (!members.length) {
      setSelectedMemberId("");
      return;
    }
    if (!members.some((member) => member.id === selectedMemberId)) {
      setSelectedMemberId(members[0].id);
    }
  }, [members, selectedMemberId]);

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") || "");
    const password = String(form.get("password") || "");
    const name = String(form.get("name") || "");
    setAuthState("loading");
    setStatus(authMode === "signup" ? "Creating account" : "Signing in");
    try {
      if (authMode === "signup") await signup(normalizedApiBase, { name, email, password });
      const nextToken = await login(normalizedApiBase, { email, password });
      setStoredToken(nextToken);
      setStoredApiBase(normalizedApiBase);
      setToken(nextToken);
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
    setAnalysisState("loading");
    try {
      const [projectData, visualData, analysisData] = await Promise.all([
        getProject(normalizedApiBase, token, project.id),
        getVisualization(normalizedApiBase, token, project.id),
        getAnalysis(normalizedApiBase, token, project.id),
      ]);
      setExtraction(projectData);
      setVisualization(visualData || projectData.visualization || null);
      setAnalysis(analysisData);
      setAnalysisState("success");
      setStatus("Project loaded");
    } catch (error) {
      setAnalysisState("error");
      setStatus(getErrorMessage(error));
    }
  }

  async function handleUpload(file: File) {
    setUploadState("loading");
    setTaskMessage("Starting extraction");
    try {
      const started = await startExtraction(normalizedApiBase, token, file);
      if (!started.task_id) throw new ApiError("Extraction started without a task id", 500);
      setTaskMessage(`Task ${started.task_id} running`);
      const result = await pollTask(started.task_id, normalizedApiBase, setTaskMessage);
      if (result.status !== "SUCCESS" || !result.data || typeof result.data === "string") {
        throw new ApiError(typeof result.data === "string" ? result.data : "Extraction failed", 500);
      }
      const projectId = started.project_id || result.project_id || "";
      setActiveProject(projectId ? { id: projectId, filename: file.name } : null);
      setExtraction(result.data);
      setVisualization(result.data.visualization || null);
      if (projectId) {
        setAnalysisState("loading");
        setAnalysis(await getAnalysis(normalizedApiBase, token, projectId));
        setAnalysisState("success");
      }
      setUploadState("success");
      setTaskMessage("");
      setStatus("Extraction and analysis complete");
      await loadProjects();
    } catch (error) {
      setUploadState("error");
      setTaskMessage("");
      setStatus(getErrorMessage(error));
    }
  }

  async function handleDeleteProject(project: ProjectSummary) {
    try {
      await deleteProject(normalizedApiBase, token, project.id);
      if (activeProject?.id === project.id) clearWorkspace();
      await loadProjects();
      setStatus("Project deleted");
    } catch (error) {
      setStatus(getErrorMessage(error));
    }
  }

  function clearWorkspace() {
    setActiveProject(null);
    setExtraction(null);
    setVisualization(null);
    setAnalysis(null);
    setSelectedMemberId("");
  }

  function signOut() {
    setStoredToken("");
    setToken("");
    setProjects([]);
    clearWorkspace();
    setStatus("Signed out");
  }

  function loadDemo() {
    setActiveProject({ id: "demo", filename: "Demo extraction" });
    setExtraction(demoExtraction);
    setVisualization(demoVisualization);
    setAnalysis(demoAnalysis);
    setAnalysisState("success");
    setUploadState("success");
    setStatus("Demo loaded");
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Workspace">
        <Brand />
        <ConnectionPanel apiBase={apiBase} backendState={backendState} onApiBase={setApiBase} />
        {token ? (
          <ProjectRail
            projects={projectMatches}
            state={projectsState}
            activeProject={activeProject}
            search={projectSearch}
            onSearch={setProjectSearch}
            onRefresh={loadProjects}
            onOpen={openProject}
            onDelete={handleDeleteProject}
          />
        ) : (
          <AuthPanel mode={authMode} state={authState} onMode={setAuthMode} onSubmit={handleAuth} />
        )}
        <button className="ghost-button" onClick={token ? signOut : loadDemo}>
          {token ? <LogOut size={16} /> : <Eye size={16} />}
          {token ? "Sign out" : "Demo"}
        </button>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Member workbench</p>
            <h1>{activeProject?.filename || "Structure Analysis Agent"}</h1>
          </div>
          <div className="status-pill" data-state={uploadState}>
            {uploadState === "loading" ? <Loader2 className="spin" size={16} /> : <Activity size={16} />}
            <span>{taskMessage || status}</span>
          </div>
        </header>

        <section className="command-strip">
          <UploadPanel disabled={!token} state={uploadState} onUpload={handleUpload} />
          <Metric label="Members" value={members.length} icon={PanelLeft} />
          <Metric label="Checks" value={analysis?.summary.total_items || 0} icon={BadgeCheck} />
          <Metric label="Failing" value={analysis?.summary.failing || 0} icon={AlertCircle} />
          <Metric label="Errors" value={analysis?.summary.errors || 0} icon={Gauge} />
        </section>

        <Workbench
          members={members}
          filteredMembers={filteredMembers}
          selectedMember={selectedMember}
          visualization={visualization}
          extraction={extraction}
          analysis={analysis}
          analysisState={analysisState}
          activeSystem={activeSystem}
          statusFilter={statusFilter}
          memberSearch={memberSearch}
          onActiveSystem={setActiveSystem}
          onStatusFilter={setStatusFilter}
          onMemberSearch={setMemberSearch}
          onSelectMember={setSelectedMemberId}
          onLoadDemo={loadDemo}
        />
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

function ConnectionPanel({
  apiBase,
  backendState,
  onApiBase,
}: {
  apiBase: string;
  backendState: "online" | "offline" | "checking";
  onApiBase: (value: string) => void;
}) {
  return (
    <div className="connection-panel">
      <label htmlFor="api-base">API base</label>
      <div className="api-row">
        <input
          id="api-base"
          value={apiBase}
          onChange={(event) => onApiBase(event.target.value)}
          onBlur={(event) => {
            const next = trimTrailingSlash(event.currentTarget.value);
            onApiBase(next);
            setStoredApiBase(next);
          }}
        />
        <span className="status-dot" data-state={backendState}>
          {backendState === "online" ? <Check size={14} /> : backendState === "offline" ? <AlertCircle size={14} /> : <CircleDashed size={14} />}
        </span>
      </div>
    </div>
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
        <button type="button" className={mode === "login" ? "active" : ""} onClick={() => onMode("login")}>Login</button>
        <button type="button" className={mode === "signup" ? "active" : ""} onClick={() => onMode("signup")}>Signup</button>
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
        <button type="submit" className="primary-button" disabled={state === "loading"}>
          {state === "loading" ? <Loader2 className="spin" size={16} /> : <ArrowRight size={16} />}
          Continue
        </button>
      </form>
    </section>
  );
}

function ProjectRail({
  projects,
  state,
  activeProject,
  search,
  onSearch,
  onRefresh,
  onOpen,
  onDelete,
}: {
  projects: ProjectSummary[];
  state: LoadState;
  activeProject: ProjectSummary | null;
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
        <input value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search projects" />
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
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <section className={`upload-tool ${disabled ? "disabled" : ""}`}>
      <input ref={inputRef} type="file" accept="application/pdf,.pdf" onChange={(event) => event.target.files?.[0] && onUpload(event.target.files[0])} />
      <button className="upload-action" disabled={disabled || state === "loading"} onClick={() => inputRef.current?.click()}>
        {state === "loading" ? <Loader2 className="spin" size={22} /> : <UploadCloud size={22} />}
        <span>
          <strong>Plan PDF</strong>
          <small>{disabled ? "Login required" : "Extract + analyze"}</small>
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

function Workbench({
  members,
  filteredMembers,
  selectedMember,
  visualization,
  extraction,
  analysis,
  analysisState,
  activeSystem,
  statusFilter,
  memberSearch,
  onActiveSystem,
  onStatusFilter,
  onMemberSearch,
  onSelectMember,
  onLoadDemo,
}: {
  members: MemberRecord[];
  filteredMembers: MemberRecord[];
  selectedMember: MemberRecord | null;
  visualization: VisualizationData | null;
  extraction: ExtractionData | null;
  analysis: AnalysisData | null;
  analysisState: LoadState;
  activeSystem: string;
  statusFilter: StatusFilter;
  memberSearch: string;
  onActiveSystem: (value: string) => void;
  onStatusFilter: (value: StatusFilter) => void;
  onMemberSearch: (value: string) => void;
  onSelectMember: (id: string) => void;
  onLoadDemo: () => void;
}) {
  if (!extraction) {
    return (
      <section className="empty-state">
        <Building2 size={26} />
        <h2>No extraction loaded</h2>
        <p>Upload a structural PDF or open the demo workspace to review extracted members and analysis inputs.</p>
        <button className="primary-button" onClick={onLoadDemo}>
          <Eye size={16} />
          Open demo
        </button>
      </section>
    );
  }

  return (
    <section className="workbench-grid">
      <MemberBrowser
        members={members}
        filteredMembers={filteredMembers}
        selectedMember={selectedMember}
        activeSystem={activeSystem}
        statusFilter={statusFilter}
        memberSearch={memberSearch}
        onActiveSystem={onActiveSystem}
        onStatusFilter={onStatusFilter}
        onMemberSearch={onMemberSearch}
        onSelectMember={onSelectMember}
      />
      <MemberDetail member={selectedMember} analysisState={analysisState} />
      <aside className="right-rail">
        <MiniVisualizer visualization={visualization} selectedMember={selectedMember} />
        <AnalysisSummary analysis={analysis} />
      </aside>
    </section>
  );
}

function MemberBrowser({
  members,
  filteredMembers,
  selectedMember,
  activeSystem,
  statusFilter,
  memberSearch,
  onActiveSystem,
  onStatusFilter,
  onMemberSearch,
  onSelectMember,
}: {
  members: MemberRecord[];
  filteredMembers: MemberRecord[];
  selectedMember: MemberRecord | null;
  activeSystem: string;
  statusFilter: StatusFilter;
  memberSearch: string;
  onActiveSystem: (value: string) => void;
  onStatusFilter: (value: StatusFilter) => void;
  onMemberSearch: (value: string) => void;
  onSelectMember: (id: string) => void;
}) {
  return (
    <section className="member-browser">
      <div className="panel-title">
        <div>
          <p className="eyebrow">Extracted members</p>
          <h2>{filteredMembers.length} of {members.length}</h2>
        </div>
        <SlidersHorizontal size={18} />
      </div>
      <label className="searchbox">
        <Search size={15} />
        <input value={memberSearch} onChange={(event) => onMemberSearch(event.target.value)} placeholder="Search members" />
      </label>
      <div className="filter-row">
        <select value={activeSystem} onChange={(event) => onActiveSystem(event.target.value)}>
          <option value="all">All systems</option>
          {SYSTEM_CONFIG.map((system) => (
            <option key={system.key} value={system.key}>{system.label}</option>
          ))}
        </select>
        <select value={statusFilter} onChange={(event) => onStatusFilter(event.target.value as StatusFilter)}>
          <option value="all">All results</option>
          <option value="PASS">Pass</option>
          <option value="FAIL">Fail</option>
          <option value="ERROR">Error</option>
        </select>
      </div>
      <div className="member-list">
        {filteredMembers.map((member) => (
          <button
            key={member.id}
            className={`member-row ${selectedMember?.id === member.id ? "active" : ""}`}
            onClick={() => onSelectMember(member.id)}
          >
            <span className="status-bar" data-status={member.status} />
            <span>
              <strong>{member.label}</strong>
              <small>{member.systemLabel} / {member.typeLabel}</small>
            </span>
            <span className="member-size">{member.size || "-"}</span>
          </button>
        ))}
        {filteredMembers.length === 0 && <div className="table-empty">No members match the filters</div>}
      </div>
    </section>
  );
}

function MemberDetail({ member, analysisState }: { member: MemberRecord | null; analysisState: LoadState }) {
  if (!member) {
    return (
      <section className="member-detail empty-detail">
        <PanelLeft size={22} />
        <h2>Select a member</h2>
      </section>
    );
  }

  const inputEntries = Object.entries(flattenObject(member.raw)).filter(([, value]) => value !== "" && value !== null && value !== undefined);
  const checks = member.analysis?.checks || [];

  return (
    <section className="member-detail">
      <header className="detail-header">
        <div>
          <span className="status-badge" data-status={member.status}>{member.status}</span>
          <h2>{member.label}</h2>
          <p>{member.systemLabel} / {member.typeLabel}{member.size ? ` / ${member.size}` : ""}</p>
        </div>
        <div className="util-box">
          <strong>{member.utilization == null ? "-" : `${formatNumber(member.utilization)}%`}</strong>
          <span>Max utilization</span>
        </div>
      </header>

      <section className="detail-section">
        <div className="section-heading">
          <h3>Inputs extracted from PDF</h3>
          <span>{inputEntries.length} fields</span>
        </div>
        <div className="input-grid">
          {inputEntries.map(([key, value]) => (
            <div className="input-cell" key={key}>
              <label>{humanize(key)}</label>
              <strong>{formatValue(value)}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="detail-section">
        <div className="section-heading">
          <h3>Structural analysis</h3>
          <span>{analysisState === "loading" ? "Running" : `${checks.length} checks`}</span>
        </div>
        {member.analysis?.error && <div className="analysis-error">{member.analysis.error}</div>}
        <div className="checks-table">
          <div className="checks-head">
            <span>Check</span>
            <span>Actual</span>
            <span>Allowed</span>
            <span>Util.</span>
            <span>Combo</span>
          </div>
          {checks.map((check) => (
            <div className="checks-row" data-status={check.status} key={`${member.id}-${check.name}`}>
              <strong>{check.name}</strong>
              <span>{formatValue(check.actual)}</span>
              <span>{formatValue(check.allowed)}</span>
              <span>{check.utilization == null ? "-" : `${formatNumber(check.utilization)}%`}</span>
              <span>{check.combo || "-"}</span>
            </div>
          ))}
          {checks.length === 0 && <div className="table-empty">No calculation checks for this member yet</div>}
        </div>
      </section>
    </section>
  );
}

function MiniVisualizer({ visualization, selectedMember }: { visualization: VisualizationData | null; selectedMember: MemberRecord | null }) {
  const context = visualization?.context;
  const footprint = context?.footprints?.[0];
  const length = footprint?.overall_length_ft || context?.dimensions?.find((dim) => dim.direction === "X")?.value_ft || 46;
  const width = footprint?.overall_width_ft || context?.dimensions?.find((dim) => dim.direction === "Y")?.value_ft || 30;
  const scale = Math.min(248 / length, 172 / width);
  const drawW = length * scale;
  const drawH = width * scale;
  const x = 24 + (248 - drawW) / 2;
  const y = 42 + (172 - drawH) / 2;

  return (
    <section className="mini-visualizer">
      <div className="panel-title compact">
        <div>
          <p className="eyebrow">Visualizer</p>
          <h2>{selectedMember?.label || "Plan"}</h2>
        </div>
      </div>
      <svg viewBox="0 0 296 244" role="img" aria-label="Compact plan visualizer">
        <rect x="1" y="1" width="294" height="242" rx="8" fill="#fff" stroke="#dce2da" />
        <rect x={x} y={y} width={drawW} height={drawH} fill="#eef3ec" stroke="#29322d" strokeWidth="2" />
        <line x1={x + drawW * 0.12} y1={y + drawH / 2} x2={x + drawW * 0.88} y2={y + drawH / 2} stroke="#b95f28" strokeWidth="3" />
        <circle cx={x + drawW * 0.18} cy={y + drawH * 0.72} r="5" fill="#4e7a45" />
        <line x1={x + drawW * 0.18} y1={y + drawH * 0.36} x2={x + drawW * 0.18} y2={y + drawH * 0.9} stroke="#29322d" strokeWidth="3" />
        <text x={x + drawW - 4} y={y - 8} textAnchor="end" className="mini-svg-text">{formatNumber(length)} x {formatNumber(width)} ft</text>
        {selectedMember && (
          <g>
            <rect x="20" y="210" width="256" height="22" rx="5" fill="#f0f3ee" />
            <text x="30" y="225" className="mini-svg-text">{selectedMember.systemLabel} / {selectedMember.typeLabel}</text>
          </g>
        )}
      </svg>
    </section>
  );
}

function AnalysisSummary({ analysis }: { analysis: AnalysisData | null }) {
  return (
    <section className="analysis-summary-panel">
      <div className="panel-title compact">
        <div>
          <p className="eyebrow">Analysis</p>
          <h2>{analysis?.summary.overall || "Not run"}</h2>
        </div>
      </div>
      <div className="summary-grid">
        <span><strong>{analysis?.summary.total_items || 0}</strong> items</span>
        <span><strong>{analysis?.summary.passing || 0}</strong> pass</span>
        <span><strong>{analysis?.summary.failing || 0}</strong> fail</span>
        <span><strong>{analysis?.summary.errors || 0}</strong> errors</span>
      </div>
    </section>
  );
}

async function pollTask(taskId: string, apiBase: string, onMessage: (message: string) => void) {
  for (let attempt = 1; attempt <= 120; attempt += 1) {
    await delay(3000);
    const result = await checkStatus(apiBase, taskId);
    if (result.status === "SUCCESS" || result.status === "ERROR") return result;
    onMessage(result.message || `Processing ${attempt}`);
  }
  throw new ApiError("Extraction timed out", 408);
}

function buildMemberRecords(extraction: ExtractionData | null, analysis: AnalysisData | null): MemberRecord[] {
  if (!extraction) return [];
  const records: MemberRecord[] = [];

  SYSTEM_CONFIG.forEach((system) => {
    const systemData = extraction[system.key] as Record<string, unknown> | undefined;
    if (!systemData || typeof systemData !== "object") return;

    system.collections.forEach(([collectionKey, typeLabel]) => {
      const items = systemData[collectionKey];
      if (!Array.isArray(items)) return;
      items.forEach((raw, index) => {
        if (!raw || typeof raw !== "object") return;
        const item = raw as Record<string, unknown>;
        const label = getLabel(item, typeLabel, index);
        const itemAnalysis = findAnalysisItem(analysis, system.key, collectionKey, label, index);
        records.push({
          id: `${system.key}:${collectionKey}:${index}`,
          systemKey: system.key,
          systemLabel: system.label,
          collectionKey,
          typeLabel,
          label,
          size: getSize(item),
          span: getSpan(item),
          spacing: getSpacing(item),
          status: itemAnalysis?.status || "UNRUN",
          utilization: itemAnalysis?.max_utilization ?? null,
          raw: item,
          analysis: itemAnalysis,
        });
      });
    });
  });

  return records;
}

function filterMembers(members: MemberRecord[], system: string, status: StatusFilter, search: string) {
  const query = search.trim().toLowerCase();
  return members.filter((member) => {
    if (system !== "all" && member.systemKey !== system) return false;
    if (status !== "all" && member.status !== status) return false;
    if (!query) return true;
    return `${member.label} ${member.size} ${member.systemLabel} ${member.typeLabel}`.toLowerCase().includes(query);
  });
}

function findAnalysisItem(analysis: AnalysisData | null, systemKey: string, collectionKey: string, label: string, index: number) {
  if (!analysis) return undefined;
  const sameCollection = analysis.items.filter((item) => item.source_system === systemKey && item.source_collection === collectionKey);
  return sameCollection.find((item) => item.label === label) || sameCollection[index];
}

function getLabel(item: Record<string, unknown>, fallback: string, index: number) {
  return String(item.zone || item.post_mark || item.footing_mark || item.sw_mark || item.bwl_id || item.opening_mark || item.location_description || `${fallback} ${index + 1}`);
}

function getSize(item: Record<string, unknown>) {
  return String(item.size || item.stud_size || item.header_size || item.post_size || item.sill_plate_size || "");
}

function getSpan(item: Record<string, unknown>) {
  const value = [item.clear_span_ft, item.wall_length_ft, item.length_ft, item.pier_length_ft, item.header_clear_span_ft, item.height_ft].find(
    (candidate): candidate is number => typeof candidate === "number",
  );
  return value == null ? "" : `${formatNumber(value)} ft`;
}

function getSpacing(item: Record<string, unknown>) {
  const value = [item.spacing_in, item.stud_spacing_in, item.rebar_spacing_in, item.transverse_rebar_spacing_in].find(
    (candidate): candidate is number => typeof candidate === "number",
  );
  return value == null ? "" : `${formatNumber(value)} in`;
}

function flattenObject(value: Record<string, unknown>, prefix = ""): Record<string, unknown> {
  return Object.entries(value).reduce<Record<string, unknown>>((acc, [key, raw]) => {
    const nextKey = prefix ? `${prefix}.${key}` : key;
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      Object.assign(acc, flattenObject(raw as Record<string, unknown>, nextKey));
    } else {
      acc[nextKey] = raw;
    }
    return acc;
  }, {});
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.map(formatValue).join(", ") : "-";
  return String(value);
}

function formatNumber(value: unknown) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function humanize(key: string) {
  return key.replace(/\./g, " / ").replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
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
