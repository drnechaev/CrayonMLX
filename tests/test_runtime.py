from pathlib import Path
from types import SimpleNamespace

import pytest

from crayonmlx.models.runtime import ModelRuntime
from crayonmlx.schemas import Preset, PromptBlocks, Settings


class FakeWorker:
    def __init__(self, root):
        self.commands = []
        self.closed = False
        self.phase = "ready"
        self.fail = False

    def request(self, payload):
        self.commands.append(payload)
        if self.fail:
            raise RuntimeError("test worker failure")
        if payload["action"] == "render":
            Path(payload["output"]).write_bytes(b"test output")

    def snapshot(self):
        return {
            "phase": self.phase,
            "memory_active_bytes": 1024,
            "memory_peak_bytes": 2048,
            "memory_cache_bytes": 0,
        }

    def alive(self):
        return not self.closed

    def close(self):
        self.closed = True


@pytest.fixture
def runtime(tmp_path):
    settings = Settings(models_dir=str(tmp_path), output_dir=str(tmp_path), model_idle_minutes=15)
    clock = [0.0]
    workers = []

    def factory(root):
        worker = FakeWorker(root)
        workers.append(worker)
        return worker

    manager = ModelRuntime(tmp_path / "runtime", lambda: settings, factory, lambda: clock[0])
    yield manager, settings, clock, workers
    manager.close()


def render(manager, tmp_path, quantize=4):
    preset = Preset(name="Test", blocks=PromptBlocks(subject="Cat"))
    preset.parameters.quantize = quantize
    manager.render(
        SimpleNamespace(id="mflux-qwen-edit"),
        preset,
        tmp_path / "model",
        tmp_path / "source",
        tmp_path / "output",
    )


def test_reuse_and_idle_timeout(runtime, tmp_path):
    manager, settings, clock, workers = runtime
    render(manager, tmp_path)
    clock[0] = 800
    render(manager, tmp_path)
    assert len(workers) == 1
    assert [command["action"] for command in workers[0].commands] == ["load", "render", "render"]
    clock[0] = 1699
    manager.expire_idle()
    assert manager.snapshot()["phase"] == "ready"
    clock[0] = 1700
    manager.expire_idle()
    assert workers[0].closed
    assert manager.snapshot()["phase"] == "unloaded"


def test_none_keeps_model_loaded_and_memory_reported(runtime, tmp_path):
    manager, settings, clock, workers = runtime
    settings.model_idle_minutes = None
    render(manager, tmp_path)
    clock[0] = 1_000_000
    manager.expire_idle()
    state = manager.snapshot()
    assert state["phase"] == "ready"
    assert state["unload_in_seconds"] is None
    assert state["memory_active_bytes"] == 1024
    assert not workers[0].closed


def test_busy_worker_not_unloaded(runtime, tmp_path):
    manager, settings, clock, workers = runtime
    render(manager, tmp_path)
    clock[0] = 9999
    with manager.operation:
        manager.expire_idle()
        with pytest.raises(ValueError):
            manager.unload()
    assert not workers[0].closed
    manager.expire_idle()
    assert workers[0].closed


def test_quantization_change_reloads_and_failure_releases_process(runtime, tmp_path):
    manager, settings, clock, workers = runtime
    render(manager, tmp_path)
    render(manager, tmp_path, None)
    assert len(workers) == 2
    assert workers[0].closed
    workers[1].fail = True
    with pytest.raises(RuntimeError):
        render(manager, tmp_path, None)
    assert workers[1].closed
    assert manager.snapshot()["phase"] == "error"


def test_disable_preserves_files_and_blocks_new_jobs(client):
    import json

    from test_studio import request_body, upload

    model = client.get("/api/models").json()[0]
    assert model["enabled"]
    assert (
        client.post("/api/models/availability", json={"model": model["id"], "enabled": False}).status_code
        == 200
    )
    assert not client.get("/api/models").json()[0]["enabled"]
    assert Path(model["path"]).is_dir()
    response = client.post(
        "/api/generations", data={"config": json.dumps(request_body(client))}, files={"image": upload()}
    )
    assert response.status_code == 422
    assert client.post("/api/models/load", json={"model": model["id"]}).status_code == 422
    assert (
        client.post("/api/models/availability", json={"model": model["id"], "enabled": True}).status_code
        == 200
    )


def test_timeout_settings_roundtrip(client):
    state = client.get("/api/settings").json()
    assert state["model_idle_minutes"] == 15
    body = {"models_dir": state["models_dir"], "output_dir": state["output_dir"], "model_idle_minutes": None}
    assert client.put("/api/settings", json=body).json()["model_idle_minutes"] is None
    body["model_idle_minutes"] = 30
    assert client.put("/api/settings", json=body).json()["model_idle_minutes"] == 30


def test_job_returns_live_progress_without_writing_history(client, monkeypatch):
    state = client.app.state.services
    request = {"model_path": "/model", "preset": {}}
    import json

    state.database.add_job(
        dict(
            id="progress",
            created_at="now",
            status="running",
            request=json.dumps(request),
            source="a",
            output="b",
        )
    )
    monkeypatch.setattr(
        state.runtime,
        "snapshot",
        lambda: {"model_path": "/model", "phase": "denoising", "step": 8, "total_steps": 30},
    )
    assert client.get("/api/generations/progress").json()["progress"]["step"] == 8
    assert "progress" not in state.database.job("progress")
