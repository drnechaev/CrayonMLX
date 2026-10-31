import json

import pytest
from PIL import Image

from crayonmlx.models.catalog import list_models
from crayonmlx.models.identity import identify_model


@pytest.mark.parametrize("variant", ["dev", "schnell", "krea-dev", "qwen-image-edit", "qwen-image-edit-2511"])
def test_mflux_manifest_is_independent_of_folder_name(tmp_path, variant):
    root = tmp_path / "arbitrary-name"
    root.mkdir()
    (root / "mflux_model.json").write_text(json.dumps({"model_name": variant}))
    assert identify_model(root).base_model == variant
    assert list_models(root)[0]["recognized"]


def test_hf_qwen_snapshot_without_model_index(tmp_path):
    root = tmp_path / "models--Qwen--Qwen-Image-Edit-2509" / "snapshots" / "hash"
    (root / "transformer").mkdir(parents=True)
    (root / "transformer" / "config.json").write_text('{"_class_name": "QwenImageTransformer2DModel"}')
    assert identify_model(root).base_model == "qwen-image-edit"
    assert identify_model(root).engine == "mflux-qwen-edit"


def test_named_prequantized_checkpoint(tmp_path):
    root = tmp_path / "Qwen--Qwen-Image-Edit-2511-4bit"
    root.mkdir()
    assert identify_model(root).base_model == "qwen-image-edit-2511"


def test_ambiguous_qwen_version_is_not_guessed(tmp_path):
    (tmp_path / "model_index.json").write_text('{"_class_name": "QwenImageEditPlusPipeline"}')
    with pytest.raises(ValueError, match="однозначно"):
        identify_model(tmp_path)
    assert not list_models(tmp_path)[0]["recognized"]


@pytest.mark.parametrize("pipeline", ["FluxKontextPipeline", "Flux2Pipeline", "QwenImagePipeline"])
def test_incompatible_pipeline_rejected_despite_model_name(tmp_path, pipeline):
    (tmp_path / "mflux_model.json").write_text('{"model_name": "dev"}')
    (tmp_path / "model_index.json").write_text(json.dumps({"_class_name": pipeline}))
    with pytest.raises(ValueError, match="Архитектура"):
        identify_model(tmp_path)


def test_conflicting_metadata_and_corrupt_json(tmp_path):
    (tmp_path / "mflux_model.json").write_text('{"model_name":"dev", "base_model":"schnell"}')
    with pytest.raises(ValueError, match="однозначно"):
        identify_model(tmp_path)
    (tmp_path / "mflux_model.json").write_text("broken")
    assert not list_models(tmp_path)[0]["recognized"]


def test_server_uses_selected_checkpoint_instead_of_preset(client):
    from crayonmlx.schemas import GenerationRequest, Preset, PromptBlocks

    state = client.app.state.services
    request = GenerationRequest(
        model="qwen",
        preset=Preset(
            name="Old FLUX preset",
            engine="mflux-flux",
            base_model="schnell",
            blocks=PromptBlocks(subject="A cat"),
        ),
    )
    job = state.queue.submit(request, Image.new("RGB", (16, 16)))
    assert job["request"]["preset"]["engine"] == "mflux-qwen-edit"
    assert job["request"]["preset"]["base_model"] == "qwen-image-edit-2511"
    assert request.preset.engine == "mflux-flux"  # Original preset remains unchanged.


def test_unknown_model_cannot_reuse_preset_identity(client, tmp_path):
    from pathlib import Path

    from crayonmlx.schemas import GenerationRequest, Preset, PromptBlocks

    state = client.app.state.services
    model = Path(state.database.settings().models_dir) / "unknown"
    model.mkdir()
    (model / "config.json").write_text("{}")
    request = GenerationRequest(
        model="unknown", preset=Preset(name="Known preset", blocks=PromptBlocks(subject="A cat"))
    )
    with pytest.raises(ValueError, match="однозначно"):
        state.queue.submit(request, Image.new("RGB", (16, 16)))
    assert state.database.jobs() == []
