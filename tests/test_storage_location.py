import json

from fastapi.testclient import TestClient

from crayonmlx.app import create_app
from crayonmlx.paths import data_directory


def test_transfer_preserves_snapshots_and_freezes_writes(client, tmp_path, monkeypatch):
    locator = tmp_path / "bootstrap" / "location.json"
    monkeypatch.setattr("crayonmlx.storage.location.location_file", lambda: locator)
    monkeypatch.setattr("crayonmlx.paths.location_file", lambda: locator)
    source = client.app.state.services.root
    target = tmp_path / "new-data"
    before = client.get("/api/settings").json()
    client.app.state.services.tokens.set("hf_local_secret")
    client.app.state.services.database.add_job(
        dict(
            id="old",
            created_at="now",
            status="completed",
            request='{"prompt":"Original prompt"}',
            source="/original/source.png",
            output="/original/output.png",
        )
    )
    response = client.post("/api/storage/location", json={"data_dir": str(target)})
    assert response.status_code == 200, response.text
    assert response.json()["restart_required"]
    assert (source / "crayonmlx.sqlite3").is_file()
    assert (target / "crayonmlx.sqlite3").is_file()
    assert (target / "hf-token").stat().st_mode & 0o777 == 0o600
    assert json.loads(locator.read_text())["data_dir"] == str(target)
    assert data_directory() == target
    body = {"models_dir": before["models_dir"], "output_dir": before["output_dir"]}
    assert client.put("/api/settings", json=body).status_code == 409
    with TestClient(create_app(target, engines={})) as relocated:
        settings = relocated.get("/api/settings").json()
        assert settings["models_dir"] == before["models_dir"]
        assert settings["output_dir"] == before["output_dir"]
        assert relocated.get("/api/generations/old").json()["request"]["prompt"] == "Original prompt"
        assert relocated.get("/api/presets").json() == client.get("/api/presets").json()


def test_transfer_rejects_nonempty_overlapping_and_active(client, tmp_path, monkeypatch):
    locator = tmp_path / "location.json"
    monkeypatch.setattr("crayonmlx.storage.location.location_file", lambda: locator)
    target = tmp_path / "existing"
    target.mkdir()
    (target / "precious.txt").write_text("keep")
    assert client.post("/api/storage/location", json={"data_dir": str(target)}).status_code == 422
    assert (target / "precious.txt").read_text() == "keep"
    source = client.app.state.services.root
    assert client.post("/api/storage/location", json={"data_dir": str(source / "nested")}).status_code == 422
    client.app.state.services.database.add_job(
        dict(id="pending", created_at="now", status="queued", request="{}", source="a", output="b")
    )
    assert client.post("/api/storage/location", json={"data_dir": str(tmp_path / "new")}).status_code == 422
    assert not locator.exists()


def test_copy_failure_keeps_original(client, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("test copy failure")

    monkeypatch.setattr("crayonmlx.storage.location.shutil.copytree", fail)
    source = client.app.state.services.root
    response = client.post("/api/storage/location", json={"data_dir": str(tmp_path / "new")})
    assert response.status_code == 400
    assert (source / "crayonmlx.sqlite3").is_file()
    assert client.app.state.pending_data_dir is None
    assert not (tmp_path / "new").exists()


def test_saved_location_overrides_bootstrap_environment(tmp_path, monkeypatch):
    target = tmp_path / "data"
    target.mkdir()
    (target / "crayonmlx.sqlite3").touch()
    locator = tmp_path / "location.json"
    locator.write_text(json.dumps({"data_dir": str(target)}))
    monkeypatch.setattr("crayonmlx.paths.location_file", lambda: locator)
    monkeypatch.setenv("CRAYONMLX_DATA_DIR", str(tmp_path / "old"))
    assert data_directory() == target
