type DataPanelProps = {
  label: string;
  title: string;
  note?: string;
  children: React.ReactNode;
};

export function DataPanel({ label, title, note, children }: DataPanelProps) {
  return (
    <section className="rounded-sm border border-base-300 bg-base-100">
      <header className="space-y-2 border-b border-base-300 px-4 py-3 font-mono">
        <p className="text-base-content/60 text-xs uppercase tracking-[0.18em]">
          {label}
        </p>
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-sm font-semibold">{title}</h3>
          {note ? <p className="text-base-content/60 text-xs">{note}</p> : null}
        </div>
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}
