import { handle, toast } from "./api.js";
import { initializePresets } from "./presets.js";
import {
  refreshModels,
  loadSettings,
  saveSettings,
  refreshDownloads,
  downloadModel,
  initializeDownloadPresets,
  selectFolder,
  initializeModelSelection,
  initializeModelRuntime,
  transferStorage,
} from "./library.js";
import {
  selectImage,
  generate,
  restoreActiveJob,
  loadHistory,
} from "./generation.js";
import { initializeEditor, renderEditor } from "./preset-editor.js";
const $ = (id) => document.getElementById(id);

for (const button of document.querySelectorAll("[data-tab]")) {
  button.addEventListener(
    "click",
    handle(async () => {
      document
        .querySelectorAll("[data-tab]")
        .forEach((item) => item.classList.toggle("active", item === button));
      document
        .querySelectorAll(".tab")
        .forEach((item) =>
          item.classList.toggle("active", item.id === button.dataset.tab),
        );
      if (button.dataset.tab === "presets") renderEditor();
      if (button.dataset.tab === "history") await loadHistory();
      if (button.dataset.tab === "models") {
        await refreshModels();
        await refreshDownloads();
      }
    }),
  );
}
for (const button of document.querySelectorAll("[data-folder-target]"))
  button.addEventListener("click", handle(selectFolder));
$("storage-form").addEventListener("submit", handle(transferStorage));
$("settings-form").addEventListener("submit", handle(saveSettings));
$("download-form").addEventListener("submit", handle(downloadModel));
$("refresh-models").addEventListener("click", handle(refreshModels));
$("generate").addEventListener("click", handle(generate));
$("more-history").addEventListener(
  "click",
  handle(() => loadHistory(true)),
);
$("image").addEventListener(
  "change",
  handle((event) => selectImage(event.target.files[0])),
);
const dropzone = $("dropzone");
for (const event of ["dragenter", "dragover"])
  dropzone.addEventListener(event, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragging");
  });
for (const event of ["dragleave", "drop"])
  dropzone.addEventListener(event, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragging");
  });
dropzone.addEventListener(
  "drop",
  handle((event) => selectImage(event.dataTransfer.files[0])),
);

try {
  initializeDownloadPresets();
  initializeModelSelection();
  initializeModelRuntime();
  await initializePresets();
  initializeEditor();
  await loadSettings();
  await refreshModels();
  await refreshDownloads();
  await restoreActiveJob();
} catch (error) {
  toast(`Не удалось загрузить студию: ${error.message}`, true);
}
