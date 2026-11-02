/* Run + reset buttons, with the running / out-of-date / error messages of a tab. */
export default function RunControls({ label, onRun, onReset, disabled, loading, loadingHint, stale, error, needs }) {
  return (
    <div className="space-y-2 border-t border-slate-200 pt-4">
      <div className="flex gap-2">
        <button type="button" className="btn btn-primary flex-1" onClick={onRun} disabled={disabled || loading}>
          {loading && <span className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
          {loading ? "Running…" : label}
        </button>
        <button type="button" className="btn" onClick={onReset} disabled={loading}>
          Reset options
        </button>
      </div>
      {loading && loadingHint && <p className="text-xs text-slate-500">{loadingHint}</p>}
      {!loading && needs && <p className="text-xs text-slate-500">{needs}</p>}
      {!loading && stale && (
        <p className="rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800">
          Input or options changed since the last run. Run again to update the result.
        </p>
      )}
      {error && <p className="rounded-md bg-red-50 px-2 py-1 text-sm text-red-700">{error}</p>}
    </div>
  );
}
