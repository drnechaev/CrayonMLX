import pytest
from fastapi.testclient import TestClient
from PIL import Image

from crayonmlx.app import create_app


class TestRenderer:
    __test__ = False
    id = "mflux-qwen-edit"
    name = "Test renderer (no inference)"
    base_models = ("qwen-image-edit-2511", "qwen-image-edit")
    supports_strength = False

    def available(self):
        return True

    def render(self, preset, model, source, output):
        with Image.open(source) as image:
            image.resize((preset.parameters.width, preset.parameters.height)).save(output)


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "data", {"mflux-qwen-edit": TestRenderer()})
    with TestClient(app) as client:
        model = tmp_path / "models" / "qwen"
        model.mkdir(parents=True)
        (model / "mflux_model.json").write_text('{"model_name": "qwen-image-edit-2511"}')
        response = client.put(
            "/api/settings", json={"models_dir": str(model.parent), "output_dir": str(tmp_path / "art")}
        )
        assert response.status_code == 200
        yield client
