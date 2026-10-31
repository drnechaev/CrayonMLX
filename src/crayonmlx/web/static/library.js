import { api, option, toast, handle } from "./api.js";
import { modelChanged } from "./presets.js";
let localModels = [];
const $ = (id) => document.getElementById(id);

export async function refreshModels() {
  const models = await api("/models");
  localModels = models;
  const previous = $("model").value;
  $("model").replaceChildren(
    option(
      "",
      models.length ? "Выберите модель" : "Добавьте модель в разделе «Модели»",
    ),
    ...models.map((item) => {
      const entry = option(
        item.id,
        item.recognized
          ? `${item.label} · ${item.name}`
          : `${item.name} — не распознана`,
      );
      entry.disabled = !item.recognized || !item.enabled;
      return entry;
    }),
  );
  if (
    models.some(
      (item) => item.id === previous && item.recognized && item.enabled,
    )
  )
    $("model").value = previous;
  else if (
    models.filter((item) => item.recognized && item.enabled).length === 1
  )
    $("model").value = models.find(
      (item) => item.recognized && item.enabled,
    ).id;
  modelChanged(models.find((item) => item.id === $("model").value));
  $("model-list").replaceChildren();
  if (!models.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Пока здесь нет моделей";
    $("model-list").append(empty);
  }
  for (const model of models) {
    const item = document.createElement("div");
    item.className = "model-item";
    const name = document.createElement("strong");
    name.textContent = model.recognized
      ? `${model.label} · ${model.name}`
      : model.name;
    const path = document.createElement("small");
    path.textContent = model.error
      ? `${model.path} — ${model.error}`
      : model.path;
    const status = document.createElement("p");
    status.className = "hint";
    const phase = model.runtime.phase;
    const labels = {
      unloaded: "Не загружена",
      starting: "Запуск",
      loading: "Загружается",
      ready: "Готова",
      preparing: "Подготовка",
      denoising: "Генерирует",
      decoding: "Сохранение изображения",
      error: "Ошибка",
    };
    const gb = (value) => (value / 1024 ** 3).toFixed(2);
    status.textContent = `${model.enabled ? labels[phase] || phase : "Выключена"}`;
    if (model.runtime.memory_active_bytes !== undefined)
      status.textContent += ` · Память MLX: ${gb(model.runtime.memory_active_bytes)} ГБ · кеш: ${gb(model.runtime.memory_cache_bytes)} ГБ · пик: ${gb(model.runtime.memory_peak_bytes)} ГБ`;
    if (
      model.runtime.unload_in_seconds !== null &&
      model.runtime.unload_in_seconds !== undefined
    )
      status.textContent += ` · выгрузка через ${Math.ceil(model.runtime.unload_in_seconds / 60)} мин`;
    if (model.runtime.error) status.textContent += ` · ${model.runtime.error}`;
    const buttons = document.createElement("div");
    buttons.className = "button-row";
    const enabled = document.createElement("button");
    enabled.className = "subtle";
    enabled.textContent = model.enabled ? "Выключить" : "Включить";
    enabled.addEventListener(
      "click",
      handle(async () => {
        await api("/models/availability", {
          method: "POST",
          body: JSON.stringify({ model: model.id, enabled: !model.enabled }),
        });
        await refreshModels();
      }),
    );
    const load = document.createElement("button");
    load.className = "subtle";
    load.textContent = "Загрузить в память";
    load.disabled =
      !model.enabled ||
      !model.recognized ||
      ["starting", "loading", "preparing", "denoising", "decoding"].includes(
        phase,
      );
    load.addEventListener(
      "click",
      handle(async () => {
        await api("/models/load", {
          method: "POST",
          body: JSON.stringify({
            model: model.id,
            quantize:
              $("quantize").value === "none"
                ? null
                : Number($("quantize").value),
          }),
        });
        await refreshModels();
      }),
    );
    const unload = document.createElement("button");
    unload.className = "subtle";
    unload.textContent = "Выгрузить";
    unload.disabled = phase !== "ready";
    unload.addEventListener(
      "click",
      handle(async () => {
        await api("/models/unload", { method: "POST" });
        await refreshModels();
      }),
    );
    buttons.append(enabled, load, unload);
    item.append(name, path, status, buttons);
    $("model-list").append(item);
  }
}

export async function loadSettings() {
  const settings = await api("/settings");
  $("model-idle-minutes").value = settings.model_idle_minutes ?? 15;
  $("keep-model-loaded").checked = settings.model_idle_minutes === null;
  $("model-idle-minutes").disabled = settings.model_idle_minutes === null;
  $("models-dir").value = settings.models_dir;
  $("output-dir").value = settings.output_dir;
  $("models-path").textContent = settings.models_dir;
  $("data-dir").value = settings.pending_data_dir || settings.data_dir;
  if (settings.pending_data_dir) {
    $("storage-status").textContent =
      `Данные перенесены в ${settings.pending_data_dir}. Перезапустите CrayonMLX.`;
    $("generate").disabled = true;
  }
  $("token-status").textContent = settings.has_hf_token
    ? "Токен сохранён. Пустое поле оставит его без изменений."
    : "Токен пока не задан. Публичные модели доступны без него.";
}

