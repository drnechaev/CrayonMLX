"""Persistent MLX process. Commands arrive on stdin; atomic files carry responses/status."""

import gc
import json
import sys
import threading
import time
import traceback
from pathlib import Path

from crayonmlx.schemas import Preset


class Telemetry:
    def __init__(self, root, mx):
        self.root, self.mx = root, mx
        self.lock = threading.Lock()
        self.state = {"phase": "starting", "step": 0, "total_steps": None}
        self.started = None
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)
        self.thread.start()

    def update(self, **values):
        with self.lock:
            self.state.update(values)
            self._write()

    def _write(self):
        state = {
            **self.state,
            "memory_active_bytes": self.mx.get_active_memory(),
            "memory_cache_bytes": self.mx.get_cache_memory(),
            "memory_peak_bytes": self.mx.get_peak_memory(),
            "elapsed_seconds": round(time.monotonic() - self.started, 1) if self.started else 0,
        }
        temporary = self.root / "status.tmp"
        temporary.write_text(json.dumps(state), encoding="utf-8")
        temporary.replace(self.root / "status.json")

    def _sample(self):
        while not self.stopped.wait(1):
            with self.lock:
                self._write()

    def call_before_loop(self, config, **kwargs):
        self.update(
            phase="denoising", step=0, total_steps=max(0, config.num_inference_steps - config.init_time_step)
        )

    def call_in_loop(self, t, config, latents, **kwargs):
        self.mx.eval(latents)  # Report completed work, not just lazily scheduled GPU operations.
        self.update(phase="denoising", step=t - config.init_time_step + 1)

    def call_after_loop(self, **kwargs):
        self.update(phase="decoding")


def load_model(payload):
    from mflux.models.common.config import ModelConfig

    config = ModelConfig.from_name(model_name=payload["base_model"])
    if payload["engine"] == "mflux-flux":
        from mflux.models.flux.variants.txt2img.flux import Flux1

        model_class = Flux1
    elif payload["engine"] == "mflux-qwen-edit":
        from mflux.models.qwen.variants.edit.qwen_image_edit import QwenImageEdit

        model_class = QwenImageEdit
    else:
        raise ValueError("Unsupported MLX adapter")
    return model_class(model_config=config, quantize=payload["quantize"], model_path=payload["model_path"])


def render(model, payload):
    preset = Preset.model_validate(payload["preset"])
    params = preset.parameters
    arguments = dict(
        seed=params.seed,
        prompt=preset.blocks.compose(),
        width=params.width,
        height=params.height,
        num_inference_steps=params.steps,
        guidance=params.guidance,
    )
    if preset.engine == "mflux-flux":
        arguments.update(image_path=payload["source"], image_strength=params.image_strength)
    else:
        arguments.update(image_paths=[payload["source"]], image_path=payload["source"])
    image = model.generate_image(**arguments)
    image.save(path=payload["output"])


def main():
    import mlx.core as mx

    root = Path(sys.argv[1])
    telemetry = Telemetry(root, mx)
    model = None
    try:
        for line in sys.stdin:
            payload = json.loads(line)
            response = root / f"{payload['request_id']}.json"
            try:
                if payload["action"] == "load":
                    telemetry.update(phase="loading", step=0, total_steps=None)
                    model = load_model(payload)
                    mx.eval(model.parameters())
                    model.callbacks.register(telemetry)
                elif payload["action"] == "render":
                    if model is None:
                        raise RuntimeError("Model is not loaded")
                    telemetry.started = time.monotonic()
                    mx.reset_peak_memory()
                    telemetry.update(phase="preparing", step=0, total_steps=None)
                    render(model, payload)
                    gc.collect()
                    mx.clear_cache()
                else:
                    raise ValueError("Unknown command")
                telemetry.update(phase="ready", effective_quantize=getattr(model, "bits", None))
                result = {"ok": True}
            except Exception as error:
                traceback.print_exc()
                telemetry.update(phase="error")
                result = {"ok": False, "error": str(error)}
            temporary = response.with_suffix(".tmp")
            temporary.write_text(json.dumps(result), encoding="utf-8")
            temporary.replace(response)
    finally:
        telemetry.stopped.set()
        telemetry.thread.join(timeout=2)


if __name__ == "__main__":
    main()
