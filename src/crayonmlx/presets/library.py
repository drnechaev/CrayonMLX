"""Independent reusable prompt fragments and render configurations."""

from crayonmlx.presets.catalog import initial_templates
from crayonmlx.presets.legacy_defaults import initial_presets as legacy_presets
from crayonmlx.presets.repository import JsonRepository
from crayonmlx.schemas import GenerationConfig, Parameters, PromptTemplate


def legacy_templates():
    names = {"style": "Стиль", "subject": "Герой", "background": "Фон",
             "composition": "Композиция", "constraints": "Ограничения"}
    for preset in legacy_presets():
        for category in names:
            text = getattr(preset.blocks, category)
            if text:
                yield PromptTemplate(name=f"{names[category]} · {preset.name}", category=category, text=text)


def initial_configs():
    return [
        GenerationConfig(
            name="Qwen Edit · портрет",
            engine="mflux-qwen-edit",
            base_model="qwen-image-edit-2511",
            parameters=Parameters(),
        ),
        GenerationConfig(
            name="Qwen Edit 2509 · квадрат",
            engine="mflux-qwen-edit",
            base_model="qwen-image-edit",
            parameters=Parameters(width=1024, height=1024),
        ),
        GenerationConfig(
            name="FLUX Dev · портрет",
            engine="mflux-flux",
            base_model="dev",
            parameters=Parameters(guidance=3.5, steps=25),
        ),
        GenerationConfig(
            name="FLUX Schnell · быстрый квадрат",
            engine="mflux-flux",
            base_model="schnell",
            parameters=Parameters(steps=4, width=768, height=768),
        ),
    ]


class PromptRepository(JsonRepository):
    def __init__(self, root):
        super().__init__(root, "prompt-templates", PromptTemplate, initial_templates)
        self.upgrade_pack("drawing-builder-v2", legacy_templates(), initial_templates())


class ConfigRepository(JsonRepository):
    def __init__(self, root):
        super().__init__(root, "generation-configs", GenerationConfig, initial_configs)
