"""Full presets are editable snapshots of independently selectable blocks."""

from crayonmlx.presets.catalog import EDIT_RULES, default_preservation, initial_templates
from crayonmlx.schemas import Preset, PromptBlocks


def initial_presets() -> list[Preset]:
    templates = {item.name: item.text for item in initial_templates()}
    original = PromptBlocks(constraints=EDIT_RULES, preservation=default_preservation())
    tokyo = original.model_copy(deep=True)
    tokyo.subject = templates["Герои и объекты · Аниме"]
    tokyo.background = templates["Фон · Токио"]
    tokyo.composition = templates["Композиция · Целиком"]
    tokyo.lighting = templates["Свет · Неоновый"]
    tokyo.preservation.background = False
    tokyo.preservation.layout = False
    cinematic = original.model_copy(deep=True)
    cinematic.style = templates["Стиль · Хантрик"]
    cinematic.lighting = templates["Свет · Мягкий дневной"]
    return [
        Preset(name="Без изменений · исходная сцена", blocks=original),
        Preset(name="Аниме-герои · вечерний Токио", blocks=tokyo),
        Preset(name="Хантрик · исходная сцена", blocks=cinematic),
    ]
