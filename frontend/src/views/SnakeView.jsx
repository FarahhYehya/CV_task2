import { useState } from "react";
import { toSrc } from "../api.js";
import { SNAKE_DEFAULTS, SNAKE_OPTIONS } from "../options.js";
import Compare from "../components/Compare.jsx";
import ImageOverlay, { Contour } from "../components/ImageOverlay.jsx";
import InputPicker from "../components/InputPicker.jsx";
import OptionsForm from "../components/OptionsForm.jsx";
import RunControls from "../components/RunControls.jsx";
import Segmented from "../components/Segmented.jsx";

const CONTOUR_MODES = [
  { value: "click", label: "Click points" },
  { value: "circle", label: "Circle" },
];

const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

/* `count` points on a circle, kept inside the image. */
function circlePoints({ cx, cy, r }, count, size) {
  return Array.from({ length: count }, (_, i) => {
    const t = (2 * Math.PI * i) / count;
    return [
      Math.round(clamp(cx + r * Math.cos(t), 0, size.w - 1) * 10) / 10,
      Math.round(clamp(cy + r * Math.sin(t), 0, size.h - 1) * 10) / 10,
    ];
  });
}

/*
 * Part 2 tab: draw the initial contour -> POST /api/snake -> compare, evolution, chain code, perimeter, area.
 * state / update: this tab's saved state in App, so the contour and result survive switching tabs.
 */
export default function SnakeView({ sources, input, inputChanged, state, update, onRun, viewMode, onViewMode }) {
  const { values, mode, points, circle, circleCount, run, loading, error } = state;
  const [size, setSize] = useState(null); // natural size of the input image (px)

  const contour = mode === "circle" ? (circle && size ? circlePoints(circle, circleCount, size) : []) : points;
  const fields = { ...values, points: JSON.stringify(contour) };
  const stale = run && (inputChanged || JSON.stringify(run.sent) !== JSON.stringify(fields));
  const setValue = (name, value) => update((prev) => ({ values: { ...prev.values, [name]: value } }));

  function addPoint([x, y]) {
    if (mode === "click") return update((prev) => ({ points: [...prev.points, [x, y]] }));
    update((prev) => ({ circle: { cx: x, cy: y, r: prev.circle?.r ?? Math.round(Math.min(size.w, size.h) / 4) } }));
  }
  const undo = () => update((prev) => ({ points: prev.points.slice(0, -1) }));

  return (
    <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
      <aside className="card space-y-4 self-start">
        <InputPicker sources={sources} value={input.key} onChange={(inputKey) => update({ inputKey })} />

        <fieldset className="space-y-2 border-t border-slate-200 pt-3">
          <p className="label">Initial contour</p>
          <Segmented options={CONTOUR_MODES} value={mode} onChange={(next) => update({ mode: next })} />
          {mode === "click" ? (
            <div className="flex items-center gap-2">
              <span className="flex-1 text-sm text-slate-600">{points.length} points</span>
              <button type="button" className="btn" onClick={undo} disabled={!points.length}>Undo</button>
              <button type="button" className="btn" onClick={() => update({ points: [] })} disabled={!points.length}>
                Clear
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
              <label className="col-span-2">
                <span className="block font-medium text-slate-700">Radius <small className="text-slate-400">(px)</small></span>
                <input
                  type="range"
                  className="w-full accent-indigo-600"
                  min="5"
                  max={size ? Math.round(Math.max(size.w, size.h) / 2) : 500}
                  value={circle?.r ?? 0}
                  disabled={!circle}
                  onChange={(e) => update((prev) => ({ circle: { ...prev.circle, r: Number(e.target.value) } }))}
                />
                <span className="text-xs text-slate-400">{circle ? `${circle.r} px` : "click the image to place the centre"}</span>
              </label>
              <label>
                <span className="block font-medium text-slate-700">No. of points</span>
                <input
                  type="number"
                  className="input"
                  min="3"
                  value={circleCount}
                  onChange={(e) => update({ circleCount: Math.max(3, Number(e.target.value) || 3) })}
                />
              </label>
            </div>
          )}
        </fieldset>

        <fieldset className="space-y-2 border-t border-slate-200 pt-3">
          <p className="label">Snake options</p>
          <OptionsForm options={SNAKE_OPTIONS} values={values} onChange={setValue} />
        </fieldset>

        <RunControls
          label="Run snake"
          onRun={() => {
            update({ frame: null }); // show the final contour of the new run
            onRun("/api/snake", fields);
          }}
          onReset={() => update({ values: SNAKE_DEFAULTS })}
          disabled={contour.length < 3}
          loading={loading}
          needs={contour.length < 3 ? "Draw an initial contour (at least 3 points) around the object." : ""}
          stale={stale}
          error={error}
        />
      </aside>

      <section className="min-w-0 space-y-6">
        <div className="card space-y-3">
          <div>
            <h2 className="font-semibold">1 · Initial contour</h2>
            <p className="text-sm text-slate-500">
              {mode === "click"
                ? "Click around the object to add points (right click = undo). The snake shrinks onto the edges."
                : "Click to place the centre, then set the radius. Make the circle enclose the object."}
            </p>
          </div>
          <ImageOverlay src={input.src} onSize={setSize} onPoint={addPoint} onUndo={mode === "click" ? undo : undefined}>
            {(s) => <Contour points={contour} size={s} vertices fill="rgba(99,102,241,0.12)" />}
          </ImageOverlay>
        </div>

        {run && <SnakeResult run={run} state={state} update={update} viewMode={viewMode} onViewMode={onViewMode} />}
      </section>
    </div>
  );
}

