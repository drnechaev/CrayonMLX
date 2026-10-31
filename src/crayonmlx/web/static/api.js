/** Shared JSON transport; no credentials are persisted in browser storage. */
export async function api(path, options = {}) {
  const headers = { ...options.headers };
  if (options.body && !(options.body instanceof FormData))
    headers["Content-Type"] = "application/json";
  const response = await fetch(`/api${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `Ошибка ${response.status}`;
    try {
      const body = await response.json();
      message =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      /* Preserve HTTP status when server returns a non-JSON error. */
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

let toastTimer;
export function toast(message, error = false) {
  const element = document.getElementById("toast");
  element.textContent = message;
  element.classList.toggle("error", error);
  element.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(
    () => {
      element.hidden = true;
    },
    error ? 10000 : 3500,
  );
}

export function handle(action) {
  return async (event) => {
    try {
      await action(event);
    } catch (error) {
      toast(error.message, true);
    }
  };
}

export function option(value, label) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}
