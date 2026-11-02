import { useState } from "react";

/*
 * Image with an SVG on top that uses IMAGE pixel coordinates (viewBox = natural size),
 * so contour points are drawn and clicked in the same units the backend uses.
 * children(size) draws inside the SVG. onPoint([x, y]) = left click, onUndo() = right click.
 */
export default function ImageOverlay({ src, onSize, onPoint, onUndo, children }) {
  const [size, setSize] = useState(null);

  function toImage(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const round = (v) => Math.round(v * 10) / 10;
    return [round(((e.clientX - rect.left) * size.w) / rect.width), round(((e.clientY - rect.top) * size.h) / rect.height)];
  }

  return (
    <div className="relative mx-auto w-fit max-w-full select-none">
      <img
        src={src}
        alt="Input"
        draggable={false}
        className="block max-h-[70vh] max-w-full rounded-lg bg-slate-900"
        onLoad={(e) => {
          const next = { w: e.target.naturalWidth, h: e.target.naturalHeight };
          setSize(next);
          onSize?.(next);
        }}
      />
      {size && (
        <svg
          viewBox={`0 0 ${size.w} ${size.h}`}
          className={`absolute inset-0 h-full w-full ${onPoint ? "cursor-crosshair" : ""}`}
          onClick={onPoint && ((e) => onPoint(toImage(e)))}
          onContextMenu={onUndo && ((e) => (e.preventDefault(), onUndo()))}
        >
          {children(size)}
        </svg>
      )}
    </div>
  );
}

/* Closed contour (polyline while it has < 3 points). Stroke width stays the same on screen at any zoom. */
export function Contour({ points, size, color = "#6366f1", dashed = false, vertices = false, fill = "none" }) {
  if (!points.length) return null;
  const dot = Math.max(size.w, size.h) / 200; // vertex radius, ~0.5 % of the image
  const Shape = points.length >= 3 ? "polygon" : "polyline";
  return (
    <g>
      <Shape
        points={points.map((p) => p.join(",")).join(" ")}
        fill={fill}
        stroke={color}
        strokeWidth="2"
        strokeDasharray={dashed ? "6 4" : undefined}
        vectorEffect="non-scaling-stroke"
      />
      {vertices && points.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={dot} fill={color} stroke="white" strokeWidth="1" vectorEffect="non-scaling-stroke" />)}
    </g>
  );
}
