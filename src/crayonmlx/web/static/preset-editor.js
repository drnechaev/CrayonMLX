/** CRUD editors for the three independent libraries; never edits history. */
import { api, handle, toast } from "./api.js";
import {
  $,
  blockNames,
  defaults,
  field,
  input,
  select,
  parameterFields,
  readParameters,
  templateSelect,
} from "./forms.js";
import { library, refreshLibrary, readPreset } from "./presets.js";
import {
  preservationFields,
  readPreservation,
  releasePreservation,
} from "./preservation.js";
let kind = "full",
  selected = "";
const sources = {
  full: ["presets", "presets"],
  prompts: ["templates", "prompt-templates"],
  configs: ["configs", "generation-configs"],
};

function emptyEntry() {
  if (kind === "prompts")
    return { name: "Новая заготовка", category: "style", text: "" };
  const studio = readPreset();
  return kind === "full"
    ? { ...studio, name: "Новый пресет" }
    : {
        name: "Новый конфиг",
        engine: studio.engine,
        base_model: studio.base_model,
        parameters: { ...defaults },
      };
}
function readEditor() {
  const name = $("edit-name").value.trim();
  if (kind === "prompts")
    return {
      name,
      category: $("edit-category").value,
      text: $("edit-text").value,
    };
  const value = {
    name,
    engine: $("library-form").dataset.engine,
    base_model: $("library-form").dataset.baseModel,
    parameters: readParameters("edit-"),
  };
  if (kind === "full")
    value.blocks = {
      ...Object.fromEntries(
        Object.keys(blockNames).map((key) => [
          key,
          $(`edit-block-${key}`).value,
        ]),
      ),
      preservation: readPreservation("edit-"),
    };
  return value;
}
function editorBody(entry) {
  const form = document.createElement("form");
  form.id = "library-form";
  form.className = "panel";
  form.dataset.engine = entry.engine || "mflux-qwen-edit";
  form.dataset.baseModel = entry.base_model || "qwen-image-edit-2511";
  const title = document.createElement("h2");
  title.textContent = entry.name;
  form.append(title);
  const name = input("edit-name", entry.name);
  name.maxLength = 100;
  name.required = true;
  form.append(field("Название", name));
  if (kind === "prompts") {
    form.append(
      field(
        "Блок промпта",
        select("edit-category", Object.entries(blockNames)),
      ),
    );
    const text = document.createElement("textarea");
    text.id = "edit-text";
    text.value = entry.text;
    text.required = true;
    text.maxLength = 12000;
    text.rows = 10;
    form.append(field("Текст заготовки", text));
  } else {
    if (kind === "full") {
      const configPicker = select("edit-config", [
        ["", "Текущие параметры"],
        ...library.configs.map((item) => [item.id, item.name]),
      ]);
      configPicker.addEventListener("change", () => {
        const config = library.configs.find(
          (item) => item.id === configPicker.value,
        );
        if (!config) return;
        const current = readEditor();
        Object.assign(current, {
          parameters: config.parameters,
        });
        replaceForm(current);
      });
      form.append(field("Взять параметры из конфига", configPicker));
    }
    const hint = document.createElement("p");
    hint.className = "hint";
    hint.textContent =
      "Модель выбирается в студии. Параметры применяются с учётом её возможностей.";
    form.append(hint, parameterFields("edit-", entry.parameters));
    if (kind === "full")
      for (const [category, label] of Object.entries(blockNames)) {
        const text = document.createElement("textarea");
        text.id = `edit-block-${category}`;
        text.value = entry.blocks[category] || "";
        text.maxLength = 12000;
        const picker = templateSelect(
          `edit-template-${category}`,
          category,
          library.templates,
          text.value,
          (value) => {
            text.value = value;
            const message = releasePreservation("edit-", category, value);
            if (message) toast(message);
          },
        );
        picker.setAttribute("aria-label", `Заготовка: ${label}`);
        text.addEventListener("input", () => {
          picker.value = "";
          const message = releasePreservation("edit-", category, text.value);
          if (message) toast(message);
        });
        form.append(field(label, picker), text);
        if (category === "constraints")
          form.append(
            preservationFields(
              "edit-",
              entry.blocks.preservation || {},
              (key, checked) => {
                const category = {
                  background: "background",
                  layout: "composition",
                }[key];
                if (
                  checked &&
                  category &&
                  document.getElementById(`edit-block-${category}`).value.trim()
                ) {
                  document.getElementById(`edit-preserve-${key}`).checked =
                    false;
                  toast(
                    "Сначала очистите соответствующий блок фона или композиции.",
                  );
                }
              },
            ),
          );
      }
  }
  const buttons = document.createElement("div");
  buttons.className = "button-row";
  const save = document.createElement("button");
  save.type = "submit";
  save.className = "primary";
  save.textContent = "Сохранить";
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "subtle danger";
  remove.textContent = "Удалить";
  remove.disabled = !selected;
  remove.addEventListener(
    "click",
    handle(async () => {
      if (
        !confirm(
          "Удалить запись из библиотеки? Прошлые генерации останутся в истории.",
        )
      )
        return;
      await api(`/${sources[kind][1]}/${selected}`, { method: "DELETE" });
      selected = "";
      await refreshLibrary();
      renderEditor();
      toast("Запись удалена");
    }),
  );
  buttons.append(save, remove);
  form.append(buttons);
  form.addEventListener(
    "submit",
    handle(async (event) => {
      event.preventDefault();
      const value = readEditor(),
        endpoint = sources[kind][1];
      const saved = await api(`/${endpoint}${selected ? `/${selected}` : ""}`, {
        method: selected ? "PUT" : "POST",
        body: JSON.stringify(value),
      });
      selected = saved.id;
      await refreshLibrary();
      renderEditor();
      toast("Сохранено в библиотеку");
    }),
  );
  return form;
}
function replaceForm(entry) {
  $("library-form").replaceWith(editorBody(entry));
  if (kind === "prompts") $("edit-category").value = entry.category;
}
export function renderEditor() {
  const items = library[sources[kind][0]];
  if (selected && !items.some((item) => item.id === selected)) selected = "";
  const container = $("preset-editor");
  container.replaceChildren();
  container.className = "library-layout";
  const list = document.createElement("aside");
  list.className = "panel library-list";
  const create = document.createElement("button");
  create.className = "primary";
  create.textContent = "+ Создать";
  create.addEventListener("click", () => {
    selected = "";
    renderEditor();
  });
  list.append(create);
  for (const item of items) {
    const button = document.createElement("button");
    button.className = `library-item${item.id === selected ? " active" : ""}`;
    button.textContent = item.name;
    button.addEventListener("click", () => {
      selected = item.id;
      renderEditor();
    });
    list.append(button);
  }
  const entry = items.find((item) => item.id === selected) || emptyEntry();
  container.append(list, editorBody(entry));
  if (kind === "prompts") $("edit-category").value = entry.category;
}
export function initializeEditor() {
  for (const button of document.querySelectorAll("[data-library]"))
    button.addEventListener("click", () => {
      kind = button.dataset.library;
      selected = "";
      document
        .querySelectorAll("[data-library]")
        .forEach((item) => item.classList.toggle("active", item === button));
      renderEditor();
    });
  renderEditor();
}
