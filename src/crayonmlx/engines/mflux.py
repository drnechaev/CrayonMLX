"""MFLUX CLI adapters run in isolated processes so Metal memory is released per job."""

import os
import platform
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

from crayonmlx.schemas import Preset


class MfluxEngine:
    def __init__(self, runtime=None):
        self.runtime = runtime

    def available(self) -> bool:
        return (
            platform.system() == "Darwin" and platform.machine() == "arm64" and find_spec("mflux") is not None
        )

    def command(self, preset: Preset, model: Path, source: Path, output: Path) -> list[str]:
        parameters = preset.parameters
        return [
            sys.executable,
            "-m",
            self.module,
            "--model",
            str(model),
            "--base-model",
            preset.base_model,
            "--prompt",
            preset.blocks.compose(),
            "--seed",
            str(parameters.seed),
            "--steps",
            str(parameters.steps),
            "--width",
            str(parameters.width),
            "--height",
            str(parameters.height),
            *(["--quantize", str(parameters.quantize)] if parameters.quantize is not None else []),
            "--output",
            str(output),
            *self.image_arguments(preset, source),
        ]

    def render(self, preset: Preset, model: Path, source: Path, output: Path) -> dict | None:
        if not self.available():
            raise RuntimeError("Нужен Mac Apple Silicon и MFLUX. Установите: uv sync или uv tool install .")
        if self.runtime is not None:
            return self.runtime.render(self, preset, model, source, output)
        # Generation must never trigger implicit network access or ignore missing weights.
        environment = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        log = output.with_suffix(".log")
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                self.command(preset, model, source, output),
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if result.returncode or not output.is_file():
            tail = log.read_text(encoding="utf-8", errors="replace")[-3000:]
            raise RuntimeError(f"MFLUX не завершил генерацию. Проверьте полноту и тип модели.\n{tail}")


class FluxEngine(MfluxEngine):
    id = "mflux-flux"
    name = "MFLUX · FLUX.1 image-to-image"
    module = "mflux.models.flux.cli.flux_generate"
    base_models = ("dev", "schnell", "krea-dev")
    supports_strength = True

    def image_arguments(self, preset: Preset, source: Path) -> list[str]:
        result = ["--image-path", str(source), "--image-strength", str(preset.parameters.image_strength)]
        if preset.base_model != "schnell":
            result += ["--guidance", str(preset.parameters.guidance)]
        return result


class QwenEditEngine(MfluxEngine):
    id = "mflux-qwen-edit"
    name = "MFLUX · Qwen Image Edit"
    module = "mflux.models.qwen.cli.qwen_image_edit_generate"
    base_models = ("qwen-image-edit-2511", "qwen-image-edit")
    supports_strength = False

    def image_arguments(self, preset: Preset, source: Path) -> list[str]:
        return ["--image-paths", str(source), "--guidance", str(preset.parameters.guidance)]
