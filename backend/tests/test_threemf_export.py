"""3MF export: one multi-part object holding every body that prints with the bin."""
import zipfile

import numpy as np
import pytest
from lxml import etree

from app.api import routes
from app.models.schemas import GenerateRequest, TextLabel
from app.services.polygon_scaler import ScaledPolygon

NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}


class _OpenStore:
    def ensure_open(self):
        pass


def _square(x, y, size):
    return ScaledPolygon("sq", [(x, y), (x + size, y), (x + size, y + size), (x, y + size)], "Square")


def _generate(monkeypatch, tmp_path, **params):
    monkeypatch.setattr(routes, "_stl_generation_semaphore", None)
    (tmp_path / "outputs").mkdir()
    config = GenerateRequest(grid_x=2, grid_y=2, height_units=4, cutout_depth=10,
                             stacking_lip=False, magnets=False, **params)
    response = routes._run_generate(
        [_square(10, 10, 20)], config, "bin", tmp_path, "hash", "default", _OpenStore()
    )
    assert response.threemf_url and response.threemf_url.endswith("/bin.3mf")
    return tmp_path / "outputs" / "bin.3mf"


def _parts(path):
    """{part name: vertex array} for the single printable object, plus build item count."""
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("3D/3dmodel.model"))
    objects = {o.get("id"): o for o in root.iterfind(".//m:resources/m:object", NS)}
    items = root.findall(".//m:build/m:item", NS)
    assert len(items) == 1, "every body must belong to one object"
    parent = objects[items[0].get("objectid")]
    parts = {}
    for comp in parent.iterfind(".//m:component", NS):
        # identity transforms keep every part where it was modelled
        assert [float(v) for v in comp.get("transform").split()] == [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
        obj = objects[comp.get("objectid")]
        verts = np.array([[float(v.get(a)) for a in "xyz"] for v in obj.iterfind(".//m:vertex", NS)])
        parts[obj.get("name")] = verts
    return parts


def test_plain_bin_gets_a_3mf(monkeypatch, tmp_path):
    parts = _parts(_generate(monkeypatch, tmp_path))
    assert set(parts) == {"bin"}
    assert parts["bin"][:, 2].min() == pytest.approx(0)


def test_in_place_insert_is_a_part_of_the_bin_object(monkeypatch, tmp_path):
    parts = _parts(_generate(monkeypatch, tmp_path, insert_enabled=True, insert_height=0.2,
                             insert_in_place=True))
    assert set(parts) == {"bin", "insert"}
    floor = 4 * 7 - 10.2
    assert parts["insert"][:, 2].min() == pytest.approx(floor, abs=1e-4)
    assert parts["insert"][:, 2].max() == pytest.approx(floor + 0.2, abs=1e-4)
    # the separate STL is still written for users who prefer it
    assert (tmp_path / "outputs" / "bin_insert.stl").exists()


def test_loose_insert_stays_out_of_the_3mf(monkeypatch, tmp_path):
    parts = _parts(_generate(monkeypatch, tmp_path, insert_enabled=True))
    assert set(parts) == {"bin"}
    assert (tmp_path / "outputs" / "bin_insert.stl").exists()


def test_labels_and_insert_share_the_object(monkeypatch, tmp_path):
    label = TextLabel(id="l", text="AB", x=60, y=60, font_size=6, depth=1, emboss=True)
    parts = _parts(_generate(monkeypatch, tmp_path, insert_enabled=True, insert_in_place=True,
                             insert_height=0.2, text_labels=[label]))
    assert set(parts) == {"bin", "labels", "insert"}