export async function saveSettings(event) {
  event.preventDefault();
  const settings = {
    models_dir: $("models-dir").value,
    output_dir: $("output-dir").value,
    model_idle_minutes: $("keep-model-loaded").checked
      ? null
      : Number($("model-idle-minutes").value),
  };
  if ($("remove-token").checked) settings.hf_token = "";
  else if ($("hf-token").value.trim())
    settings.hf_token = $("hf-token").value.trim();
  await api("/settings", { method: "PUT", body: JSON.stringify(settings) });
  $("hf-token").value = "";
  $("remove-token").checked = false;
  await loadSettings();
  await refreshModels();
  toast("Настройки сохранены");
}

let downloadPolling = false;
export async function refreshDownloads() {
  const downloads = await api("/downloads");
  $("download-list").replaceChildren();
  const labels = {
    queued: "В очереди",
    running: "Скачивается…",
    completed: "Скачано",
    failed: "Ошибка",
  };
  for (const item of downloads) {
    const row = document.createElement("div");
    row.className = "download-item";
    row.textContent = `${item.repo} · ${labels[item.status]}${item.error ? `\n${item.error}` : ""}`;
    $("download-list").append(row);
  }
  const active = downloads.some((item) =>
    ["queued", "running"].includes(item.status),
  );
  $("download-form").querySelector("button").disabled = active;
  if (active && !downloadPolling) {
    downloadPolling = true;
    setTimeout(async () => {
      downloadPolling = false;
      try {
        await refreshDownloads();
        await refreshModels();
      } catch (error) {
        toast(error.message, true);
      }
    }, 2500);
  }
}

export async function downloadModel(event) {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  button.disabled = true;
  try {
    await api("/downloads", {
      method: "POST",
      body: JSON.stringify({
        repo: $("hf-repo").value.trim(),
        revision: $("hf-revision").value.trim(),
      }),
    });
    toast("Загрузка поставлена в очередь");
    await refreshDownloads();
  } catch (error) {
    button.disabled = false;
    throw error;
  }
}

export function initializeDownloadPresets() {
  $("hf-preset").addEventListener("change", () => {
    if (!$("hf-preset").value) return;
    $("hf-repo").value = $("hf-preset").value;
    $("hf-revision").value = "main";
  });
  $("hf-repo").addEventListener("input", () => {
    $("hf-preset").value = $("hf-repo").value.trim();
  });
}

export async function selectFolder(event) {
  const button = event.currentTarget;
  const target = button.dataset.folderTarget;
  const field = $(
    {
      models_dir: "models-dir",
      output_dir: "output-dir",
      data_dir: "data-dir",
    }[target],
  );
  const buttons = document.querySelectorAll("[data-folder-target]");
  buttons.forEach((item) => {
    item.disabled = true;
  });
  button.textContent = "Выбор…";
  try {
    const result = await api("/folders/select", {
      method: "POST",
      body: JSON.stringify({ target, current_path: field.value }),
    });
    if (result.path !== null) {
      field.value = result.path;
      toast(
        target === "data_dir"
          ? "Папка выбрана. Нажмите «Перенести данные»."
          : "Папка выбрана. Нажмите «Сохранить настройки».",
      );
    }
  } finally {
    buttons.forEach((item) => {
      item.disabled = false;
    });
    button.textContent = "Выбрать…";
  }
}

export function initializeModelSelection() {
  $("model").addEventListener("change", () =>
    modelChanged(localModels.find((item) => item.id === $("model").value)),
  );
}

export function initializeModelRuntime() {
  $("keep-model-loaded").addEventListener("change", () => {
    $("model-idle-minutes").disabled = $("keep-model-loaded").checked;
  });
  setInterval(() => {
    if ($("models").classList.contains("active"))
      refreshModels().catch((error) => toast(error.message, true));
  }, 2500);
}

export async function transferStorage(event) {
  event.preventDefault();
  const result = await api("/storage/location", {
    method: "POST",
    body: JSON.stringify({ data_dir: $("data-dir").value }),
  });
  if (result.restart_required) {
    $("storage-status").textContent =
      `Данные перенесены в ${result.data_dir}. Остановите приложение (Ctrl+C) и запустите crayonmlx заново.`;
    $("generate").disabled = true;
    toast("Перенос завершён. Перезапустите CrayonMLX.");
  } else toast("Эта папка уже используется");
}
