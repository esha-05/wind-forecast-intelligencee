import { useCallback, useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
type Row = { startTime: string; forecast: number | null; publishTime: string | null; actual?: number | null; error?: number | null; abs_error?: number | null; status: string };
type M = { mae: number | null; rmse: number | null; bias: number | null; mape_pct: number | null; mape_excluded: number; matched: number; expected: number; coverage_pct: number | null };
type Resp = { rows: Row[]; metrics?: M; cutoff_rule: string; fetched_at: string; date: string; cutoff: string };
const f = (v?: number | null, d = 1) => (v == null ? "n/a" : v.toFixed(d));
const hhmm = (s: string) => s.slice(11, 16);

export default function App() {
  const [tab, setTab] = useState<"forecast" | "accuracy">("forecast");
  const [date, setDate] = useState("2026-01-15");
  const [cutoff, setCutoff] = useState("08:00");
  const [d, setD] = useState<Resp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (refresh = false) => {
    setLoading(true); setErr(null);
    try {
      if (refresh) { const r = await fetch(`${API}/api/refresh`, { method: "POST" }); if (!r.ok) throw new Error(`Refresh failed (${r.status})`); }
      const r = await fetch(`${API}/api/${tab}?date=${date}&cutoff=${cutoff}`);
      if (!r.ok) { const b = await r.json().catch(() => ({})); throw new Error(typeof b.detail === "string" ? b.detail : `Request failed (${r.status})`); }
      setD(await r.json());
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); setD(null); }
    finally { setLoading(false); }
  }, [tab, date, cutoff]);
  useEffect(() => { void load(); }, [load]);

  const rows = d?.rows ?? [];
  const avail = rows.filter(r => r.forecast != null);
  const avg = avail.length ? avail.reduce((s, r) => s + (r.forecast as number), 0) / avail.length : null;
  const data = rows.map(r => ({ t: hhmm(r.startTime), forecast: r.forecast, actual: r.actual ?? null, error: r.error ?? null }));

  return (<>
    <header><h1 style={{ margin: 0 }}>Wind Forecast Intelligence</h1>
      <small>Elexon FUELHH (actual, WIND) and WINDFOR (forecast) only. Units as reported by source, not independently confirmed.</small></header>
    <main>
      <div className="bar">
        <button className={tab === "forecast" ? "on" : ""} onClick={() => setTab("forecast")}>Forecast Overview</button>
        <button className={tab === "accuracy" ? "on" : ""} onClick={() => setTab("accuracy")}>Accuracy Analysis</button>
      </div>
      <div className="bar">
        <label>Delivery date<input type="date" min="2026-01-01" max="2026-01-31" value={date} onChange={e => setDate(e.target.value)} /></label>
        <label>Decision cutoff (UTC, day before)<input type="time" value={cutoff} onChange={e => e.target.value && setCutoff(e.target.value)} /></label>
        <button onClick={() => void load(true)}>Refresh from Elexon</button>
      </div>
      {loading && <p>Loading…</p>}
      {err && <div className="err" role="alert">Error: {err}</div>}
      {d && !loading && (rows.length === 0 ? <p>No data for this selection.</p> : <>
        <p className="note">Delivery {d.date}, decision cutoff {d.cutoff} UTC on the previous day. Last retrieved {d.fetched_at}. {d.cutoff_rule}</p>
        {tab === "forecast" ? (
          <div className="cards"><div className="card">Mean forecast over day ({avail.length}/{rows.length} intervals)<b>{f(avg)}</b></div>
            <div className="card">Missing forecast intervals<b>{rows.length - avail.length}</b></div></div>
        ) : d.metrics && (
          <div className="cards">
            <div className="card">MAE<b>{f(d.metrics.mae)}</b></div><div className="card">RMSE<b>{f(d.metrics.rmse)}</b></div>
            <div className="card">Bias (mean forecast − actual)<b>{f(d.metrics.bias)}</b></div>
            <div className="card">MAPE<b>{f(d.metrics.mape_pct)}%</b>{d.metrics.mape_excluded} excluded (|actual|&lt;1)</div>
            <div className="card">Coverage<b>{f(d.metrics.coverage_pct)}%</b>{d.metrics.matched}/{d.metrics.expected} intervals</div>
          </div>)}
        

{/* FIRST GRAPH: Forecast and Actual */}
<ResponsiveContainer width="100%" height={300}>
  <LineChart data={data}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="t" interval={5} />
    <YAxis />
    <Tooltip />
    <Legend />

    <Line
      type="linear"
      dataKey="forecast"
      name="Forecast"
      stroke="#14b8a6"
      strokeWidth={2}
      dot={{ r: 2 }}
      connectNulls={true}
    />

    {tab === "accuracy" && (
      <Line
        type="monotone"
        dataKey="actual"
        name="Actual"
        stroke="#0b1f3a"
        strokeWidth={2}
        dot={false}
      />
    )}
  </LineChart>
</ResponsiveContainer>

{/* SECOND GRAPH: Forecast Error */}
{tab === "accuracy" && (
  <ResponsiveContainer width="100%" height={220}>
    <LineChart data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="t" interval={5} />
      <YAxis />
      <Tooltip />

      <ReferenceLine
        y={0}
        stroke="#64748b"
        label="Zero"
      />

      <Line
        type="monotone"
        dataKey="error"
        name="Error (Forecast - Actual)"
        stroke="#b45309"
        strokeWidth={2}
        dot={{ r: 3 }}
        activeDot={{ r: 5 }}
        connectNulls={true}
      />
    </LineChart>
  </ResponsiveContainer>
)}


        <div className="scroll"><table><thead><tr><th>Delivery (UTC)</th><th>Forecast</th>{tab === "accuracy" && <><th>Actual</th><th>Error</th><th>Abs error</th></>}<th>publishTime</th><th>Status</th></tr></thead>
          <tbody>{rows.map(r => <tr key={r.startTime}><td>{r.startTime}</td><td>{f(r.forecast)}</td>
            {tab === "accuracy" && <><td>{f(r.actual)}</td><td>{f(r.error)}</td><td>{f(r.abs_error)}</td></>}
            <td>{r.publishTime ?? "n/a"}</td><td className={r.status === "matched" ? "" : "miss"}>{r.status.replace("_", " ")}</td></tr>)}</tbody></table></div>
      </>)}
    </main></>);
}