function SnakeResult({ run, state, update, viewMode, onViewMode }) {
  const { response } = run;
  const last = response.history.length - 1;
  const frame = Math.min(state.frame ?? last, last);
  const metrics = [
    ["Perimeter", response.perimeter.toFixed(1), "px"],
    ["Area", response.area.toLocaleString(undefined, { maximumFractionDigits: 1 }), "px²"],
    ["Contour points", response.points.length, "points"],
    ["Iterations", last, "iterations"],
  ];

  return (
    <>
      <div className="card space-y-3">
        <h2 className="font-semibold">2 · Result</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {metrics.map(([label, value, unit]) => (
            <div key={label} className="rounded-lg bg-slate-50 p-3">
              <p className="label">{label}</p>
              <p className="text-xl font-semibold tabular-nums">
                {value} <span className="text-sm font-normal text-slate-500">{unit}</span>
              </p>
            </div>
          ))}
        </div>
        <Compare
          before={run.inputSrc}
          after={toSrc(response.image)}
          beforeLabel="Input"
          afterLabel="Final contour"
          mode={viewMode}
          onMode={onViewMode}
        />
      </div>

      <div className="card space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">3 · Evolution</h2>
          <span className="text-sm text-slate-500 tabular-nums">Iteration {frame} / {last}</span>
        </div>
        <ImageOverlay src={run.inputSrc}>
          {(s) => (
            <>
              <Contour points={response.history[0]} size={s} color="#94a3b8" dashed />
              <Contour points={response.history[frame]} size={s} color="#22c55e" />
            </>
          )}
        </ImageOverlay>
        <input
          type="range"
          className="w-full accent-indigo-600"
          min="0"
          max={last}
          value={frame}
          onChange={(e) => update({ frame: Number(e.target.value) })}
          aria-label="Iteration"
        />
        <p className="text-xs text-slate-500">Dashed grey = initial contour (resampled), green = contour at this iteration.</p>
      </div>

      <ChainCode start={response.chain_start} code={response.chain_code} />
    </>
  );
}

function ChainCode({ start, code }) {
  const [copied, setCopied] = useState(false);
  const text = code.join("");

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="card space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">4 · Chain code</h2>
        <button type="button" className="btn" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
      </div>
      <p className="text-sm text-slate-600">
        Start ({start[0]}, {start[1]}) px · {code.length} codes · Freeman 8 directions: 0 = right, 2 = up, 4 = left, 6 = down
      </p>
      <p className="max-h-40 overflow-auto rounded-lg bg-slate-50 p-3 font-mono text-sm break-all">{text}</p>
    </div>
  );
}
