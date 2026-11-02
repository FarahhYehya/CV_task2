/* Choose the input of a tab: the upload or any stored result. sources: [{key, label, src}] */
export default function InputPicker({ sources, value, onChange }) {
  return (
    <div className="space-y-2">
      <p className="label">Input image</p>
      <div className="grid grid-cols-2 gap-2">
        {sources.map((source) => (
          <button
            key={source.key}
            type="button"
            onClick={() => onChange(source.key)}
            className={`rounded-lg border p-1 text-left transition ${
              source.key === value
                ? "border-indigo-500 ring-2 ring-indigo-200"
                : "border-slate-200 hover:border-slate-400"
            }`}
          >
            <img src={source.src} alt={source.label} className="h-16 w-full rounded bg-slate-100 object-cover" />
            <span className="mt-1 block truncate px-1 text-xs font-medium">{source.label}</span>
          </button>
        ))}
      </div>
      {sources.length === 1 && (
        <p className="text-xs text-slate-500">Results of each tab appear here, so you can use them as input.</p>
      )}
    </div>
  );
}
