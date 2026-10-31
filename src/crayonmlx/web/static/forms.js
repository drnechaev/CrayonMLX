/** Shared field helpers for the studio and independent library editors. */
import { option } from "./api.js";
export const blockNames = {
  style: "Общий стиль",
  subject: "Герои и объекты",
  background: "Место действия / фон",
  composition: "Композиция",
  lighting: "Свет",
  constraints: "Что изменить и сохранить",
};
export const parameterKeys = [
  "steps",
  "guidance",
  "width",
  "height",
  "image_strength",
  "seed",
  "quantize",
];
export const defaults = {
  steps: 30,
  guidance: 2.5,
  width: 768,
  height: 1024,
  image_strength: 0.65,
  seed: -1,
  quantize: 4,
};
export const $ = (id) => document.getElementById(id);

export function field(label, input) {
  const wrapper = document.createElement("label");
  wrapper.textContent = label;
  wrapper.append(input);
  return wrapper;
}
export function input(id, value = "") {
  const element = document.createElement("input");
  element.id = id;
  element.value = value;
  return element;
}
export function select(id, choices) {
  const element = document.createElement("select");
  element.id = id;
  element.replaceChildren(
    ...choices.map(([value, name]) => option(value, name)),
  );
  return element;
}
export function readParameters(prefix = "") {
  return Object.fromEntries(
    parameterKeys.map((key) => [
      key,
      key === "quantize" && $(prefix + key).value === "none"
        ? null
        : Number($(prefix + key).value),
    ]),
  );
}
export function setParameters(values, prefix = "") {
  for (const key of parameterKeys)
    $(prefix + key).value = values[key] === null ? "none" : values[key];
}
export function parameterFields(prefix, values = defaults) {
  const container = document.createElement("div");
  container.className = "parameter-grid";
  const specs = {
    steps: ["Шаги", 1, 150, 1],
    guidance: ["Guidance", 0, 30, 0.1],
    width: ["Ширина", 256, 2048, 16],
    height: ["Высота", 256, 2048, 16],
    image_strength: ["Image strength", 0.01, 1, 0.01],
    seed: ["Seed (-1 — случайный)", -1, 4294967295, 1],
  };
  for (const [key, [name, min, max, step]] of Object.entries(specs)) {
    const element = input(prefix + key, values[key]);
    element.type = "number";
    element.min = min;
    element.max = max;
    element.step = step;
    container.append(field(name, element));
  }
  const quantize = select(prefix + "quantize", [
    ["none", "None — без квантизации"],
    ["4", "4 bit"],
    ["8", "8 bit"],
  ]);
  quantize.value = values.quantize === null ? "none" : values.quantize;
  container.append(field("Квантизация", quantize));
  return container;
}
export function templateSelect(id, category, templates, text, onSelect) {
  const choices = templates.filter((item) => item.category === category);
  const element = select(id, [
    ["", "Не менять / без дополнительных указаний"],
    ...choices.map((item) => [item.id, item.name]),
  ]);
  element.value = choices.find((item) => item.text === text)?.id || "";
  element.addEventListener("change", () => {
    const item = choices.find((item) => item.id === element.value);
    onSelect(item ? item.text : "");
  });
  return element;
}
