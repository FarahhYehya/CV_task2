import { useEffect, useMemo, useRef, useState } from "react";
import { postImage, toSrc } from "./api.js";
import { SHAPES_DEFAULTS, SNAKE_DEFAULTS } from "./options.js";
import Upload from "./components/Upload.jsx";
import ShapesView from "./views/ShapesView.jsx";
import SnakeView from "./views/SnakeView.jsx";

const TABS = [
  { key: "shapes", label: "Edges & shapes", hint: "Canny · lines · circles · ellipses", View: ShapesView },
  { key: "snake", label: "Active contour", hint: "Greedy snake · chain code · perimeter · area", View: SnakeView },
];

// run = last successful result of the tab: {inputKey, inputSrc, sent (fields sent), response}
const EMPTY_RUN = { inputKey: "original", run: null, loading: false, error: "" };
const INITIAL_STORE = {
  shapes: { ...EMPTY_RUN, values: SHAPES_DEFAULTS, show: "image" },
  snake: { ...EMPTY_RUN, values: SNAKE_DEFAULTS, mode: "click", points: [], circle: null, circleCount: 40, frame: null },
};

/* File -> object URL for <img>, revoked when the file changes. */
function useObjectUrl(file) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    if (!file) return setUrl(null);
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  return url;
}

export default function App() {
  const [file, setFile] = useState(null); // the upload, shared by both tabs
  const url = useObjectUrl(file);
  const [tab, setTab] = useState(TABS[0].key);
  const [store, setStore] = useState(INITIAL_STORE); // {tab key: that tab's state}, survives switching tabs
  const [viewMode, setViewMode] = useState("slider"); // compare view, same in both tabs
  const uploadId = useRef(0); // changes on every upload, to drop results of requests sent for an older image

  // patch = object or (prev tab state) => object, merged into that tab's state
  const updateTab = (key) => (patch) =>
    setStore((prev) => ({ ...prev, [key]: { ...prev[key], ...(typeof patch === "function" ? patch(prev[key]) : patch) } }));

  // Every image a tab can take as input: the upload + the stored result of each tab (owner = tab that made it)
  const { shapes, snake } = store;
  const sources = useMemo(
    () =>
      [
        url && { key: "original", label: "Uploaded image", src: url },
        shapes.run && { key: "shapes", owner: "shapes", label: "Shapes result", src: toSrc(shapes.run.response.image) },
        shapes.run && { key: "edges", owner: "shapes", label: "Canny edges", src: toSrc(shapes.run.response.edges) },
        snake.run && { key: "snake", owner: "snake", label: "Snake result", src: toSrc(snake.run.response.image) },
      ].filter(Boolean),
    [url, shapes.run, snake.run]
  );

  // New image -> every result and the drawn contour are stale (options are kept)
  function upload(newFile) {
    uploadId.current += 1;
    setFile(newFile);
    setStore((prev) => ({
      shapes: { ...prev.shapes, ...EMPTY_RUN },
      snake: { ...prev.snake, ...EMPTY_RUN, points: [], circle: null, frame: null },
    }));
  }

  // Results are saved in the tab that sent the request, even if the user switched tabs meanwhile
  async function runTab(key, endpoint, fields, input) {
    const id = uploadId.current;
    const update = updateTab(key);
    update({ loading: true, error: "" });
    const { response, error } = await postImage(endpoint, input.src, fields);
    if (id !== uploadId.current) return; // a new image was uploaded while waiting
    const run = response && { inputKey: input.key, inputSrc: input.src, sent: fields, response };
    update((prev) => ({ loading: false, error, run: run || prev.run }));
  }

  const { View } = TABS.find((t) => t.key === tab);
  const state = store[tab];
  const input = sources.find((s) => s.key === state.inputKey) ?? sources[0];
  // A tab fed with its own result gets a new input after every run: that alone is not a change
  const inputChanged = Boolean(
    state.run && (state.run.inputKey !== input.key || (state.run.inputSrc !== input.src && input.owner !== tab))
  );

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-4 px-4 pt-4">
          <div className="pb-3">
            <h1 className="text-lg font-bold">
              <span className="text-indigo-600">CV Task 2</span> · Shape detection & active contour
            </h1>
            <p className="text-xs text-slate-500">All processing runs on the backend, written from scratch with NumPy.</p>
          </div>
          <nav className="flex gap-1">
            {TABS.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={`rounded-t-lg border-b-2 px-4 py-2 text-left transition ${
                  t.key === tab ? "border-indigo-600 bg-indigo-50" : "border-transparent hover:bg-slate-50"
                }`}
              >
                <span className="flex items-center gap-2 text-sm font-semibold">
                  {t.label}
                  {store[t.key].loading ? (
                    <span className="size-3 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" title="Running" />
                  ) : (
                    store[t.key].run && <span className="size-2 rounded-full bg-green-500" title="Has a result" />
                  )}
                </span>
                <span className="block text-xs text-slate-500">{t.hint}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
        <Upload file={file} url={url} onFile={upload} />
        {input && (
          <View
            sources={sources}
            input={input}
            inputChanged={inputChanged}
            state={state}
            update={updateTab(tab)}
            onRun={(endpoint, fields) => runTab(tab, endpoint, fields, input)}
            viewMode={viewMode}
            onViewMode={setViewMode}
          />
        )}
      </main>
    </div>
  );
}
