import { useState } from "react";
import Segmented from "./Segmented.jsx";

export const VIEW_MODES = [
  { value: "slider", label: "Slider" },
  { value: "side", label: "Side by side" },
];

/*
 * Input vs result. mode "slider": one image, drag the line to reveal the difference.
 * mode "side": both images next to each other. Both images have the same size.
 */
export default function Compare({ before, after, beforeLabel, afterLabel, mode, onMode }) {
  const [split, setSplit] = useState(50); // % of the width that shows `before`

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Segmented options={VIEW_MODES} value={mode} onChange={onMode} />
        <a className="btn" href={after} download={`${afterLabel.toLowerCase().replaceAll(" ", "_")}.png`}>
          Download result
        </a>
      </div>

      {mode === "slider" ? (
        <div className="relative mx-auto w-fit max-w-full select-none overflow-hidden rounded-lg bg-slate-900">
          <img src={after} alt={afterLabel} className="block max-h-[70vh] max-w-full" draggable={false} />
          <img
            src={before}
            alt={beforeLabel}
            className="absolute inset-0 h-full w-full"
            style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}
            draggable={false}
          />
          <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-white shadow" style={{ left: `${split}%` }}>
            <span className="absolute top-1/2 left-1/2 flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white text-xs font-bold text-slate-700 shadow-md">
              ⇔
            </span>
          </div>
          <span className="pointer-events-none absolute top-2 left-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">
            {beforeLabel}
          </span>
          <span className="pointer-events-none absolute top-2 right-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">
            {afterLabel}
          </span>
          {/* Invisible range over the image: drag anywhere, or use the arrow keys */}
          <input
            type="range"
            min="0"
            max="100"
            step="0.1"
            value={split}
            onChange={(e) => setSplit(Number(e.target.value))}
            aria-label="Split between input and result"
            className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
          />
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {[[beforeLabel, before], [afterLabel, after]].map(([label, src]) => (
            <figure key={label} className="space-y-1">
              <figcaption className="label">{label}</figcaption>
              <img src={src} alt={label} className="w-full rounded-lg bg-slate-900" />
            </figure>
          ))}
        </div>
      )}
    </div>
  );
}
