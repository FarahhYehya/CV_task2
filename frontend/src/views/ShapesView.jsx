import { toSrc } from "../api.js";
import { SHAPES_DEFAULTS, SHAPES_GROUPS } from "../options.js";
import Compare from "../components/Compare.jsx";
import InputPicker from "../components/InputPicker.jsx";
import OptionsForm from "../components/OptionsForm.jsx";
import RunControls from "../components/RunControls.jsx";
import Segmented from "../components/Segmented.jsx";

// One table per shape type. Colours match the ones drawn by the backend (draw_shapes)
const SHAPE_TABLES = [
  { key: "lines", label: "Lines", color: "bg-green-100 text-green-800", columns: ["x1", "y1", "x2", "y2"] },
  { key: "circles", label: "Circles", color: "bg-red-100 text-red-800", columns: ["cx", "cy", "r"] },
  { key: "ellipses", label: "Ellipses", color: "bg-blue-100 text-blue-800", columns: ["cx", "cy", "width", "height", "angle"] },
];

const RESULT_IMAGES = [
  { value: "image", label: "Detected shapes" },
  { value: "edges", label: "Canny edges" },
];

/*
 * Part 1 tab: options -> POST /api/shapes -> compare input vs shapes (or edges) + table of shapes.
 * state / update: this tab's saved state in App, so it survives switching tabs.
 */
export default function ShapesView({ sources, input, inputChanged, state, update, onRun, viewMode, onViewMode }) {
  const { values, show, run, loading, error } = state;
  const setValue = (name, value) => update((prev) => ({ values: { ...prev.values, [name]: value } }));
  const stale = run && (inputChanged || JSON.stringify(run.sent) !== JSON.stringify(values));
  const showLabel = RESULT_IMAGES.find((r) => r.value === show).label;

  return (
    <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
      <aside className="card space-y-4 self-start">
        <InputPicker sources={sources} value={input.key} onChange={(inputKey) => update({ inputKey })} />

        {SHAPES_GROUPS.map((group) => {
          const enabled = group.toggle ? values[group.toggle] : group.enabledIf?.(values) ?? true;
          return (
            <fieldset key={group.title} className="space-y-2 border-t border-slate-200 pt-3">
              <label className="flex items-center justify-between">
                <span className="label">{group.title}</span>
                {group.toggle && (
                  <input
                    type="checkbox"
                    className="size-4 accent-indigo-600"
                    checked={values[group.toggle]}
                    onChange={(e) => setValue(group.toggle, e.target.checked)}
                  />
                )}
              </label>
              {group.hint && enabled && <p className="text-xs text-amber-700">{group.hint}</p>}
              <OptionsForm options={group.options} values={values} onChange={setValue} disabled={!enabled} />
            </fieldset>
          );
        })}

        <RunControls
          label="Detect"
          onRun={() => onRun("/api/shapes", values)}
          onReset={() => update({ values: SHAPES_DEFAULTS })}
          loading={loading}
          loadingHint={values.detect_ellipses ? "Ellipse detection can take up to ~10 s." : ""}
          stale={stale}
          error={error}
        />
      </aside>

      <section className="min-w-0 space-y-6">
        {run ? (
          <>
            <div className="card space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-semibold">Result</h2>
                <Segmented options={RESULT_IMAGES} value={show} onChange={(next) => update({ show: next })} />
              </div>
              <Compare
                before={run.inputSrc}
                after={toSrc(run.response[show])}
                beforeLabel="Input"
                afterLabel={showLabel}
                mode={viewMode}
                onMode={onViewMode}
              />
            </div>
            <ShapeTables response={run.response} />
          </>
        ) : (
          <div className="card space-y-3">
            <h2 className="font-semibold">Input</h2>
            <img src={input.src} alt="Input" className="mx-auto block max-h-[70vh] max-w-full rounded-lg bg-slate-900" />
            <p className="text-center text-sm text-slate-500">Choose the detectors and press Detect.</p>
          </div>
        )}
      </section>
    </div>
  );
}

function ShapeTables({ response }) {
  return (
    <div className="card space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="mr-2 font-semibold">Detected shapes</h2>
        {SHAPE_TABLES.map((t) => (
          <span key={t.key} className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${t.color}`}>
            {response[t.key].length} {t.label.toLowerCase()}
          </span>
        ))}
      </div>
      <p className="text-xs text-slate-500">
        All values in px (x right, y down). Ellipse width / height = full major / minor axis, angle in degrees.
      </p>
      <div className="grid gap-4 xl:grid-cols-3">
        {SHAPE_TABLES.filter((t) => response[t.key].length).map((t) => (
          <div key={t.key} className="max-h-72 overflow-auto rounded-lg border border-slate-200">
            <table className="w-full text-right text-sm tabular-nums">
              <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500">
                <tr>
                  <th className="px-2 py-1 text-left">{t.label}</th>
                  {t.columns.map((c) => <th key={c} className="px-2 py-1">{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {response[t.key].map((shape, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="px-2 py-1 text-left text-slate-400">{i + 1}</td>
                    {t.columns.map((c) => <td key={c} className="px-2 py-1">{shape[c]}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
