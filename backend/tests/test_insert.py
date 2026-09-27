"""Tests for contrast insert STL generation."""
import os
import tempfile

import pytest

from app.services.polygon_scaler import ScaledPolygon
from app.services.stl_generator_manifold import ManifoldSTLGenerator

GF_GRID = 42.0


class FakeConfig:
    def __init__(self, insert_height=1.0, grid_x=2, grid_y=2, insert_clearance=None):
        self.insert_enabled = True
        self.insert_height = insert_height
        self.grid_x = grid_x
        self.grid_y = grid_y
        if insert_clearance is not None:
            self.insert_clearance = insert_clearance


def _make_polygon(x, y, size, poly_id="test"):
    return ScaledPolygon(
        id=poly_id,
        points_mm=[(x, y), (x + size, y), (x + size, y + size), (x, y + size)],
        label="test",
        finger_holes=[],
        interior_rings_mm=[],
    )


def _grid_offsets(grid_x=2, grid_y=2):
    bin_width = grid_x * GF_GRID
    bin_depth = grid_y * GF_GRID
    return -bin_width / 2, -bin_depth / 2


@pytest.fixture
def generator():
    return ManifoldSTLGenerator()


@pytest.fixture
def output_path():
    fd, path = tempfile.mkstemp(suffix=".stl")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_generate_insert_produces_file(generator, output_path):
    poly = _make_polygon(10, 10, 20)
    config = FakeConfig()
    ox, oy = _grid_offsets()

    result = generator.generate_insert([poly], config, output_path, ox, oy)

    assert result is True
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0


def test_generate_insert_empty_polygons(generator, output_path):
    config = FakeConfig()

    result = generator.generate_insert([], config, output_path, 0, 0)

    assert result is False


def test_generate_insert_custom_height(generator, output_path):
    poly = _make_polygon(10, 10, 20)
    config = FakeConfig(insert_height=2.5)
    ox, oy = _grid_offsets()

    result = generator.generate_insert([poly], config, output_path, ox, oy)

    assert result is True
    assert os.path.getsize(output_path) > 0


def test_generate_insert_multiple_polygons(generator, output_path):
    polys = [
        _make_polygon(5, 5, 15, "tool1"),
        _make_polygon(30, 30, 10, "tool2"),
    ]
    config = FakeConfig()
    ox, oy = _grid_offsets()

    result = generator.generate_insert(polys, config, output_path, ox, oy)

    assert result is True
    assert os.path.getsize(output_path) > 0


def test_generate_insert_degenerate_polygon(generator, output_path):
    degen = ScaledPolygon(
        id="degen",
        points_mm=[(0, 0), (1, 0)],
        label="degen",
        finger_holes=[],
        interior_rings_mm=[],
    )
    config = FakeConfig()
    ox, oy = _grid_offsets()

    result = generator.generate_insert([degen], config, output_path, ox, oy)

    assert result is False


def _stl_extents(path):
    import trimesh
    mesh = trimesh.load(path)
    return mesh.bounds[1] - mesh.bounds[0]


def test_generate_insert_default_fit_clearance(generator, output_path):
    """insert must be smaller than the pocket it drops into (default 0.2mm/side)."""
    poly = _make_polygon(10, 10, 20)
    config = FakeConfig()
    ox, oy = _grid_offsets()

    assert generator.generate_insert([poly], config, output_path, ox, oy) is True

    extents = _stl_extents(output_path)
    assert extents[0] == pytest.approx(20.0 - 2 * 0.2, abs=0.02)
    assert extents[1] == pytest.approx(20.0 - 2 * 0.2, abs=0.02)


def test_generate_insert_custom_fit_clearance(generator, output_path):
    poly = _make_polygon(10, 10, 20)
    config = FakeConfig(insert_clearance=0.5)
    ox, oy = _grid_offsets()

    assert generator.generate_insert([poly], config, output_path, ox, oy) is True

    extents = _stl_extents(output_path)
    assert extents[0] == pytest.approx(20.0 - 2 * 0.5, abs=0.02)


def test_generate_insert_keeps_all_pieces_when_clearance_splits_shape(generator, output_path):
    """a narrow neck can vanish under the fit clearance; both lobes must survive."""
    dumbbell = ScaledPolygon(
        id="dumbbell",
        points_mm=[
            (0, 0), (20, 0), (20, 9.85), (50, 9.85), (50, 0), (70, 0),
            (70, 20), (50, 20), (50, 10.15), (20, 10.15), (20, 20), (0, 20),
        ],
        label="dumbbell",
        finger_holes=[],
        interior_rings_mm=[],
    )
    config = FakeConfig()  # default 0.2mm clearance kills the 0.3mm neck
    ox, oy = _grid_offsets()

    assert generator.generate_insert([dumbbell], config, output_path, ox, oy) is True

    extents = _stl_extents(output_path)
    # both 20mm lobes present: full 70mm span minus clearance each side
    assert extents[0] == pytest.approx(70.0 - 2 * 0.2, abs=0.02)


