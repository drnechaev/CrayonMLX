import { api, toast } from "./api.js";
import { readPreset } from "./presets.js";
const $ = (id) => document.getElementById(id);
const labels = {
  queued: "В очереди",
  running: "Создаём новую историю…",
  completed: "Готово",
  failed: "Ошибка",
};
let sourceFile,
  previewUrl,
  activeJob,
  historyOffset = 0;

export function selectImage(file) {
  if (!file) return;
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type))
    throw new Error("Выберите PNG, JPEG или WebP");
  if (file.size > 20 * 1024 * 1024)
    throw new Error("Максимальный размер — 20 МБ");
  sourceFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  $("source-preview").src = previewUrl;
  $("source-preview").hidden = false;
  $("upload-hint").hidden = true;
}

function showJob(job) {
  const progress = job.progress;
  $("render-progress").hidden = !progress || job.status !== "running";
  if (progress) {
    const phases = {
      starting: "Запуск модели",
      loading: "Загрузка модели",
      preparing: "Подготовка изображения",
      decoding: "Декодирование и сохранение",
      ready: "Завершение",
    };
    const bar = $("step-progress");
    if (progress.phase === "denoising" && progress.total_steps > 0) {
      bar.max = progress.total_steps;
      bar.value = progress.step;
    } else bar.removeAttribute("value");
    $("step-label").textContent =
      `${progress.phase === "denoising" ? `Шаг ${progress.step} из ${progress.total_steps}` : phases[progress.phase] || "Подготовка"} · ${Math.round(progress.elapsed_seconds || 0)} сек`;
  }

  $("render-status").textContent =
    `${labels[job.status]} · ${job.request.preset.name} · seed ${job.request.preset.parameters.seed}${job.error ? `\n${job.error}` : ""}`;
  $("render-status").classList.toggle("error", job.status === "failed");
  const completed = job.status === "completed";
  $("result-preview").hidden = !completed;
  $("result-hint").hidden = completed;
  $("download-result").hidden = !completed;
  if (completed) {
    const url = `/api/generations/${job.id}/output`;
    $("result-preview").src = url;
    $("download-result").href = url;
    $("download-result").download = `crayonmlx-${job.id}.png`;
  }
  if (["queued", "running"].includes(job.status)) {
    $("result-hint").querySelector("h3").textContent = labels[job.status];
    $("result-hint").querySelector("p").textContent =
      "Можно продолжать редактировать будущие истории";
  }
}

async function pollJob(id) {
  try {
    const job = await api(`/generations/${id}`);
    if (activeJob !== id) return;
    showJob(job);
    if (["queued", "running"].includes(job.status))
      setTimeout(() => pollJob(id), 2000);
    else {
      activeJob = null;
      $("generate").disabled = false;
      await loadHistory();
    }
  } catch (error) {
    $("render-status").textContent =
      `Не удалось обновить статус: ${error.message}. Повторная проверка через 5 секунд.`;
    setTimeout(() => pollJob(id), 5000);
  }
}

export async function generate() {
  if (!sourceFile) throw new Error("Сначала загрузите рисунок");
  if (!$("model").value) throw new Error("Выберите локальную модель");
  const form = new FormData();
  form.append("image", sourceFile);
  form.append(
    "config",
    JSON.stringify({ preset: readPreset(), model: $("model").value }),
  );
  $("generate").disabled = true;
  try {
    const job = await api("/generations", { method: "POST", body: form });
    activeJob = job.id;
    showJob(job);
    pollJob(job.id);
  } catch (error) {
    $("generate").disabled = false;
    throw error;
  }
}

export async function restoreActiveJob() {
  const jobs = await api("/generations?limit=100");
  const job = jobs.find((item) => ["queued", "running"].includes(item.status));
  if (job) {
    activeJob = job.id;
    $("generate").disabled = true;
    showJob(job);
    pollJob(job.id);
  }
}

export async function loadHistory(append = false) {
  if (!append) {
    historyOffset = 0;
    $("history-list").replaceChildren();
  }
  const jobs = await api(`/generations?limit=24&offset=${historyOffset}`);
  if (!jobs.length && !append) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Первая история начинается с вашего рисунка.";
    $("history-list").append(empty);
  }
  for (const job of jobs) {
    const card = document.createElement("article");
    card.className = "history-card";
    const pictures = document.createElement("div");
    pictures.className = "history-pictures";
    for (const kind of job.status === "completed"
      ? ["source", "output"]
      : ["source"]) {
      const image = document.createElement("img");
      image.src = `/api/generations/${job.id}/${kind}`;
      image.alt = kind === "source" ? "Исходный рисунок" : "Результат";
      image.loading = "lazy";
      pictures.append(image);
    }
    const title = document.createElement("h3");
    title.textContent = job.request.preset.name;
    const info = document.createElement("p");
    info.textContent = `${new Date(job.created_at).toLocaleString("ru-RU")} · ${labels[job.status]}\n${job.request.preset.base_model} · ${job.request.preset.parameters.width} × ${job.request.preset.parameters.height} · seed ${job.request.preset.parameters.seed}${job.error ? `\n${job.error}` : ""}`;
    const buttons = document.createElement("div");
    buttons.className = "button-row";
    if (job.status === "completed") {
      const download = document.createElement("a");
      download.className = "subtle";
      download.textContent = "Скачать";
      download.href = `/api/generations/${job.id}/output`;
      download.download = `crayonmlx-${job.id}.png`;
      buttons.append(download);
    }
    const details = document.createElement("details"),
      summary = document.createElement("summary"),
      metadata = document.createElement("pre");
    summary.textContent = "Промпт и параметры";
    metadata.textContent = JSON.stringify(
      { ...job.request, execution: job.execution },
      null,
      2,
    );
    details.append(summary, metadata);
    card.append(pictures, title, info, buttons, details);
    $("history-list").append(card);
  }
  historyOffset += jobs.length;
  $("more-history").hidden = jobs.length < 24;
}
