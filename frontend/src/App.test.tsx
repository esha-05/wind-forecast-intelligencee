import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import App from "./App";

// SYNTHETIC test payloads, not Elexon data.
const row = (t: string, forecast: number | null, status: string) => ({ startTime: t, forecast, publishTime: forecast == null ? null : "2026-01-14T08:00:00Z", status });
const ok = { date: "2026-01-15", cutoff: "08:00", cutoff_rule: "rule", fetched_at: "now", rows: [row("2026-01-15T00:00:00Z", 100, "matched"), row("2026-01-15T00:30:00Z", null, "missing_both")] };

beforeEach(() => { vi.restoreAllMocks(); });
const mock = (r: Partial<Response> & { json: () => Promise<unknown> }) => vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, ...r }));

test("renders data, KPI and missing status", async () => {
  mock({ json: async () => ok });
  render(<App />);
  expect(screen.getByText("Wind Forecast Intelligence")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("missing both")).toBeInTheDocument());
  expect(screen.getByText(/1\/2 intervals/)).toBeInTheDocument();
});

test("shows error state", async () => {
  mock({ ok: false, status: 502, json: async () => ({ detail: "Elexon data unavailable" }) });
  render(<App />);
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Elexon data unavailable"));
});

test("shows empty state and refresh posts", async () => {
  mock({ json: async () => ({ ...ok, rows: [] }) });
  render(<App />);
  await waitFor(() => expect(screen.getByText(/No data/)).toBeInTheDocument());
  fireEvent.click(screen.getByText("Refresh from Elexon"));
  await waitFor(() => expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.some(c => c[1]?.method === "POST")).toBe(true));
});