def test_generate_insert_with_hole(generator, output_path):
    poly = ScaledPolygon(
        id="holed",
        points_mm=[(0, 0), (40, 0), (40, 40), (0, 40)],
        label="holed",
        finger_holes=[],
        interior_rings_mm=[[(10, 10), (30, 10), (30, 30), (10, 30)]],
    )
    config = FakeConfig()
    ox, oy = _grid_offsets()

    result = generator.generate_insert([poly], config, output_path, ox, oy)

    assert result is True
    assert os.path.getsize(output_path) > 0


# ── in-place inserts ──────────────────────────────────────────────────────────

def _to_manifold(mesh):
    import manifold3d as mf
    import numpy as np
    return mf.Manifold(mf.Mesh(
        vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
        tri_verts=np.asarray(mesh.faces, dtype=np.uint32),
    ))


def _in_place_pair(tmp_path, polys, **overrides):
    """Generate a bin and its in-place insert the way the route does."""
    import trimesh

    from app.models.schemas import GenerateRequest

    params = dict(grid_x=2, grid_y=2, height_units=4, cutout_depth=10, stacking_lip=False,
                  magnets=False, insert_enabled=True, insert_height=0.2,
                  insert_clearance=0.5, insert_in_place=True)
    params.update(overrides)
    config = GenerateRequest(**params)
    gen = ManifoldSTLGenerator()
    bin_path, insert_path = tmp_path / "bin.stl", tmp_path / "insert.stl"
    gen.generate_bin(polys, config, str(bin_path))
    ox, oy = _grid_offsets(config.grid_x, config.grid_y)
    assert gen.generate_insert(polys, config, str(insert_path), ox, oy) is True
    return trimesh.load_mesh(bin_path), trimesh.load_mesh(insert_path)


def test_in_place_insert_fills_pocket_floor(tmp_path):
    bin_mesh, insert = _in_place_pair(tmp_path, [_make_polygon(10, 10, 20)])
    # pocket spans the requested depth plus the insert allowance
    floor = 4 * 7 - 10.2
    assert insert.bounds[0, 2] == pytest.approx(floor, abs=1e-4)
    assert insert.bounds[1, 2] == pytest.approx(floor + 0.2, abs=1e-4)
    # fit clearance is ignored: the insert is the full pocket outline, in
    # the bin's own coordinate frame
    ox, oy = _grid_offsets()
    assert insert.bounds[0, :2] == pytest.approx([10 + ox, -(30 + oy)], abs=1e-4)
    assert insert.bounds[1, :2] == pytest.approx([30 + ox, -(10 + oy)], abs=1e-4)
    # the insert occupies only empty pocket space and rests on the bin
    body, part = _to_manifold(bin_mesh), _to_manifold(insert)
    assert (body ^ part).volume() == pytest.approx(0, abs=1e-3)
    assert (body + part).volume() == pytest.approx(body.volume() + part.volume(), rel=1e-6)
    assert part.volume() == pytest.approx(20 * 20 * 0.2, rel=1e-4)


def test_in_place_insert_follows_per_cutout_depth(tmp_path):
    shallow = _make_polygon(5, 5, 15, poly_id="shallow")
    deep = _make_polygon(50, 50, 15, poly_id="deep")
    deep.depth_override = 15
    _, insert = _in_place_pair(tmp_path, [shallow, deep])
    parts = sorted(insert.split(only_watertight=True), key=lambda m: m.bounds[0, 2])
    assert len(parts) == 2
    assert parts[0].bounds[0, 2] == pytest.approx(28 - 15.2, abs=1e-4)
    assert parts[1].bounds[0, 2] == pytest.approx(28 - 10.2, abs=1e-4)


def test_in_place_insert_clipped_to_bin_interior(tmp_path):
    # the tool overhangs the wall; the pocket is clipped, so is the insert
    bin_mesh, insert = _in_place_pair(tmp_path, [_make_polygon(-10, 10, 30)])
    body, part = _to_manifold(bin_mesh), _to_manifold(insert)
    assert (body ^ part).volume() == pytest.approx(0, abs=1e-3)
    assert insert.bounds[0, 0] == pytest.approx(-(2 * GF_GRID - 0.5) / 2 + 1.6, abs=1e-4)


def test_in_place_insert_capped_by_shallow_pocket(tmp_path):
    # 1u bins only allow a 0.25mm pocket; the insert must not rise above the wall top
    _, insert = _in_place_pair(tmp_path, [_make_polygon(10, 10, 20)],
                               height_units=1, cutout_depth=0.25, insert_height=1.0)
    assert insert.bounds[0, 2] == pytest.approx(6.75, abs=1e-4)
    assert insert.bounds[1, 2] == pytest.approx(7.0, abs=1e-4)


def test_loose_insert_unchanged_by_in_place_default(generator, output_path):
    config = FakeConfig()
    ox, oy = _grid_offsets()
    assert generator.generate_insert([_make_polygon(10, 10, 20)], config, output_path, ox, oy)
    import trimesh
    assert trimesh.load(output_path).bounds[0, 2] == pytest.approx(0)
