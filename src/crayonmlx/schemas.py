"""Validated configuration shared by the UI, storage and render adapters."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


PRESERVATION_RULES = {
    "identity": "Preserve the identity, distinctive features, and recognizable silhouettes of the original subjects.",
    "clothing": "Preserve the original clothing, accessories, and their distinctive details.",
    "poses": "Preserve the original poses, expressions, and gestures.",
    "colors": "Preserve the source colors and color relationships; shading may adapt to the selected light.",
    "objects": "Preserve the original foreground characters, animals, buildings that are main subjects, and other main objects; do not add or remove main subjects.",
    "layout": "Preserve the relative placement, scale, and arrangement of the original subjects.",
    "lettering": "Preserve intentional lettering, symbols, and decorations already present in the drawing.",
    "background": "Preserve the original background and location.",
}


class Preservation(StrictModel):
    # False defaults keep legacy presets and their composed prompts unchanged.
    identity: bool = False
    clothing: bool = False
    poses: bool = False
    colors: bool = False
    objects: bool = False
    layout: bool = False
    lettering: bool = False
    background: bool = False

    def compose(self) -> str:
        return "\n".join(text for key, text in PRESERVATION_RULES.items() if getattr(self, key))


class PromptBlocks(StrictModel):
    style: str = Field(default="", max_length=12000)
    subject: str = Field(default="", max_length=12000)
    background: str = Field(default="", max_length=12000)
    composition: str = Field(default="", max_length=12000)
    lighting: str = Field(default="", max_length=12000)
    constraints: str = Field(default="", max_length=12000)
    preservation: Preservation = Field(default_factory=Preservation)

    def compose(self) -> str:
        values = [
            self.style,
            self.subject,
            self.background,
            self.composition,
            self.lighting,
            self.constraints,
            self.preservation.compose(),
        ]
        return "\n\n".join(value.strip() for value in values if value.strip())


class Parameters(StrictModel):
    guidance: float = Field(default=2.5, ge=0, le=30)
    image_strength: float = Field(default=0.65, gt=0, le=1)
    steps: int = Field(default=30, ge=1, le=150)
    width: int = Field(default=768, ge=256, le=2048, multiple_of=16)
    height: int = Field(default=1024, ge=256, le=2048, multiple_of=16)
    seed: int = Field(default=-1, ge=-1, le=4294967295)
    quantize: Literal[4, 8] | None = 4


class Preset(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    engine: str = "mflux-qwen-edit"
    base_model: str = "qwen-image-edit-2511"
    blocks: PromptBlocks = Field(default_factory=PromptBlocks)
    parameters: Parameters = Field(default_factory=Parameters)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Название не может быть пустым")
        return value.strip()


class Settings(StrictModel):
    model_idle_minutes: int | None = Field(default=15, ge=1, le=10080)
    models_dir: str = Field(min_length=1)
    output_dir: str = Field(min_length=1)

    @field_validator("models_dir", "output_dir")
    @classmethod
    def absolute_path(cls, value: str) -> str:
        from pathlib import Path

        path = Path(value).expanduser()
        if not path.is_absolute():
            raise ValueError("Укажите абсолютный путь к папке")
        return str(path.resolve())


class GenerationRequest(StrictModel):
    preset: Preset
    model: str = Field(min_length=1)


class PromptTemplate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    category: Literal["style", "subject", "background", "composition", "lighting", "constraints"]
    text: str = Field(min_length=1, max_length=12000)

    @field_validator("name", "text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Поле не может быть пустым")
        return value.strip()


class GenerationConfig(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    engine: str
    base_model: str
    parameters: Parameters = Field(default_factory=Parameters)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Название не может быть пустым")
        return value.strip()
