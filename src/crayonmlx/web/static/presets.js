/** Studio selectors. Persistent editing is owned by the separate library screen. */
import { api, option, toast } from "./api.js";
import {
  $,
  blockNames,
  defaults,
  readParameters,
  setParameters,
  templateSelect,
} from "./forms.js";
import {
  preservationFields,
  readPreservation,
  preservationPrompt,
  releasePreservation,
} from "./preservation.js";
export const library = { engines: [], presets: [], templates: [], configs: [] };
let studioName = "Новая история";

export function updatePrompt() {
  $("composed-prompt").textContent = Object.keys(blockNames)
    .map((key) => $(`block-${key}`).value.trim())
    .concat(preservationPrompt(readPreservation()))
    .filter(Boolean)
    .join("\n\n");
}
function buildBlocks() {
  const current = Object.fromEntries(
    Object.keys(blockNames).map((key) => [key, $(`block-${key}`)?.value || ""]),
  );
  const preservation = readPreservation();
  $("blocks").replaceChildren();
  for (const [key, label] of Object.entries(blockNames)) {
    const details = document.createElement("details");
    details.className = "prompt-block";
    details.open = true;
    const summary = document.createElement("summary");
    summary.textContent = label;
    const text = document.createElement("textarea");
    text.id = `block-${key}`;
    text.value = current[key];
    text.maxLength = 12000;
    text.setAttribute("aria-label", label);
    const picker = templateSelect(
      `template-${key}`,
      key,
      library.templates,
      current[key],
      (value) => {
        text.value = value;
        const message = releasePreservation("", key, value);
        if (message) toast(message);
        $("preset").value = "";
        updatePrompt();
      },
    );
    picker.setAttribute("aria-label", `Заготовка: ${label}`);
    text.addEventListener("input", () => {
      picker.value = "";
      const message = releasePreservation("", key, text.value);
      if (message) toast(message);
      $("preset").value = "";
      updatePrompt();
    });
    details.append(summary, picker, text);
    if (key === "constraints")
      details.append(
        preservationFields("", preservation, (changed, checked) => {
          const category = { background: "background", layout: "composition" }[
            changed
          ];
          if (checked && category && $(`block-${category}`).value.trim()) {
            $(`preserve-${changed}`).checked = false;
            toast(
              "Сначала выберите «Не менять» в соответствующем блоке или очистите его текст.",
            );
          }
          $("preset").value = "";
          updatePrompt();
        }),
      );
    $("blocks").append(details);
  }
}
let selectedModel = null;
export function modelChanged(model) {
  selectedModel = model?.recognized ? model : null;
  const engine = library.engines.find(
    (item) => item.id === selectedModel?.engine,
  );
  $("image_strength").disabled = !engine?.supports_strength;
  $("guidance").disabled =
    !selectedModel || selectedModel.base_model === "schnell";
  $("strength-hint").textContent =
    selectedModel?.engine === "mflux-flux"
      ? "Больше значение — сильнее влияние исходного рисунка."
      : "Для выбранной модели image strength не применяется.";
  $("model-hint").textContent =
    model?.error ||
    (selectedModel
      ? `${selectedModel.label}. Способ запуска определяется автоматически.`
      : "Добавьте поддерживаемую модель в разделе «Модели».");
  if (selectedModel && !engine?.available)
    $("model-hint").textContent =
      "Для запуска нужен Mac Apple Silicon и установленный MFLUX.";
}
export function readPreset() {
  return {
    name: studioName,
    engine: selectedModel?.engine || "mflux-qwen-edit",
    base_model: selectedModel?.base_model || "qwen-image-edit-2511",
    blocks: {
      ...Object.fromEntries(
        Object.keys(blockNames).map((key) => [key, $(`block-${key}`).value]),
      ),
      preservation: readPreservation(),
    },
    parameters: readParameters(),
  };
}
export function applyConfig(config) {
  setParameters(config.parameters);
}
export function applyPreset(preset) {
  studioName = preset.name;
  applyConfig(preset);
  for (const key of Object.keys(blockNames)) {
    $(`block-${key}`).value = preset.blocks[key] || "";
    $(`template-${key}`).value =
      library.templates.find(
        (item) => item.category === key && item.text === preset.blocks[key],
      )?.id || "";
  }
  for (const key of Object.keys(readPreservation()))
    $(`preserve-${key}`).checked = Boolean(preset.blocks.preservation?.[key]);
  $("generation-config").value =
    library.configs.find(
      (item) =>
        JSON.stringify(item.parameters) === JSON.stringify(preset.parameters),
    )?.id || "";
  updatePrompt();
}
export async function refreshLibrary() {
  const [presets, templates, configs] = await Promise.all([
    api("/presets"),
    api("/prompt-templates"),
    api("/generation-configs"),
  ]);
  Object.assign(library, { presets, templates, configs });
  for (const [id, items, placeholder] of [
    ["preset", presets, "Своя комбинация"],
    ["generation-config", configs, "Свои параметры"],
  ]) {
    const value = $(id).value;
    $(id).replaceChildren(
      option("", placeholder),
      ...items.map((item) => option(item.id, item.name)),
    );
    $(id).value = items.some((item) => item.id === value) ? value : "";
  }
  buildBlocks();
  updatePrompt();
}
export async function initializePresets() {
  library.engines = await api("/engines");
  await refreshLibrary();
  setParameters(defaults);
  // Start with source-preserving choices, not an arbitrary full preset.
  const rules = library.templates.find(
    (item) => item.name === "Изменения · Только выбранные изменения",
  );
  if (rules) {
    $("block-constraints").value = rules.text;
    $("template-constraints").value = rules.id;
  }
  for (const key of Object.keys(readPreservation()))
    $(`preserve-${key}`).checked = true;
  updatePrompt();
  $("preset").addEventListener("change", () => {
    const preset = library.presets.find(
      (item) => item.id === $("preset").value,
    );
    if (preset) applyPreset(preset);
    else studioName = "Новая история";
  });
  $("generation-config").addEventListener("change", () => {
    const config = library.configs.find(
      (item) => item.id === $("generation-config").value,
    );
    if (config) applyConfig(config);
  });
  for (const id of [
    "steps",
    "guidance",
    "width",
    "height",
    "image_strength",
    "seed",
    "quantize",
  ])
    $(id).addEventListener("input", () => {
      $("generation-config").value = "";
    });
  $("toggle-prompt").addEventListener("click", () => {
    $("composed-prompt").hidden = !$("composed-prompt").hidden;
    $("toggle-prompt").textContent = $("composed-prompt").hidden
      ? "Показать итоговый промпт"
      : "Скрыть итоговый промпт";
  });
}
