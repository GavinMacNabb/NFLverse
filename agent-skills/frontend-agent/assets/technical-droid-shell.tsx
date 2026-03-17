import { Outlet, useLocation, useNavigate } from "react-router-dom";

const routes = [
  { label: "Dashboard", path: "/" },
  { label: "Scans", path: "/scans" },
  { label: "Networks", path: "/networks" },
  { label: "Hosts", path: "/hosts" },
  { label: "Alerts", path: "/alerts" },
  { label: "Domains", path: "/domains" },
  { label: "Summary", path: "/summary" },
];

export function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="grid min-h-screen grid-cols-[18rem_minmax(0,1fr)] bg-base-100 text-base-content">
      <aside className="border-r border-base-300 bg-base-200/50 p-4 font-mono">
        <div className="space-y-2 border-b border-base-300 pb-4">
          <p className="text-base-content/60 text-xs uppercase tracking-[0.18em]">
            Gatherer
          </p>
          <h1 className="text-lg font-semibold">Technical Droid Console</h1>
          <p className="text-base-content/60 text-xs">
            └─ Real-time network monitoring and discovery
          </p>
        </div>

        <nav className="mt-4 space-y-1">
          {routes.map((route) => {
            const active = location.pathname === route.path;
            return (
              <button
                key={route.path}
                type="button"
                onClick={() => navigate(route.path)}
                className={[
                  "flex w-full items-center justify-between rounded-sm border px-3 py-2 text-left text-sm",
                  active
                    ? "border-primary/40 bg-primary/10"
                    : "border-transparent hover:border-base-300 hover:bg-base-200",
                ].join(" ")}
              >
                <span>{route.label}</span>
                <span className="text-base-content/50 text-xs">→</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="min-w-0">
        <header className="border-b border-base-300 px-6 py-4 font-mono">
          <div className="flex items-end justify-between gap-4">
            <div className="space-y-2">
              <p className="text-base-content/60 text-xs uppercase tracking-[0.18em]">
                Operator View
              </p>
              <h2 className="text-2xl font-semibold">Network Inventory</h2>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-sm border border-base-300 px-3 py-2">
                <div className="text-base-content/60">Scope</div>
                <div>Customer / Region / Site</div>
              </div>
              <div className="rounded-sm border border-base-300 px-3 py-2">
                <div className="text-base-content/60">Status</div>
                <div>Live</div>
              </div>
              <div className="rounded-sm border border-base-300 px-3 py-2">
                <div className="text-base-content/60">Updated</div>
                <div>00:14 UTC</div>
              </div>
            </div>
          </div>
        </header>

        <main className="space-y-5 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
