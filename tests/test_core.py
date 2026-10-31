import json
from pathlib import Path
from threading import Event

import pytest
from PIL import Image
from pydantic import ValidationError

from crayonmlx.engines.mflux import FluxEngine, QwenEditEngine
from crayonmlx.generation.queue import GenerationQueue
from crayonmlx.models.catalog import list_models, resolve_model
from crayonmlx.models.downloads import Downloads
from crayonmlx.presets.repository import PresetRepository
from crayonmlx.schemas import GenerationRequest, Preset, PromptBlocks, Settings
from crayonmlx.storage.database import Database
from crayonmlx.storage.secrets import TokenStore


def test_prompt_order_and_preset_persistence(tmp_path):
    blocks = PromptBlocks(
        style="  style  ", subject="hero", background="", composition=" frame ", constraints="rules"
    )
    assert blocks.compose() == "style\n\nhero\n\nframe\n\nrules"
    repository = PresetRepository(tmp_path)
    for item in repository.list():
        repository.delete(item["id"])
    assert PresetRepository(tmp_path).list() == []  # Never reinsert deleted defaults.
    with pytest.raises(ValueError):
        repository.save("../escape", Preset(name="Test"))
    with pytest.raises(ValidationError):
        Settings(models_dir="relative", output_dir=str(tmp_path))


def test_catalog_hides_downloads_and_rejects_escapes(tmp_path):
    root = tmp_path / "models"
    (root / "valid").mkdir(parents=True)
    (root / "valid" / "model_index.json").write_text("{}")
    (root / ".download-partial").mkdir()
    (root / ".download-partial" / "config.json").write_text("{}")
    (root / "single.safetensors").touch()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "config.json").write_text("{}")
    (root / "escape").symlink_to(outside)
    assert [item["id"] for item in list_models(root)] == ["valid"]
    for name in ("../outside", "escape", "/outside"):
        with pytest.raises(ValueError):
            resolve_model(root, name)


def test_adapters_have_distinct_capabilities_and_no_shell():
    preset = Preset(name="Qwen", blocks=PromptBlocks(subject="Draw a cat"))
    qwen = QwenEditEngine().command(preset, Path("/models/qwen"), Path("/drawing.png"), Path("/result.png"))
    assert "--image-paths" in qwen and "--image-strength" not in qwen
    preset.engine, preset.base_model = "mflux-flux", "schnell"
    flux = FluxEngine().command(preset, Path("/models/flux"), Path("/drawing.png"), Path("/result.png"))
    assert "--image-strength" in flux and "--guidance" not in flux


def test_queue_serializes_and_records_failure(tmp_path):
    started, release = Event(), Event()
    calls = []

    class Engine:
        id = "mflux-flux"
        base_models = ("schnell",)

        def render(self, preset, model, source, output):
            calls.append(preset.name)
            if len(calls) == 1:
                started.set()
                assert release.wait(5)
                Image.new("RGB", (16, 16)).save(output)
            else:
                raise RuntimeError("deliberate test failure")

    database = Database(tmp_path / "data")
    model = tmp_path / "models" / "test"
    model.mkdir(parents=True)
    (model / "mflux_model.json").write_text('{"model_name": "schnell"}')
    database.save_settings(Settings(models_dir=str(model.parent), output_dir=str(tmp_path / "outputs")))
    queue = GenerationQueue(database, {"mflux-flux": Engine()})
    request = GenerationRequest(
        preset=Preset(
            name="first", engine="mflux-flux", base_model="schnell", blocks=PromptBlocks(subject="hello")
        ),
        model="test",
    )
    try:
        first = queue.submit(request, Image.new("RGB", (16, 16)))
        assert started.wait(5)
        request.preset.name = "second"
        second = queue.submit(request, Image.new("RGB", (16, 16)))
        assert calls == ["first"]
        assert database.job(second["id"])["status"] == "queued"
    finally:
        release.set()
        queue.close()
    assert database.job(first["id"])["status"] == "completed"
    assert database.job(second["id"])["status"] == "failed"
    assert "deliberate" in database.job(second["id"])["error"]
    assert database.job(first["id"])["request"]["preset"]["name"] == "first"
    assert json.loads(Path(first["output"]).with_name("generation.json").read_text())["model_path"] == str(
        model
    )


def test_restart_marks_pending_jobs_failed(tmp_path):
    database = Database(tmp_path)
    database.add_job(
        dict(id="pending", created_at="today", status="queued", request="{}", source="a", output="b")
    )
    restarted = Database(tmp_path)
    assert restarted.job("pending")["status"] == "failed"


def test_explicit_hf_download_uses_token_and_publishes_after_completion(tmp_path, monkeypatch):
    tokens = TokenStore(tmp_path)
    tokens.set("hf_test")
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        path = kwargs["local_dir"]
        path.mkdir()
        (path / "model_index.json").write_text("{}")

    monkeypatch.setattr("crayonmlx.models.downloads.snapshot_download", download)
    downloads = Downloads(tokens)
    try:
        downloads.start(tmp_path / "models", "Qwen/example", "revision-id")
    finally:
        downloads.close()
    assert calls[0]["token"] == "hf_test"
    assert calls[0]["revision"] == "revision-id"
    assert downloads.list()[0]["status"] == "completed"
    assert list_models(tmp_path / "models")[0]["id"] == "Qwen--example"
    assert "hf_test" not in json.dumps(downloads.list())


def test_download_error_hides_credentials(tmp_path, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("hf_secret should never reach the UI")

    monkeypatch.setattr("crayonmlx.models.downloads.snapshot_download", fail)
    downloads = Downloads(TokenStore(tmp_path))
    downloads.start(tmp_path / "models", "Qwen/example", "main")
    downloads.close()
    assert downloads.list()[0]["status"] == "failed"
    assert "hf_secret" not in downloads.list()[0]["error"]


def test_data_directory_override(tmp_path, monkeypatch):
    from crayonmlx.paths import data_directory

    monkeypatch.setattr("crayonmlx.paths.location_file", lambda: tmp_path / "no-location.json")
    monkeypatch.setenv("CRAYONMLX_DATA_DIR", str(tmp_path / "custom"))
    assert data_directory() == tmp_path / "custom"


def test_no_quantization_omits_cli_flag():
    preset = Preset(name="Unquantized", blocks=PromptBlocks(subject="A cat"))
    preset.parameters.quantize = None
    restored = Preset.model_validate_json(preset.model_dump_json())
    assert restored.parameters.quantize is None
    for engine in (FluxEngine(), QwenEditEngine()):
        command = engine.command(restored, Path("/model"), Path("/source.png"), Path("/result.png"))
        assert "--quantize" not in command
        assert "None" not in command
