/*
 * Options of every endpoint (api/routers/). The forms are built from these lists only.
 * name = form field name in the API, default = API default, unit shown to the user.
 * type "int" | "float". default "" = optional field, not sent (the backend picks the value).
 */

const SIGMA = { name: "sigma", label: "Sigma", type: "float", default: 1.4, min: 0, step: 0.1, unit: "px, 0 = no blur" };

// POST /api/shapes. toggle = boolean field that switches the group's detector on / off
export const SHAPES_GROUPS = [
  {
    title: "Canny",
    options: [
      { name: "low_threshold", label: "Low threshold", type: "float", default: 50, min: 0, unit: "gradient" },
      { name: "high_threshold", label: "High threshold", type: "float", default: 150, min: 0, unit: "gradient" },
      SIGMA,
    ],
  },
  {
    title: "Lines", toggle: "detect_lines",
    options: [
      { name: "threshold", label: "Min votes", type: "int", default: 60, min: 1, unit: "edge pixels" },
      { name: "min_line_length", label: "Min length", type: "int", default: 40, min: 1, unit: "px" },
      { name: "max_line_gap", label: "Max gap", type: "int", default: 10, min: 0, unit: "px" },
    ],
  },
  {
    title: "Circles", toggle: "detect_circles",
    options: [
      { name: "min_radius", label: "Min radius", type: "int", default: 10, min: 1, unit: "px" },
      { name: "max_radius", label: "Max radius", type: "int", default: "", min: 1, unit: "px, empty = auto" },
      { name: "min_votes", label: "Min votes", type: "int", default: 30, min: 1, unit: "votes" },
    ],
  },
  {
    title: "Ellipses", toggle: "detect_ellipses", hint: "Slow: about 3-10 s on a 640×480 image.",
    options: [
      { name: "min_axis_length", label: "Min minor axis", type: "int", default: 10, min: 1, unit: "px" },
      { name: "max_axis_length", label: "Max major axis", type: "int", default: "", min: 1, unit: "px, empty = auto" },
      { name: "min_center_votes", label: "Min centre votes", type: "int", default: 25, min: 1, unit: "votes" },
    ],
  },
  {
    title: "Circles + ellipses", enabledIf: (values) => values.detect_circles || values.detect_ellipses,
    options: [
      { name: "min_edge_support", label: "Min edge support", type: "float", default: 0.8, min: 0, max: 1, step: 0.05, unit: "fraction, 0-1" },
    ],
  },
];

// POST /api/snake (the `points` field comes from the contour editor)
export const SNAKE_OPTIONS = [
  { name: "alpha", label: "Alpha", type: "float", default: 1.0, min: 0, step: 0.1, unit: "continuity" },
  { name: "beta", label: "Beta", type: "float", default: 1.0, min: 0, step: 0.1, unit: "curvature" },
  { name: "gamma", label: "Gamma", type: "float", default: 1.2, min: 0, step: 0.1, unit: "edge pull" },
  SIGMA,
  { name: "neighborhood", label: "Window", type: "int", default: 3, min: 3, step: 2, unit: "odd, px" },
  { name: "spacing", label: "Spacing", type: "float", default: 5.0, min: 0.5, step: 0.5, unit: "px between points" },
  { name: "max_iterations", label: "Max iterations", type: "int", default: 500, min: 1, unit: "iterations" },
  { name: "min_moved", label: "Min moved", type: "int", default: 2, min: 0, unit: "points / iteration" },
  { name: "curv_thresh", label: "Corner threshold", type: "float", default: 0.25, min: 0, step: 0.05, unit: "curvature" },
];

const defaultsOf = (options) => Object.fromEntries(options.map((option) => [option.name, option.default]));

export const SHAPES_DEFAULTS = {
  ...Object.fromEntries(SHAPES_GROUPS.filter((group) => group.toggle).map((group) => [group.toggle, true])),
  ...defaultsOf(SHAPES_GROUPS.flatMap((group) => group.options)),
};
export const SNAKE_DEFAULTS = defaultsOf(SNAKE_OPTIONS);
