# CrayonMLX

A local web studio for transforming children's drawings on Apple Silicon.
Choose what to change — style, characters, background, composition, and lighting —
and explicitly preserve the details that matter.

[Source code and full documentation](https://github.com/drnechaev/CrayonMLX)
· [Report an issue](https://github.com/drnechaev/CrayonMLX/issues)

## Requirements

- An Apple Silicon Mac with a macOS version supported by MLX.
- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
- A supported local model and enough memory for its weights and inference.

## Install and run

Install the published alpha:

```sh
uv tool install 'crayonmlx==0.1.0a1'
crayonmlx
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787) in your browser.
To use a different port, run `crayonmlx --port 8788`.
Stop the application with Ctrl+C in its terminal.

## First transformation

1. In **Settings**, choose your model folder and the folder for generated images.
2. Add a complete supported checkpoint manually, or download a Hugging Face repository
   from **Models**. For gated repositories, configure your HF token in Settings and
   obtain access on Hugging Face first. Weights are not bundled with the application.
3. Upload a drawing and select a local model.
4. Independently choose an overall style, a treatment for the original characters or
   objects, a background, composition, and lighting. Edit any instruction if needed.
5. Mark what must remain: identity, clothing, poses, colors, main subjects,
   placement, lettering, and the original background. Choosing a new background
   releases background preservation; reframing releases placement preservation.
6. Choose a saved generation configuration, inspect the composed prompt, and generate.

For example: **anime characters → Tokyo background → entire subject → neon lighting**,
while preserving the original characters' identity, clothes, poses, and colors.

The interface is currently in Russian; built-in generation instructions are in English.
Prompt templates, numerical generation configurations, and full presets can be
created, edited, and saved separately. History stores the original image, result,
and complete request as an immutable snapshot.

## Supported models

Native MLX inference through MFLUX:

- **Qwen Image Edit**: 2509 and 2511. Instruction-based editing with an input image;
  image strength is not applied by this adapter.
- **FLUX.1 image-to-image**: dev, schnell, and krea-dev. Schnell does not apply guidance.

Use complete compatible checkpoints, not an isolated `.safetensors` or `.gguf` file.
The adapter is detected from the selected local model. Downloads are explicit;
missing components during generation do not trigger automatic downloads.
Memory requirements depend on the model, quantization, and output dimensions.

## Local workflow

- Model loading, generation stages, completed steps, and MLX memory usage are visible
  in the interface.
- One model stays loaded between generations, with a default idle timeout of
  15 minutes. Change the timeout or select None in Settings.
- Model enable/disable and manual load/unload controls are available.
- Model, output, and internal application-data folders are configurable.
- The server listens only on `127.0.0.1`; generation runs locally on your Mac.

CrayonMLX is an early alpha. For setup details, source installation, development,
and the complete storage behavior, see the
[GitHub README](https://github.com/drnechaev/CrayonMLX#readme).

## License

CrayonMLX is licensed under the [MIT License](https://github.com/drnechaev/CrayonMLX/blob/main/LICENSE).
Copyright (c) 2026 Nikolay Nechaev.
Model weights and third-party dependencies retain their respective licenses.
