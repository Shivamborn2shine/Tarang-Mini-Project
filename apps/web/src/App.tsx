import { useEffect, useState } from "react";

interface Project {
  id: string;
  name: string;
  map_mode: "indoor" | "outdoor";
  created_at: string;
}

interface Session {
  id: string;
  project_id: string;
  device_id: string;
  started_at: string;
  status: string;
}

interface Observation {
  id: string;
  kind: "wifi" | "cellular";
  technology: string;
  source: string;
  observed_at: string;
  freshness_ms: number | null;
  location:
    | { kind: "indoor"; floorplan_id: string; x_norm: number; y_norm: number }
    | { kind: "outdoor"; lat: number; lon: number; gps_accuracy_m: number | null }
    | { kind: "unknown" };
  metrics: {
    rssi_dbm?: number | null;
    quality_percent?: number | null;
    rsrp_dbm?: number | null;
    frequency_mhz?: number | null;
  };
  network: {
    ssid?: string | null;
    operator_name?: string | null;
    is_connected?: boolean;
  };
  flags: string[];
}

interface Summary {
  project_id: string;
  session_count?: number;
  total_observations: number;
  by_kind: Record<string, number>;
  by_technology: Record<string, number>;
}

function classifyRssi(rssi: number | null | undefined): { label: string; color: string } {
  if (rssi == null) return { label: "N/A", color: "#64748b" };
  if (rssi >= -55) return { label: "Excellent", color: "#2563eb" };
  if (rssi >= -67) return { label: "Good", color: "#0d9488" };
  if (rssi >= -75) return { label: "Fair", color: "#d97706" };
  return { label: "Weak", color: "#dc2626" };
}

