/** Explicit preservation choices, included as values in every saved full preset. */
import { field } from "./forms.js";
export const preservationNames = {
  identity: "Внешность и узнаваемость",
  clothing: "Одежда и аксессуары",
  poses: "Позы, выражения и жесты",
  colors: "Исходные цвета",
  objects: "Состав героев и предметов",
  layout: "Расположение и масштаб",
  lettering: "Надписи и украшения",
  background: "Исходный фон",
};
// Kept in sync with schemas.PRESERVATION_RULES; the server composes the saved prompt.
const rules = {
  identity:
    "Preserve the identity, distinctive features, and recognizable silhouettes of the original subjects.",
  clothing:
    "Preserve the original clothing, accessories, and their distinctive details.",
  poses: "Preserve the original poses, expressions, and gestures.",
  colors:
    "Preserve the source colors and color relationships; shading may adapt to the selected light.",
  objects:
    "Preserve the original foreground characters, animals, buildings that are main subjects, and other main objects; do not add or remove main subjects.",
  layout:
    "Preserve the relative placement, scale, and arrangement of the original subjects.",
  lettering:
    "Preserve intentional lettering, symbols, and decorations already present in the drawing.",
  background: "Preserve the original background and location.",
};
export function preservationFields(prefix, values, onChange = () => {}) {
  const container = document.createElement("fieldset");
  container.className = "preservation-fields";
  const legend = document.createElement("legend");
  legend.textContent = "Что обязательно сохранить";
  container.append(legend);
  for (const [key, label] of Object.entries(preservationNames)) {
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = `${prefix}preserve-${key}`;
    checkbox.checked = Boolean(values[key]);
    checkbox.addEventListener("change", () => onChange(key, checkbox.checked));
    const wrapper = field(label, checkbox);
    wrapper.className = "preservation-choice";
    container.append(wrapper);
  }
  const hint = document.createElement("p");
  hint.className = "hint";
  hint.textContent =
    "Отмеченное закрепляем явно. Без галочки детали могут адаптироваться к выбранным изменениям. Новый фон отключает сохранение фона; новая композиция — расположения.";
  container.append(hint);
  return container;
}
export function readPreservation(prefix = "") {
  return Object.fromEntries(
    Object.keys(preservationNames).map((key) => [
      key,
      Boolean(document.getElementById(`${prefix}preserve-${key}`)?.checked),
    ]),
  );
}
export function preservationPrompt(values) {
  return Object.keys(preservationNames)
    .filter((key) => values[key])
    .map((key) => rules[key])
    .join("\n");
}
export function releasePreservation(prefix, category, value) {
  const key = { background: "background", composition: "layout" }[category];
  if (!key || !value.trim()) return "";
  const checkbox = document.getElementById(`${prefix}preserve-${key}`);
  if (!checkbox?.checked) return "";
  checkbox.checked = false;
  return `Отключено сохранение: ${preservationNames[key].toLowerCase()}.`;
}
