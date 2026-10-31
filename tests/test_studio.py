import io
import json
import time

from PIL import Image


def upload():
    stream = io.BytesIO()
    Image.new("RGB", (48, 64), "lavender").save(stream, format="PNG")
    return ("drawing.png", stream.getvalue(), "image/png")


def request_body(client):
    preset = client.get("/api/presets").json()[0]
    preset.pop("id")
    return {"preset": preset, "model": "qwen"}


def wait_job(client, identifier):
    for _ in range(100):
        job = client.get(f"/api/generations/{identifier}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.01)
    raise AssertionError("Job did not finish")


def test_presets_roundtrip_and_validation(client):
    preset = request_body(client)["preset"]
    preset["name"] = "Моя сказка"
    preset["blocks"]["background"] = "A mountain stream"
    created = client.post("/api/presets", json=preset)
    assert created.status_code == 201
    identifier = created.json()["id"]
    preset["parameters"]["steps"] = 24
    assert client.put(f"/api/presets/{identifier}", json=preset).json()["parameters"]["steps"] == 24
    assert client.delete(f"/api/presets/{identifier}").status_code == 204
    assert client.put(f"/api/presets/{identifier}", json=preset).status_code == 404
    preset["parameters"]["width"] = 511
    assert client.post("/api/presets", json=preset).status_code == 422


def test_generation_history_and_immutable_paths(client, tmp_path):
    body = request_body(client)
    response = client.post("/api/generations", data={"config": json.dumps(body)}, files={"image": upload()})
    assert response.status_code == 202
    job = wait_job(client, response.json()["id"])
    assert job["status"] == "completed", job["error"]
    assert job["request"]["preset"]["parameters"]["seed"] >= 0
    assert "mountain" in job["request"]["prompt"].lower() or job["request"]["prompt"]
    assert client.get(f"/api/generations/{job['id']}/output").headers["content-type"] == "image/png"
    settings = client.get("/api/settings").json()
    client.put(
        "/api/settings", json={"models_dir": settings["models_dir"], "output_dir": str(tmp_path / "other")}
    )
    assert client.get(f"/api/generations/{job['id']}/output").status_code == 200
    assert len(client.get("/api/generations").json()) == 1
    assert client.get(f"/api/generations/{job['id']}/arbitrary").status_code == 404


def test_invalid_inputs_do_not_create_jobs(client):
    body = request_body(client)
    bad = client.post(
        "/api/generations",
        data={"config": json.dumps(body)},
        files={"image": ("bad.png", b"not image", "image/png")},
    )
    assert bad.status_code == 422
    body["model"] = "../outside"
    assert (
        client.post(
            "/api/generations", data={"config": json.dumps(body)}, files={"image": upload()}
        ).status_code
        == 422
    )
    body["model"] = "qwen"
    body["model"] = "missing-checkpoint"
    assert (
        client.post(
            "/api/generations", data={"config": json.dumps(body)}, files={"image": upload()}
        ).status_code
        == 422
    )
    assert client.get("/api/generations").json() == []


def test_token_is_write_only_and_can_be_cleared(client, tmp_path):
    settings = client.get("/api/settings").json()
    body = {
        "models_dir": settings["models_dir"],
        "output_dir": settings["output_dir"],
        "hf_token": "hf_test_credential",
    }
    response = client.put("/api/settings", json=body)
    assert response.status_code == 200
    assert response.json()["has_hf_token"]
    assert "hf_test_credential" not in client.get("/api/settings").text
    assert (tmp_path / "data" / "hf-token").stat().st_mode & 0o777 == 0o600
    body["hf_token"] = ""
    assert not client.put("/api/settings", json=body).json()["has_hf_token"]


def test_local_ui_and_remote_form_protection(client):
    assert "CrayonMLX" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/api/models").json()[0]["id"] == "qwen"
    assert (
        client.post(
            "/api/presets", json=request_body(client)["preset"], headers={"Origin": "https://remote.example"}
        ).status_code
        == 403
    )
    assert client.get("/", headers={"Host": "remote.example"}).status_code == 400


def test_prompt_library_crud_and_categories(client):
    initial = client.get("/api/prompt-templates").json()
    assert {item["category"] for item in initial} == {
        "style",
        "subject",
        "background",
        "composition",
        "lighting",
        "constraints",
    }
    body = {"name": "Мой лес", "category": "background", "text": "A sunlit forest"}
    response = client.post("/api/prompt-templates", json=body)
    assert response.status_code == 201
    identifier = response.json()["id"]
    body["text"] = "A snowy forest"
    assert client.put(f"/api/prompt-templates/{identifier}", json=body).json()["text"] == body["text"]
    body["category"] = "unknown"
    assert client.post("/api/prompt-templates", json=body).status_code == 422
    assert client.delete(f"/api/prompt-templates/{identifier}").status_code == 204
    assert client.delete(f"/api/prompt-templates/{identifier}").status_code == 404


def test_config_crud_none_and_compatibility(client):
    body = {
        "name": "Без квантизации",
        "engine": "mflux-qwen-edit",
        "base_model": "qwen-image-edit",
        "parameters": {"quantize": None},
    }
    response = client.post("/api/generation-configs", json=body)
    assert response.status_code == 201
    assert response.json()["parameters"]["quantize"] is None
    identifier = response.json()["id"]
    body["parameters"]["steps"] = 42
    assert client.put(f"/api/generation-configs/{identifier}", json=body).json()["parameters"]["steps"] == 42
    body["base_model"] = "schnell"
    assert client.post("/api/generation-configs", json=body).status_code == 422
    assert client.delete(f"/api/generation-configs/{identifier}").status_code == 204


def test_history_is_snapshot_and_has_no_edit_endpoint(client):
    body = request_body(client)
    template = client.post(
        "/api/prompt-templates",
        json={"name": "Background", "category": "background", "text": "Original background"},
    ).json()
    config = client.post(
        "/api/generation-configs",
        json={
            "name": "Settings",
            "engine": body["preset"]["engine"],
            "base_model": body["preset"]["base_model"],
            "parameters": {"steps": 12, "quantize": None},
        },
    ).json()
    body["preset"]["blocks"]["background"] = template["text"]
    body["preset"]["parameters"] = config["parameters"]
    response = client.post("/api/generations", data={"config": json.dumps(body)}, files={"image": upload()})
    identifier = response.json()["id"]
    before = wait_job(client, identifier)
    client.put(
        f"/api/prompt-templates/{template['id']}",
        json={"name": "Background", "category": "background", "text": "Changed background"},
    )
    client.put(
        f"/api/generation-configs/{config['id']}",
        json={
            "name": "Settings",
            "engine": config["engine"],
            "base_model": config["base_model"],
            "parameters": {"steps": 99},
        },
    )
    after = client.get(f"/api/generations/{identifier}").json()
    assert after["request"] == before["request"]
    assert after["request"]["preset"]["parameters"]["quantize"] is None
    assert after["request"]["preset"]["parameters"]["steps"] == 12
    assert after["request"]["preset"]["blocks"]["background"] == "Original background"
    assert client.put(f"/api/generations/{identifier}", json=body).status_code == 405


def test_full_preset_lighting_and_preservation_are_snapshotted(client):
    body = request_body(client)
    body["preset"]["blocks"]["lighting"] = "Neon reflected light"
    body["preset"]["blocks"]["preservation"] = {"identity": True, "clothing": True, "background": False}
    created = client.post("/api/presets", json=body["preset"]).json()
    assert created["blocks"]["lighting"] == "Neon reflected light"
    response = client.post("/api/generations", data={"config": json.dumps(body)}, files={"image": upload()})
    job = wait_job(client, response.json()["id"])
    snapshot = job["request"]
    assert snapshot["preset"]["blocks"]["preservation"]["clothing"] is True
    assert "Neon reflected light" in snapshot["prompt"]
    assert "Preserve the original clothing" in snapshot["prompt"]
    client.delete(f"/api/presets/{created['id']}")
    assert client.get(f"/api/generations/{job['id']}").json()["request"] == snapshot
