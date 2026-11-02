import { useRef, useState } from "react";

/*
 * Image upload by click or drag & drop.
 * No file yet -> big drop zone. File chosen -> compact bar with a thumbnail and "Replace".
 */
export default function Upload({ file, url, onFile }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function pick(files) {
    const image = [...files].find((f) => f.type.startsWith("image/"));
    if (image) onFile(image);
  }

  const dropProps = {
    onDragOver: (e) => {
      e.preventDefault();
      setDragging(true);
    },
    onDragLeave: () => setDragging(false),
    onDrop: (e) => {
      e.preventDefault();
      setDragging(false);
      pick(e.dataTransfer.files);
    },
  };
  const hiddenInput = (
    <input
      ref={inputRef}
      type="file"
      accept="image/*"
      className="hidden"
      onChange={(e) => {
        pick(e.target.files);
        e.target.value = ""; // allows choosing the same file again
      }}
    />
  );

  if (!file) {
    return (
      <button
        type="button"
        {...dropProps}
        onClick={() => inputRef.current.click()}
        className={`flex w-full flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-20 text-center transition ${
          dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-white hover:border-indigo-400"
        }`}
      >
        {hiddenInput}
        <span className="text-lg font-semibold text-slate-700">Drop an image here or click to choose</span>
        <span className="text-sm text-slate-500">
          Grayscale or colour. Upload it once, then use it in both tabs.
        </span>
      </button>
    );
  }

  return (
    <div
      {...dropProps}
      className={`card flex items-center gap-4 py-3 transition ${dragging ? "border-indigo-500 bg-indigo-50" : ""}`}
    >
      {hiddenInput}
      <img src={url} alt="Uploaded" className="h-12 w-12 rounded-md bg-slate-100 object-cover" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{file.name}</p>
        <p className="text-xs text-slate-500">Used by both tabs · drop a new image here to replace it</p>
      </div>
      <button type="button" className="btn" onClick={() => inputRef.current.click()}>
        Replace image
      </button>
    </div>
  );
}
