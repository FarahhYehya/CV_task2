# Commands run while building the frontend (2026-11-02)

| # | Command (folder) | Why |
|---|---|---|
| 1 | `npm install` (`frontend/`) | install React, Vite, Tailwind (pinned versions in `package.json`) |
| 2 | `npx vite build` (`frontend/`), twice | check the code compiles (the `dist/` output was deleted afterwards) |
| 3 | `venv/Scripts/python.exe -m uvicorn api.main:app --port 8000` (`CV_task2/`) | start the backend |
| 4 | `npx vite --port 5173 --strictPort` (`frontend/`) | start the UI dev server |
| 5 | `curl -X POST http://localhost:5173/api/shapes -F image=@Test_images/... ` | Part 1 through the Vite proxy |
| 6 | `curl -X POST http://localhost:5173/api/snake -F image=@... -F points=[[...]]` | Part 2 through the Vite proxy |
| 7 | same `curl` calls with bad input (2 points, even window, `low_threshold=abc`) | error messages reach the UI (400 / 422) |

## Results of the checks

| Request | Result | Meaning |
|---|---|---|
| shapes, `01_basic_shapes.png`, no ellipses | 5 lines, 1 circle (cx 140, cy 330, r 67 px) | proxy + form fields work, same as README |
| shapes, `04_ellipses_only.png`, all detectors | 4 ellipses in ~5.5 s | the UI shows the "can take up to ~10 s" hint for this |
| snake, `03_circles_only.png`, square around the circle | perimeter 411.6 px, area 12221 px², 56 iterations, 128 points | same values as the README example |
| snake with 2 points | 400 `points must be at least 3 (x, y) pairs` | shown in red under the Run button |
| snake with `neighborhood=4` | 400 `neighborhood must be an odd integer >= 3` | shown in red under the Run button |
| shapes with `low_threshold=abc` | 422 `low_threshold: Input should be a valid number…` | shown in red under the Run button |
