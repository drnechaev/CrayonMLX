from subprocess import CompletedProcess, TimeoutExpired

import pytest

from crayonmlx.web.folders import _SCRIPT, choose_folder


def test_native_chooser_uses_arguments_and_existing_parent(tmp_path, monkeypatch):
    calls = []

    def run(arguments, **options):
        calls.append((arguments, options))
        return CompletedProcess(arguments, 0, str(tmp_path) + "/\n", "")

    monkeypatch.setattr("crayonmlx.web.folders.platform.system", lambda: "Darwin")
    monkeypatch.setattr("crayonmlx.web.folders.subprocess.run", run)
    assert choose_folder('Choose "folder"', str(tmp_path / "not-created")) == str(tmp_path)
    assert calls[0][0] == ["/usr/bin/osascript", "-e", _SCRIPT, 'Choose "folder"', str(tmp_path)]
    assert str(tmp_path) not in _SCRIPT
    assert not calls[0][1].get("shell", False)


def test_cancel_does_not_change_settings(client, monkeypatch):
    before = client.get("/api/settings").json()
    monkeypatch.setattr("crayonmlx.web.folders.choose_folder", lambda *args: None)
    assert client.post("/api/folders/select", json={"target": "models_dir"}).json() == {"path": None}
    assert client.get("/api/settings").json() == before


def test_selection_is_not_saved_until_explicit_save(client, tmp_path, monkeypatch):
    before = client.get("/api/settings").json()
    monkeypatch.setattr("crayonmlx.web.folders.choose_folder", lambda *args: str(tmp_path))
    assert client.post("/api/folders/select", json={"target": "output_dir"}).json() == {"path": str(tmp_path)}
    assert client.get("/api/settings").json() == before
    assert client.post("/api/folders/select", json={"target": "arbitrary"}).status_code == 422


def test_native_cancel_and_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("crayonmlx.web.folders.platform.system", lambda: "Darwin")
    monkeypatch.setattr(
        "crayonmlx.web.folders.subprocess.run", lambda *args, **kwargs: CompletedProcess([], 0, "\n", "")
    )
    assert choose_folder("Choose", str(tmp_path)) is None
    monkeypatch.setattr(
        "crayonmlx.web.folders.subprocess.run", lambda *args, **kwargs: CompletedProcess([], 1, "", "failed")
    )
    with pytest.raises(RuntimeError, match="диалог"):
        choose_folder("Choose", str(tmp_path))


def test_timeout_releases_dialog_lock(client, monkeypatch):
    monkeypatch.setattr("crayonmlx.web.folders.platform.system", lambda: "Darwin")

    def timeout(*args, **kwargs):
        raise TimeoutExpired("osascript", 300)

    monkeypatch.setattr("crayonmlx.web.folders.subprocess.run", timeout)
    assert client.post("/api/folders/select", json={"target": "models_dir"}).status_code == 503
    monkeypatch.setattr("crayonmlx.web.folders.choose_folder", lambda *args: None)
    assert client.post("/api/folders/select", json={"target": "output_dir"}).status_code == 200
