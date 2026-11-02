/*
 * The only place that talks to the backend.
 * Input : endpoint, image src (object URL of the upload or data URL of a result), option values.
 * Output: {response, error}. Never throws, so callers only set state.
 *         Images in the response are base64 PNG strings.
 */

export const toSrc = (base64Png) => `data:image/png;base64,${base64Png}`;

function errorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail; // 400 from a service ValueError
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.at(-1)}: ${d.msg}`).join("; "); // 422 from FastAPI
  return `Request failed (HTTP ${status})`;
}

async function post(endpoint, imageSrc, values) {
  const form = new FormData();
  // fetch() reads object URLs and data URLs alike, so the upload and every result take the same path
  form.append("image", await (await fetch(imageSrc)).blob(), "image.png");
  for (const [name, value] of Object.entries(values)) {
    if (value !== "" && value !== null) form.append(name, value);
  }

  let response;
  try {
    response = await fetch(endpoint, { method: "POST", body: form });
  } catch {
    throw new Error("Cannot reach the backend. Is uvicorn running on port 8000?");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(body, response.status));
  return body;
}

export async function postImage(endpoint, imageSrc, values) {
  try {
    return { response: await post(endpoint, imageSrc, values), error: "" };
  } catch (e) {
    return { response: null, error: e.message };
  }
}