export default function App() {
  const [health, setHealth] = useState<"checking" | "ok" | "offline">("checking");
  const [tab, setTab] = useState<"overview" | "map" | "observations">("overview");
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>("");
  const [observations, setObservations] = useState<Observation[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [newName, setNewName] = useState("");
  const [newMode, setNewMode] = useState<"indoor" | "outdoor">("indoor");
  const [kindFilter, setKindFilter] = useState<"all" | "wifi" | "cellular">("all");
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  async function refreshProjects() {
    try {
      const h = await fetch("/health");
      setHealth(h.ok ? "ok" : "offline");
      const res = await fetch("/api/v1/projects");
      if (res.ok) {
        const list: Project[] = await res.json();
        setProjects(list);
        if (list.length > 0 && !selectedProjectId) {
          setSelectedProjectId(list[0].id);
        }
      }
    } catch {
      setHealth("offline");
    }
  }

  useEffect(() => {
    refreshProjects();
  }, []);

  useEffect(() => {
    if (!selectedProjectId) {
      setSessions([]);
      setSummary(null);
      return;
    }
    (async () => {
      const [sRes, sumRes] = await Promise.all([
        fetch(`/api/v1/projects/${selectedProjectId}/sessions`),
        fetch(`/api/v1/projects/${selectedProjectId}/summary`),
      ]);
      if (sRes.ok) {
        const sList: Session[] = await sRes.json();
        setSessions(sList);
        setSelectedSessionId(sList[0]?.id ?? "");
      }
      if (sumRes.ok) {
        setSummary(await sumRes.json());
      }
    })();
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedSessionId) {
      setObservations([]);
      return;
    }
    (async () => {
      const qs = kindFilter !== "all" ? `&kind=${kindFilter}` : "";
      const res = await fetch(`/api/v1/sessions/${selectedSessionId}/observations?limit=200${qs}`);
      if (res.ok) {
        const data = await res.json();
        setObservations(data.items ?? []);
      }
    })();
  }, [selectedSessionId, kindFilter]);

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setBusy(true);
    try {
      const res = await fetch("/api/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim(), map_mode: newMode }),
      });
      if (res.ok) {
        const created: Project = await res.json();
        setNewName("");
        setProjects((prev) => [created, ...prev]);
        setSelectedProjectId(created.id);
        setStatusMsg(`Created project "${created.name}".`);
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleSeedDemo() {
    setBusy(true);
    setStatusMsg(null);
    try {
      const projRes = await fetch("/api/v1/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "Home Indoor Demo Survey", map_mode: "indoor" }),
      });
      const proj: Project = await projRes.json();

      const deviceId = crypto.randomUUID();
      await fetch("/api/v1/devices/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: deviceId,
          platform: "android",
          model: "Demo Phone",
          os_version: "14",
          app_version: "0.1.0",
          capability_json: { wifi: true, lte: true },
        }),
      });

      const sessRes = await fetch("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: proj.id, device_id: deviceId, settings_json: { interval_s: 5 } }),
      });
      const sess: Session = await sessRes.json();

      const floorplanId = crypto.randomUUID();
      const points = [
        { x: 0.18, y: 0.25, rssi: -48 },
        { x: 0.34, y: 0.28, rssi: -54 },
        { x: 0.52, y: 0.35, rssi: -62 },
        { x: 0.72, y: 0.42, rssi: -71 },
        { x: 0.85, y: 0.65, rssi: -81 },
        { x: 0.62, y: 0.78, rssi: -74 },
        { x: 0.28, y: 0.72, rssi: -60 },
      ];
      const now = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
      const obsPayload = points.map((pt) => ({
        schema_version: 1,
        id: crypto.randomUUID(),
        session_id: sess.id,
        device_id: deviceId,
        kind: "wifi",
        technology: "wifi_5ghz",
        source: "android_wifi",
        observed_at: now,
        recorded_at: now,
        freshness_ms: 400,
        location: { kind: "indoor", floorplan_id: floorplanId, x_norm: pt.x, y_norm: pt.y },
        metrics: { rssi_dbm: pt.rssi, frequency_mhz: 5180, quality_percent: null },
        network: { ssid: "SurveyWiFi", bssid_hash: "9c3f1a8d2e7b4c01", is_connected: true },
        flags: [],
      }));

      await fetch("/api/v1/observations/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_id: crypto.randomUUID(), device_id: deviceId, observations: obsPayload }),
      });

      await refreshProjects();
      setSelectedProjectId(proj.id);
      setTab("map");
      setStatusMsg("Seeded 7 indoor Wi-Fi observations into a new demo project.");
    } finally {
      setBusy(false);
    }
  }

  const activeProject = projects.find((p) => p.id === selectedProjectId) ?? null;

  return (
    <div style={{ maxWidth: 1120, margin: "0 auto", padding: "24px 20px" }}>
      <header style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 16, paddingBottom: 16, borderBottom: "1px solid var(--border)" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24 }}>TARANG</h1>
          <div style={{ fontSize: 13, color: "var(--muted)" }}>
            Telecommunication Analysis, Radio-frequency Assessment, Network Geomapping
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 12, padding: "4px 10px", borderRadius: 999, border: "1px solid var(--border)", background: "var(--card)" }}>
            API: <strong style={{ color: health === "ok" ? "var(--good)" : "var(--weak)" }}>{health}</strong>
          </span>
          <button
            onClick={handleSeedDemo}
            disabled={busy || health !== "ok"}
            style={{ background: "var(--primary)", color: "var(--primary-fg)", border: "none", borderRadius: 8, padding: "8px 14px", fontSize: 13, fontWeight: 600 }}
          >
            + Seed Demo Survey
          </button>
        </div>
      </header>

      <nav style={{ display: "flex", gap: 8, margin: "16px 0" }}>
        {(["overview", "map", "observations"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: tab === t ? "var(--text)" : "var(--card)",
              color: tab === t ? "#fff" : "var(--text)",
              fontSize: 13,
              fontWeight: 600,
              textTransform: "capitalize",
            }}
          >
            {t === "map" ? "Map Explorer" : t}
          </button>
        ))}
      </nav>

      {statusMsg && (
        <div style={{ marginBottom: 16, padding: "10px 14px", borderRadius: 8, background: "#ccfbf1", color: "#115e59", fontSize: 13 }}>
          {statusMsg}
        </div>
      )}

      {/* Project & Session Selector */}
      <section style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 20, padding: 14, background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10 }}>
        <label style={{ fontSize: 13 }}>
          Project:{" "}
          <select value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)} style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)" }}>
            {projects.length === 0 && <option value="">No projects yet</option>}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.map_mode})
              </option>
            ))}
          </select>
        </label>

        <label style={{ fontSize: 13 }}>
          Session:{" "}
          <select value={selectedSessionId} onChange={(e) => setSelectedSessionId(e.target.value)} style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)" }}>
            {sessions.length === 0 && <option value="">No sessions</option>}
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id.slice(0, 8)} ({s.status})
              </option>
            ))}
          </select>
        </label>

        {selectedProjectId && (
          <a
            href={`/api/v1/projects/${selectedProjectId}/export?format=csv`}
            style={{ marginLeft: "auto", fontSize: 13, padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)", textDecoration: "none", color: "var(--text)" }}
          >
            Export CSV
          </a>
        )}
      </section>

      {tab === "overview" && (
        <div style={{ display: "grid", gap: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
            <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>Projects</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{projects.length}</div>
            </div>
            <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>Total Observations</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{summary?.total_observations ?? 0}</div>
            </div>
            <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>Wi-Fi Samples</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{summary?.by_kind?.wifi ?? 0}</div>
            </div>
            <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>Cellular Samples</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{summary?.by_kind?.cellular ?? 0}</div>
            </div>
          </div>

          <form onSubmit={handleCreateProject} style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16, display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
            <strong style={{ fontSize: 14 }}>New Survey Project</strong>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Home Ground Floor"
              style={{ flex: 1, minWidth: 200, padding: "7px 10px", borderRadius: 6, border: "1px solid var(--border)" }}
            />
            <select value={newMode} onChange={(e) => setNewMode(e.target.value as "indoor" | "outdoor")} style={{ padding: "7px 10px", borderRadius: 6, border: "1px solid var(--border)" }}>
              <option value="indoor">indoor</option>
              <option value="outdoor">outdoor</option>
            </select>
            <button type="submit" disabled={busy} style={{ padding: "8px 14px", borderRadius: 6, border: "none", background: "var(--text)", color: "#fff", fontSize: 13, fontWeight: 600 }}>
              Create Project
            </button>
          </form>
        </div>
      )}

      {tab === "map" && (
        <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div>
              <strong>{activeProject ? `${activeProject.name} (${activeProject.map_mode})` : "Select a project"}</strong>
              <div style={{ fontSize: 12, color: "var(--muted)" }}>
                Raw sample points only — heuristic Wi-Fi RSSI bands (dBm). Areas without samples are not interpolated.
              </div>
            </div>
            <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
              <span style={{ color: "#2563eb" }}>● Excellent (&ge;-55)</span>
              <span style={{ color: "#0d9488" }}>● Good (-56..-67)</span>
              <span style={{ color: "#d97706" }}>● Fair (-68..-75)</span>
              <span style={{ color: "#dc2626" }}>● Weak (&lt;-75)</span>
            </div>
          </div>

          <svg viewBox="0 0 800 420" style={{ width: "100%", height: 400, background: "#f1f5f9", borderRadius: 8, border: "1px solid var(--border)" }}>
            {[0.2, 0.4, 0.6, 0.8].map((g) => (
              <g key={g}>
                <line x1={g * 800} y1={0} x2={g * 800} y2={420} stroke="#cbd5e1" strokeDasharray="4 4" />
                <line x1={0} y1={g * 420} x2={800} y2={g * 420} stroke="#cbd5e1" strokeDasharray="4 4" />
              </g>
            ))}
            {observations
              .filter((o) => o.location.kind === "indoor")
              .map((o) => {
                const loc = o.location as { kind: "indoor"; x_norm: number; y_norm: number };
                const cx = loc.x_norm * 800;
                const cy = loc.y_norm * 420;
                const { label, color } = classifyRssi(o.metrics.rssi_dbm);
                return (
                  <g key={o.id}>
                    <circle cx={cx} cy={cy} r={10} fill={color} fillOpacity={0.85} stroke="#fff" strokeWidth={2} />
                    <text x={cx + 14} y={cy + 4} fontSize={12} fill="#0f172a" fontWeight={600}>
                      {o.metrics.rssi_dbm != null ? `${o.metrics.rssi_dbm} dBm (${label})` : label}
                    </text>
                  </g>
                );
              })}
          </svg>
        </div>
      )}

      {tab === "observations" && (
        <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            <strong>Observations ({observations.length})</strong>
            <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value as "all" | "wifi" | "cellular")} style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border)" }}>
              <option value="all">All kinds</option>
              <option value="wifi">Wi-Fi</option>
              <option value="cellular">Cellular</option>
            </select>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)", color: "var(--muted)" }}>
                  <th style={{ padding: "8px 6px" }}>Kind</th>
                  <th style={{ padding: "8px 6px" }}>Technology</th>
                  <th style={{ padding: "8px 6px" }}>Source</th>
                  <th style={{ padding: "8px 6px" }}>Signal</th>
                  <th style={{ padding: "8px 6px" }}>Location</th>
                  <th style={{ padding: "8px 6px" }}>Flags</th>
                </tr>
              </thead>
              <tbody>
                {observations.map((o) => (
                  <tr key={o.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "8px 6px" }}>{o.kind}</td>
                    <td style={{ padding: "8px 6px" }}>{o.technology}</td>
                    <td style={{ padding: "8px 6px" }}>{o.source}</td>
                    <td style={{ padding: "8px 6px" }}>
                      {o.metrics.rssi_dbm != null ? `${o.metrics.rssi_dbm} dBm` : o.metrics.rsrp_dbm != null ? `${o.metrics.rsrp_dbm} dBm RSRP` : o.metrics.quality_percent != null ? `${o.metrics.quality_percent}%` : "N/A"}
                    </td>
                    <td style={{ padding: "8px 6px" }}>{o.location.kind}</td>
                    <td style={{ padding: "8px 6px" }}>{o.flags.join(", ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
